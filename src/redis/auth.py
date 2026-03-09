import time
from typing import Optional, Dict, List
from src.redis.client import redis_client
from src.core.config import settings
from src.utils.logger import logger

REFRESH_ROTATION_SCRIPT = """
local key = KEYS[1]
local old_refresh = ARGV[1]
local new_refresh = ARGV[2]
local new_access_jti = ARGV[3]
local ttl = ARGV[4]
local now = ARGV[5]

local session = redis.call('HGETALL', key)
if #session == 0 then
    return {0, "session not found", "", ""}
end

local session_data = {}
for i = 1, #session, 2 do
    session_data[session[i]] = session[i+1]
end

local stored_refresh = session_data['refresh_token'] or ""
if stored_refresh ~= old_refresh then
    redis.call('DEL', key)
    return {0, "refresh token mismatch", stored_refresh, ""}
end

redis.call('HSET', key, 'refresh_token', new_refresh, 'access_jti', new_access_jti, 'last_used', now)
redis.call('EXPIRE', key, ttl)
local new_stored = redis.call('HGET', key, 'refresh_token')
return {1, "ok", stored_refresh, new_stored}
"""

class SessionManager:
    def __init__(self):
        self._rotation_script_hash = None

    async def initialize(self):
        self._rotation_script_hash = await redis_client.client.script_load(REFRESH_ROTATION_SCRIPT)

    def _session_key(self, user_id: str, session_id: str) -> str:
        return f"session:{user_id}:{session_id}"

    def _user_sessions_key(self, user_id: str) -> str:
        return f"user_sessions:{user_id}"

    async def create_session(
        self,
        user_id: str,
        session_id: str,              # добавляем параметр
        refresh_token: str,
        access_jti: str,
        fingerprint: str = "",
        ttl: int = None
    ) -> str:
        key = self._session_key(user_id, session_id)
        ttl = ttl or settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        now = int(time.time())
        try:
            await redis_client.client.hset(key, mapping={
                "refresh_token": refresh_token,
                "access_jti": access_jti,
                "fingerprint": fingerprint,
                "created_at": now,
                "last_used": now
            })
            await redis_client.client.expire(key, ttl)
            await redis_client.client.sadd(self._user_sessions_key(user_id), session_id)
            await redis_client.client.expire(self._user_sessions_key(user_id), ttl)
            logger.info(f"✅ Session created: {key}")
        except Exception as e:
            logger.error(f"❌ Error creating session {key}: {e}", exc_info=True)
            raise
        return session_id

    async def get_session(self, user_id: str, session_id: str) -> Optional[Dict]:
        key = self._session_key(user_id, session_id)
        logger.info(f"🔍 GET_SESSION: looking for key={key}")
        data = await redis_client.client.hgetall(key)
        logger.info(f"🔍 GET_SESSION: found data={data}")
        if not data:
            return None
        await redis_client.client.hset(key, "last_used", int(time.time()))
        return data

    async def update_session_tokens(
        self,
        user_id: str,
        session_id: str,
        new_refresh_token: str,
        new_access_jti: str
    ):
        key = self._session_key(user_id, session_id)
        await redis_client.client.hset(key, mapping={
            "refresh_token": new_refresh_token,
            "access_jti": new_access_jti,
            "last_used": int(time.time())
        })

    async def rotate_session(
        self,
        user_id: str,
        session_id: str,
        old_refresh: str,
        new_refresh: str,
        new_access_jti: str
    ) -> bool:
        key = self._session_key(user_id, session_id)
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        now = int(time.time())
        logger.info(f"🔄 ROTATE: key={key}, old_refresh={old_refresh[:30]}..., new_access_jti={new_access_jti}")
        try:
            result = await redis_client.client.evalsha(
                self._rotation_script_hash,
                1,
                key,
                old_refresh,
                new_refresh,
                new_access_jti,
                str(ttl),
                str(now)
            )
            # result = [status, message, stored_refresh]
            status = result[0]
            message = result[1]
            stored_refresh = result[2] if len(result) > 2 else ""
            logger.info(f"🔄 ROTATE result: status={status}, message={message}, stored_refresh={stored_refresh[:30] if stored_refresh else 'None'}...")
            if status == 1:
                return True
            else:
                logger.warning(f"❌ ROTATE failed: {message}, stored_refresh={stored_refresh[:30] if stored_refresh else 'None'}")
                return False
        except Exception as e:
            logger.error(f"❌ ROTATE exception: {e}", exc_info=True)
            return False

    async def delete_session(self, user_id: str, session_id: str):
        key = self._session_key(user_id, session_id)
        await redis_client.client.delete(key)
        await redis_client.client.srem(self._user_sessions_key(user_id), session_id)

    async def delete_all_sessions(self, user_id: str):
        sessions_key = self._user_sessions_key(user_id)
        session_ids = await redis_client.client.smembers(sessions_key)
        if session_ids:
            keys = [self._session_key(user_id, sid) for sid in session_ids]
            await redis_client.client.delete(*keys)
        await redis_client.client.delete(sessions_key)

    async def get_all_sessions(self, user_id: str) -> List[Dict]:
        sessions_key = self._user_sessions_key(user_id)
        session_ids = await redis_client.client.smembers(sessions_key)
        sessions = []
        for sid in session_ids:
            key = self._session_key(user_id, sid)
            data = await redis_client.client.hgetall(key)
            if data:
                data["session_id"] = sid
                sessions.append(data)
        return sessions

    async def enforce_max_sessions(self, user_id: str, max_sessions: int):
        sessions = await self.get_all_sessions(user_id)
        if len(sessions) > max_sessions:
            sessions.sort(key=lambda s: int(s.get("created_at", 0)))
            to_delete = sessions[:len(sessions) - max_sessions]
            for s in to_delete:
                await self.delete_session(user_id, s["session_id"])

class BlacklistManager:
    async def blacklist_access_jti(self, jti: str, ttl_seconds: int):
        await redis_client.client.setex(f"blacklist:access:{jti}", ttl_seconds, "1")

    async def is_access_jti_blacklisted(self, jti: str) -> bool:
        return await redis_client.client.exists(f"blacklist:access:{jti}") > 0

class FingerprintManager:
    async def save_fingerprint(self, user_id: str, fingerprint: str, ttl: int = 3600):
        await redis_client.client.setex(f"fingerprint:{user_id}", ttl, fingerprint)

    async def get_fingerprint(self, user_id: str) -> Optional[str]:
        return await redis_client.client.get(f"fingerprint:{user_id}")

session_manager = SessionManager()
blacklist_manager = BlacklistManager()
fingerprint_manager = FingerprintManager()