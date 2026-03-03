import json
from typing import Dict, Optional
import redis.asyncio as redis
from src.core.config import setting
from src.utils.auth_utils import JWTToken
from datetime import datetime


class RedisClient:
    def __init__(self):
        self.client = None

    async def _ensure_connection(self):
        """Ensure Redis connection is established."""
        if self.client is None:
            self.client = await redis.from_url(url=setting.REDIS_URL, decode_responses=True)

    async def connect(self):
        if self.client is None:
            self.client = await redis.from_url(url=setting.REDIS_URL, decode_responses=True)

    async def close(self):
        if self.client:
            await self.client.close()
            self.client = None

    async def ping(self) -> bool:
        await self._ensure_connection()
        return await self.client.ping()

    # Session management
    async def save_session(self, user_id: str, refresh_token: str, access_jti: str):
        await self._ensure_connection()
        key = f"session:{user_id}"
        await self.client.hset(key, mapping={
            "refresh": refresh_token,
            "access_jti": access_jti
        })
        await self.client.expire(key, setting.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)

    async def get_session(self, user_id: str) -> Optional[Dict[str, str]]:
        await self._ensure_connection()
        key = f"session:{user_id}"
        data = await self.client.hgetall(key)
        if data and "refresh" in data and "access_jti" in data:
            return {"refresh": data["refresh"], "access_jti": data["access_jti"]}
        return None

    async def delete_session(self, user_id: str):
        await self._ensure_connection()
        key = f"session:{user_id}"
        await self.client.delete(key)

    # Access token blacklist
    async def blacklist_access_jti(self, jti: str, ttl: int):
        await self._ensure_connection()
        await self.client.setex(f"blacklist:access:{jti}", ttl, "1")

    async def is_access_jti_blacklisted(self, jti: str) -> bool:
        await self._ensure_connection()
        return await self.client.exists(f"blacklist:access:{jti}") > 0

    # Refresh token (legacy methods, kept for compatibility)
    async def save_refresh_token(self, user_id: str, token: str) -> bool:
        await self._ensure_connection()
        key = f"user:{user_id}:refresh_token"
        expire_seconds = setting.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
        result = await self.client.setex(name=key, time=expire_seconds, value=token)
        return bool(result)

    async def get_refresh_token(self, user_id: str) -> Optional[str]:
        await self._ensure_connection()
        key = f"user:{user_id}:refresh_token"
        return await self.client.get(key)

    async def delete_refresh_token(self, user_id: str) -> bool:
        await self._ensure_connection()
        key = f"user:{user_id}:refresh_token"
        result = await self.client.delete(key)
        return result > 0

    # Blacklist (legacy)
    async def add_to_blacklist(self, token: str, expire_seconds: int = 900) -> bool:
        await self._ensure_connection()
        payload = JWTToken.decode_token(token)
        if payload and "exp" in payload:
            expire_time = payload["exp"]
            current_time = int(datetime.utcnow().timestamp())
            expire_seconds = max(expire_time - current_time, 60)
        key = f"blacklist:token:{token}"
        result = await self.client.setex(name=key, time=expire_seconds, value="1")
        return bool(result)

    async def is_blacklisted(self, token: str) -> bool:
        await self._ensure_connection()
        key = f"blacklist:token:{token}"
        return await self.client.exists(key) == 1

    # Counters
    async def increment_counter(self, key: str, amount: int = 1) -> int:
        await self._ensure_connection()
        return await self.client.incrby(key, amount)

    async def get_counter(self, key: str) -> int:
        await self._ensure_connection()
        val = await self.client.get(key)
        return int(val) if val else 0

    async def set_counter(self, key: str, value: int, ttl: Optional[int] = None):
        await self._ensure_connection()
        if ttl:
            await self.client.setex(key, ttl, value)
        else:
            await self.client.set(key, value)

    # Generic key-value cache
    async def cache_get(self, key: str) -> Optional[str]:
        await self._ensure_connection()
        return await self.client.get(key)

    async def cache_set(self, key: str, value: str, ttl: int):
        await self._ensure_connection()
        await self.client.setex(key, ttl, value)

    async def cache_delete(self, key: str):
        await self._ensure_connection()
        await self.client.delete(key)

    # Generic methods
    async def set_key_with_ttl(self, key: str, value: str, ttl_seconds: int) -> bool:
        await self._ensure_connection()
        result = await self.client.setex(name=key, time=ttl_seconds, value=value)
        return bool(result)

    async def get_key(self, key: str) -> Optional[str]:
        await self._ensure_connection()
        return await self.client.get(key)

    async def delete_key(self, key: str) -> bool:
        await self._ensure_connection()
        result = await self.client.delete(key)
        return result > 0