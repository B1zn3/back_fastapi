from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TokenType
from src.cruds.auth_crud import authcrud
from src.models.model import User
from src.redis.auth import blacklist_manager, session_manager
from src.utils.auth_utils import JWTToken


async def get_current_user_from_ws(
    websocket: WebSocket,
    db: AsyncSession,
) -> User | None:
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(
            code=1008,
            reason="Token is required",
        )
        return None

    try:
        payload = JWTToken.decode_token(
            token,
            expected_type=TokenType.ACCESS,
        )

        user_id = payload.get("sub")
        session_id = payload.get("sid")
        jti = payload.get("jti")

        if not user_id or not session_id or not jti:
            await websocket.close(
                code=1008,
                reason="Invalid token payload",
            )
            return None

        if await blacklist_manager.is_access_jti_blacklisted(jti):
            await websocket.close(
                code=1008,
                reason="Token revoked",
            )
            return None

        session = await session_manager.get_session(
            str(user_id),
            session_id,
        )

        if not session:
            await websocket.close(
                code=1008,
                reason="Session not found",
            )
            return None

        if session.get("access_jti") != jti:
            await websocket.close(
                code=1008,
                reason="Invalid session token",
            )
            return None

        user = await authcrud.get_with_role(db, int(user_id))

        if not user or not user.is_active:
            await websocket.close(
                code=1008,
                reason="User not found or inactive",
            )
            return None

        if not user.role or user.role.name not in ("applicant", "company"):
            await websocket.close(
                code=1008,
                reason="Only applicant or company can use chat",
            )
            return None

        return user

    except Exception:
        await websocket.close(
            code=1008,
            reason="Authentication error",
        )
        return None