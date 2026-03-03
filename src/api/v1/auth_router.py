from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps.db_deps import get_db, get_redis_service
from src.deps.auth_deps import get_current_user
from src.cruds.auth_crud import authcrud
from src.cruds.role_crud import rolecrud
from src.schemas.auth_schema import UserCreate, UserLogin, TokenResponse, RefreshTokenRequest, LogoutRequest
from src.services.auth_service import AuthService
from src.redis.redis_client import RedisClient
from src.models.model import User
from src.core.config import setting
from src.utils.auth_utils import JWTToken

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

@auth_router.post("/register", summary="Регистрация нового пользователя")
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(authcrud, rolecrud)
    try:
        await service.register(db, user_data)
        return {"msg": "Пользователь успешно зарегистрирован"}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка регистрации: {str(e)}"
        )

@auth_router.post("/login", response_model=TokenResponse, summary="Вход в систему")
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis_service)
):
    service = AuthService(authcrud, rolecrud)
    try:
        tokens = await service.login(db, user_data, redis_client)
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка входа: {str(e)}"
        )

@auth_router.post("/refresh", response_model=TokenResponse, summary="Обновление access токена")
async def refresh(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis_service)
):
    service = AuthService(authcrud, rolecrud)
    try:
        tokens = await service.refresh_tokens(refresh_request.refresh_token, db, redis_client)
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении токена: {str(e)}"
        )

@auth_router.post("/logout")
async def logout(
    logout_request: LogoutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis_service),
    current_user: User = Depends(get_current_user)
):
    access_token = credentials.credentials
    try:
        payload = JWTToken.decode_token(access_token)
        access_jti = payload.get("jti")
        if not access_jti:
            raise HTTPException(status_code=401, detail="Отсутствует jti в access токене")
    except Exception:
        raise HTTPException(status_code=401, detail="Невалидный access токен")

    service = AuthService(authcrud, rolecrud)
    await service.logout(access_jti, current_user.id, logout_request.refresh_token, redis_client)
    return {"msg": "Успешный выход"}