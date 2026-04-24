import json
from typing import Any, Optional

from src.redis.client import redis_client


class VerificationStore:
    @staticmethod
    def _signup_pending_key(email: str) -> str:
        return f"auth:signup:pending:{email}"

    @staticmethod
    def _signup_code_key(email: str) -> str:
        return f"auth:signup:code:{email}"
    @staticmethod
    def _password_reset_code_key(email: str) -> str:
        return f"auth:password-reset:code:{email}"
    
    async def set_signup_pending(
        self,
        email: str,
        data: dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        key = self._signup_pending_key(email)
        await redis_client.client.setex(key, ttl_seconds, json.dumps(data))

    async def get_signup_pending(self, email: str) -> Optional[dict[str, Any]]:
        key = self._signup_pending_key(email)
        raw = await redis_client.client.get(key)
        if not raw:
            return None
        return json.loads(raw)

    async def delete_signup_pending(self, email: str) -> None:
        key = self._signup_pending_key(email)
        await redis_client.client.delete(key)

    async def set_signup_code(
        self,
        email: str,
        data: dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        key = self._signup_code_key(email)
        await redis_client.client.setex(key, ttl_seconds, json.dumps(data))

    async def get_signup_code(self, email: str) -> Optional[dict[str, Any]]:
        key = self._signup_code_key(email)
        raw = await redis_client.client.get(key)
        if not raw:
            return None
        return json.loads(raw)

    async def delete_signup_code(self, email: str) -> None:
        key = self._signup_code_key(email)
        await redis_client.client.delete(key)

    async def delete_signup_state(self, email: str) -> None:
        await self.delete_signup_pending(email)
        await self.delete_signup_code(email)
    async def set_password_reset_code(self, email: str, data: dict, ttl_seconds: int) -> None:
        key = self._password_reset_code_key(email)
        await redis_client.client.setex(key, ttl_seconds, json.dumps(data))

    async def get_password_reset_code(self, email: str) -> dict | None:
        key = self._password_reset_code_key(email)
        value = await redis_client.client.get(key)
        return json.loads(value) if value else None

    async def delete_password_reset_state(self, email: str) -> None:
        await redis_client.client.delete(self._password_reset_code_key(email))

verification_store = VerificationStore()