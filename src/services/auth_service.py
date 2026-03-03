import uuid
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import setting
from src.cruds.applicant_cruds.applicant_crud import applicantcrud
from src.cruds.auth_crud import authcrud
from src.cruds.company_cruds.company_crud import companycrud
from src.cruds.role_crud import rolecrud
from src.schemas.auth_schema import UserCreate, UserLogin, TokenResponse
from src.redis.redis_client import RedisClient
from src.utils.auth_utils import JWTToken
from src.core.hash import HashService

class AuthService:
    def __init__(self, auth_crud, role_crud):
        self.auth_crud = auth_crud
        self.role_crud = role_crud

    async def register(self, db: AsyncSession, user_data: UserCreate):
        existing = await self.auth_crud.get_by_email(db, user_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )

        if user_data.role == "applicant":
            role = await self.role_crud.get_by_name(db, "applicant")
        else:
            role = await self.role_crud.get_by_name(db, "company")

        if not role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Роль по умолчанию не настроена"
            )

        hashed_password = HashService.get_password_hash(user_data.password)

        if user_data.role == "applicant":
            applicant = await applicantcrud.create(db, {})
            await db.flush()
            applicant_id = applicant.id
            company_id = None
        else:
            if not user_data.company_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Название компании обязательно для регистрации"
                )
            company = await companycrud.create(db, {"name": user_data.company_name})
            await db.flush()
            company_id = company.id
            applicant_id = None

        user_dict = {
            "email": user_data.email,
            "password": hashed_password,
            "role_id": role.id,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "applicant_id": applicant_id,
            "company_id": company_id
        }
        user = await self.auth_crud.create(db, user_dict)

        await db.commit()
        await db.refresh(user)
        return user

    async def login(self, db: AsyncSession, user_data: UserLogin, redis_client: RedisClient) -> TokenResponse:
        user = await self.auth_crud.get_by_email_with_role(db, user_data.email)

        if not user or not HashService.verify_password(user_data.password, user.password):
            raise HTTPException(status_code=401, detail="Неверный email или пароль")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="Пользователь деактивирован")

        if user.role.name != user_data.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Неверный email или пароль"
            )

        await redis_client.delete_session(str(user.id))

        access_jti = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())
        access_token = JWTToken.create_access_token({"sub": str(user.id), "jti": access_jti})
        refresh_token = JWTToken.create_refresh_token({"sub": str(user.id), "jti": refresh_jti})

        await redis_client.save_session(str(user.id), refresh_token, access_jti)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh_tokens(self, refresh_token: str, db: AsyncSession, redis_client: RedisClient) -> TokenResponse:
        try:
            payload = JWTToken.decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Неверный тип токена")
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("No sub in token")
        except Exception:
            raise HTTPException(status_code=401, detail="Невалидный refresh токен")

        user = await self.auth_crud.get(db, int(user_id))
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Пользователь не найден или неактивен")

        session = await redis_client.get_session(str(user_id))
        if not session or session["refresh"] != refresh_token:
            raise HTTPException(status_code=401, detail="Невалидный refresh токен")

        old_access_jti = session["access_jti"]
        await redis_client.blacklist_access_jti(old_access_jti, setting.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

        new_access_jti = str(uuid.uuid4())
        new_refresh_jti = str(uuid.uuid4())
        new_access = JWTToken.create_access_token({"sub": str(user.id), "jti": new_access_jti})
        new_refresh = JWTToken.create_refresh_token({"sub": str(user.id), "jti": new_refresh_jti})

        await redis_client.save_session(str(user.id), new_refresh, new_access_jti)

        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    async def logout(self, access_jti: str, user_id: int, refresh_token: str, redis_client: RedisClient):
        session = await redis_client.get_session(str(user_id))
        if not session or session["refresh"] != refresh_token:
            raise HTTPException(status_code=401, detail="Невалидный refresh токен")

        await redis_client.blacklist_access_jti(access_jti, setting.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        await redis_client.blacklist_access_jti(session["access_jti"], setting.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        await redis_client.delete_session(str(user_id))