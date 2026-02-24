from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from src.deps.db_deps import get_db, get_redis_service
from src.cruds.auth_crud import authcrud
from src.redis.redis_client import RedisClient
from src.utils.auth_utils import JWTToken

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis_service)
):
    token = credentials.credentials
    try:
        payload = JWTToken.decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Неверный тип токена")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Отсутствует идентификатор пользователя")
        try:
            user_id = int(user_id_str)
        except ValueError:
            raise HTTPException(status_code=401, detail="Некорректный идентификатор пользователя")
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="Отсутствует jti токена")
        if await redis_client.is_access_jti_blacklisted(jti):
            raise HTTPException(status_code=401, detail="Токен отозван")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Ошибка валидации токена: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Ошибка аутентификации")

    user = await authcrud.get_with_role(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Пользователь не найден или неактивен")
    return user