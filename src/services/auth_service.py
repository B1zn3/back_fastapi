import uuid
from datetime import datetime

from fastapi import HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.email_service import email_service
from src.services.verification_service import verification_service
from src.core.config import settings
from src.core.constants import RoleName, TokenType
from src.core.exceptions import (
    BaseAppException,
    InvalidCredentialsError,
    InvalidTokenError,
    RateLimitExceededError,
    TokenRevokedError,
    UserInactiveError,
)
from src.core.hash import HashService
from src.cruds.applicant_cruds.applicant_crud import applicantcrud
from src.cruds.auth_crud import authcrud
from src.cruds.company_cruds.company_crud import companycrud
from src.cruds.role_crud import rolecrud
from src.redis.auth import blacklist_manager, fingerprint_manager, session_manager
from src.redis.rate_limit import rate_limiter
from src.schemas.auth_schema import (
    AuthMeResponse,
    CredentialsUpdateRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
)
from src.utils.auth_utils import JWTToken
from src.utils.logger import logger


class AuthService:
    async def start_registration(self, db: AsyncSession, user_data: UserCreate):
        normalized_email = user_data.email.strip().lower()
        existing = await authcrud.get_by_email(db, normalized_email)
        if existing:
            raise InvalidCredentialsError("Пользователь с таким email уже существует")

        if user_data.role == RoleName.APPLICANT:
            role = await rolecrud.get_by_name(db, RoleName.APPLICANT)
        else:
            role = await rolecrud.get_by_name(db, RoleName.COMPANY)

        if not role:
            raise InvalidCredentialsError("Роль по умолчанию не настроена")

        if user_data.role == RoleName.COMPANY and not user_data.company_name:
            raise InvalidCredentialsError("Название компании обязательно для регистрации")

        pending_data = {
            "email": normalized_email,
            "password_hash": HashService.get_password_hash(user_data.password),
            "role": user_data.role,
            "company_name": user_data.company_name,
        }

        code = await verification_service.create_signup_verification(
            normalized_email,
            pending_data,
        )

        await email_service.send_signup_code(normalized_email, code)

        logger.info(f"Registration verification started for {normalized_email}")
        return {
            "message": "Код подтверждения отправлен на почту",
            "verification_required": True,
            "email": normalized_email,
            }

    async def login(
        self,
        db: AsyncSession,
        user_data: UserLogin,
        request: Request,
    ) -> TokenResponse:
        client_ip = request.client.host
        normalized_email = user_data.email.strip().lower()
        rate_key = f"login:{normalized_email}:{client_ip}"

        allowed = await rate_limiter.check_and_increment(
            rate_key,
            settings.LOGIN_RATE_LIMIT,
            settings.LOGIN_RATE_WINDOW,
        )
        if not allowed:
            raise RateLimitExceededError()

        user = await authcrud.get_by_email_with_role(db, normalized_email)
        if not user or not HashService.verify_password(user_data.password, user.password):
            logger.warning(
                f"Failed login attempt for email {normalized_email} from IP {client_ip}"
            )
            raise InvalidCredentialsError()

        if not user.is_active:
            raise UserInactiveError()

        if user.role.name != user_data.role:
            raise InvalidCredentialsError()

        fingerprint = f"{request.headers.get('user-agent', '')}:{client_ip}"
        session_id = str(uuid.uuid4())

        access_token = JWTToken.create_access_token({"sub": str(user.id)}, session_id)
        refresh_token = JWTToken.create_refresh_token({"sub": str(user.id)}, session_id)
        access_jti = JWTToken.get_jti(access_token)

        try:
            await session_manager.create_session(
                user_id=str(user.id),
                session_id=session_id,
                refresh_token=refresh_token,
                access_jti=access_jti,
                fingerprint=fingerprint,
            )
            await fingerprint_manager.save_fingerprint(str(user.id), fingerprint)
            await session_manager.enforce_max_sessions(
                str(user.id),
                settings.MAX_SESSIONS_PER_USER,
            )
        except Exception as e:
            logger.error(
                f"Failed to create session for user {user.id}: {e}",
                exc_info=True,
            )
            raise HTTPException(status_code=500, detail="Failed to create session")

        logger.info(f"User logged in: {user.email} (id={user.id}), session={session_id}")
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh_tokens(self, refresh_token: str, request: Request) -> TokenResponse:
        client_ip = request.client.host
        rate_key = f"refresh:{client_ip}"

        allowed = await rate_limiter.check_and_increment(
            rate_key,
            settings.REFRESH_RATE_LIMIT,
            settings.REFRESH_RATE_WINDOW,
        )
        if not allowed:
            raise RateLimitExceededError()

        try:
            payload = JWTToken.decode_token(refresh_token, expected_type=TokenType.REFRESH)
        except Exception as e:
            raise InvalidTokenError("Невалидный refresh токен") from e

        user_id = payload.get("sub")
        session_id = payload.get("sid")
        if not user_id or not session_id:
            raise InvalidTokenError("Недостаточно данных в токене")

        current_fingerprint = f"{request.headers.get('user-agent', '')}:{client_ip}"
        stored_fingerprint = await fingerprint_manager.get_fingerprint(str(user_id))

        if stored_fingerprint and stored_fingerprint != current_fingerprint:
            await session_manager.delete_session(user_id, session_id)
            raise TokenRevokedError(
                "Обнаружена подозрительная активность. Выполните вход заново."
            )

        new_access = JWTToken.create_access_token({"sub": user_id}, session_id)
        new_access_jti = JWTToken.get_jti(new_access)
        new_refresh = JWTToken.create_refresh_token({"sub": user_id}, session_id)

        success = await session_manager.rotate_session(
            user_id,
            session_id,
            refresh_token,
            new_refresh,
            new_access_jti,
        )
        if not success:
            raise InvalidTokenError("Сессия недействительна. Выполните вход заново.")

        logger.info(f"Tokens refreshed for user {user_id}, session {session_id}")
        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    async def logout(
        self,
        access_token: str,
        user_id: int,
        refresh_token: str,
        request: Request,
    ):
        try:
            payload = JWTToken.decode_token(access_token, expected_type=TokenType.ACCESS)
            session_id = payload.get("sid")
            jti = payload.get("jti")
        except Exception as e:
            raise InvalidTokenError("Невалидный access токен") from e

        session = await session_manager.get_session(str(user_id), session_id)
        if not session or session.get("refresh_token") != refresh_token:
            await session_manager.delete_session(str(user_id), session_id)
            raise InvalidTokenError("Сессия недействительна")

        exp = JWTToken.get_exp(access_token)
        ttl = max(int(exp.timestamp()) - int(datetime.utcnow().timestamp()), 60)
        await blacklist_manager.blacklist_access_jti(jti, ttl)

        await session_manager.delete_session(str(user_id), session_id)
        logger.info(f"User {user_id} logged out, session {session_id}")

    async def logout_all(self, user_id: int):
        await session_manager.delete_all_sessions(str(user_id))
        logger.info(f"User {user_id} logged out from all devices")

    async def get_me(self, db: AsyncSession, user_id: int) -> AuthMeResponse:
        user = await authcrud.get_with_role(db, user_id)
        if not user:
            raise BaseAppException(status_code=404, message="Пользователь не найден")

        role_name = user.role.name if user.role else ""

        return AuthMeResponse(
            id=user.id,
            email=user.email,
            role=role_name,
            is_active=user.is_active,
        )

    async def update_credentials(
        self,
        db: AsyncSession,
        user_id: int,
        payload: CredentialsUpdateRequest,
    ):
        user = await authcrud.get_by_id(db, user_id)

        if not user:
            raise BaseAppException(status_code=404, message="Пользователь не найден")

        if not HashService.verify_password(payload.current_password, user.password):
            raise BaseAppException(status_code=401, message="Неверный текущий пароль")

        normalized_email = payload.email.strip().lower()

        if normalized_email != user.email:
            email_taken = await authcrud.is_email_taken_by_other(
                db,
                normalized_email,
                user.id,
            )

            if email_taken:
                raise BaseAppException(status_code=409, message="Email уже используется")

            await authcrud.update_user_email(db, user, normalized_email)

        applicant = await authcrud.get_applicant_for_user(db, user.id)

        if not applicant:
            raise BaseAppException(status_code=404, message="Профиль соискателя не найден")

        normalized_phone = payload.phone
        
        if normalized_phone and normalized_phone != applicant.phone:
            phone_taken = await authcrud.is_phone_taken_by_other(
                db,
                normalized_phone,
                applicant.id,
            )

            if phone_taken:
                raise BaseAppException(
                    status_code=409,
                    message="Телефон уже используется другим аккаунтом",
                )

        try:
            await authcrud.update_applicant_phone(db, applicant, normalized_phone)
            await authcrud.commit(db)
        except IntegrityError as e:
            await db.rollback()

            error_text = str(e.orig).lower()

            if "applicants_phone_key" in error_text or "key (phone)" in error_text:
                raise BaseAppException(
                    status_code=409,
                    message="Телефон уже используется другим аккаунтом",
                )

            if "users_email_key" in error_text or "key (email)" in error_text:
                raise BaseAppException(
                    status_code=409,
                    message="Email уже используется другим аккаунтом",
                )

            logger.error(f"IntegrityError in update_credentials: {e}", exc_info=True)
            raise BaseAppException(
                status_code=400,
                message="Некорректные контактные данные",
            )

        await authcrud.refresh_user(db, user)
        await authcrud.refresh_applicant(db, applicant)

        return {
            "message": "Контактные данные обновлены",
            "email": user.email,
            "phone": applicant.phone,
        }

    async def change_password(
        self,
        db: AsyncSession,
        user_id: int,
        payload: PasswordChangeRequest,
    ):
        user = await authcrud.get_by_id(db, user_id)
        if not user:
            raise BaseAppException(status_code=404, message="Пользователь не найден")

        if not HashService.verify_password(payload.current_password, user.password):
            raise BaseAppException(status_code=401, message="Неверный текущий пароль")

        if HashService.verify_password(payload.new_password, user.password):
            raise BaseAppException(
                status_code=400,
                message="Новый пароль должен отличаться от текущего",
            )

        new_password_hash = HashService.get_password_hash(payload.new_password)
        await authcrud.update_user_password(db, user, new_password_hash)

        await self.logout_all(user.id)

        await authcrud.commit(db)
        await authcrud.refresh_user(db, user)

        return {"message": "Пароль успешно изменён"}
    
    async def confirm_registration(
        self,
        db: AsyncSession,
        email: str,
        code: str,
        request: Request,
    ) -> TokenResponse:
        pending_data = await verification_service.verify_signup_code(email, code)

        normalized_email = pending_data["email"]

        existing = await authcrud.get_by_email(db, normalized_email)
        if existing:
            await verification_service.clear_signup_state(normalized_email)
            raise InvalidCredentialsError("Пользователь с таким email уже существует")

        role_name = pending_data["role"]

        if role_name == RoleName.APPLICANT:
            role = await rolecrud.get_by_name(db, RoleName.APPLICANT)
            applicant = await applicantcrud.create(db, {})
            await db.flush()
            applicant_id = applicant.id
            company_id = None
        else:
            role = await rolecrud.get_by_name(db, RoleName.COMPANY)
            company = await companycrud.create(db, {"name": pending_data["company_name"]})
            await db.flush()
            company_id = company.id
            applicant_id = None

        if not role:
            raise InvalidCredentialsError("Роль не найдена")

        user_dict = {
            "email": normalized_email,
            "password": pending_data["password_hash"],
            "role_id": role.id,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "applicant_id": applicant_id,
            "company_id": company_id,
        }

        user = await authcrud.create(db, user_dict)
        await db.commit()
        await db.refresh(user)

        await verification_service.clear_signup_state(normalized_email)

        login_payload = UserLogin(
            email=normalized_email,
            password="temporary-not-used",
            role=role_name,
        )

        fingerprint = f"{request.headers.get('user-agent', '')}:{request.client.host}"
        session_id = str(uuid.uuid4())

        access_token = JWTToken.create_access_token({"sub": str(user.id)}, session_id)
        refresh_token = JWTToken.create_refresh_token({"sub": str(user.id)}, session_id)
        access_jti = JWTToken.get_jti(access_token)

        try:
            await session_manager.create_session(
                user_id=str(user.id),
                session_id=session_id,
                refresh_token=refresh_token,
                access_jti=access_jti,
                fingerprint=fingerprint,
            )
            await fingerprint_manager.save_fingerprint(str(user.id), fingerprint)
            await session_manager.enforce_max_sessions(
                str(user.id),
                settings.MAX_SESSIONS_PER_USER,
            )
        except Exception as e:
            logger.error(
                f"Failed to create session for user {user.id}: {e}",
                exc_info=True,
            )
            raise HTTPException(status_code=500, detail="Failed to create session")

        logger.info(f"User confirmed registration and logged in: {user.email} (id={user.id})")
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    async def request_password_reset(
        self,
        db: AsyncSession,
        payload: PasswordResetRequest,
        request: Request,
    ):
        client_ip = request.client.host
        normalized_email = payload.email.strip().lower()

        rate_key = f"password-reset-request:{normalized_email}:{client_ip}"
        allowed = await rate_limiter.check_and_increment(
            rate_key,
            settings.LOGIN_RATE_LIMIT,
            settings.LOGIN_RATE_WINDOW,
        )
        if not allowed:
            raise RateLimitExceededError()

        user = await authcrud.get_by_email(db, normalized_email)

        # Не раскрываем, существует ли пользователь
        if not user:
            logger.info(f"Password reset requested for non-existing email: {normalized_email}")
            return {"message": "Код отправлен на почту"}

        if not user.is_active:
            logger.info(f"Password reset requested for inactive user: {normalized_email}")
            return {"message": "Код отправлен на почту"}

        code = await verification_service.create_password_reset_verification(normalized_email)
        await email_service.send_password_reset_code(normalized_email, code)

        logger.info(f"Password reset code sent to {normalized_email}")
        return {"message": "Код отправлен на почту"}

    async def confirm_password_reset(
        self,
        db: AsyncSession,
        payload: PasswordResetConfirmRequest,
    ):
        normalized_email = payload.email.strip().lower()

        user = await authcrud.get_by_email(db, normalized_email)
        if not user:
            raise BaseAppException(status_code=400, message="Неверный код или email")

        await verification_service.verify_password_reset_code(normalized_email, payload.code)

        if HashService.verify_password(payload.new_password, user.password):
            raise BaseAppException(
                status_code=400,
                message="Новый пароль должен отличаться от текущего",
            )
        new_password_hash = HashService.get_password_hash(payload.new_password)
        await authcrud.update_user_password(db, user, new_password_hash)

        await self.logout_all(user.id)

        await authcrud.commit(db)
        await authcrud.refresh_user(db, user)
        await verification_service.clear_password_reset_state(normalized_email)

        logger.info(f"Password reset completed for user {user.id}")
        return {"message": "Пароль успешно изменён"}
    
    async def resend_registration_code(
        self,
        db: AsyncSession,
        email: str,
        request: Request,
    ):
        client_ip = request.client.host
        normalized_email = email.strip().lower()

        rate_key = f"register-resend:{normalized_email}:{client_ip}"
        allowed = await rate_limiter.check_and_increment(
            rate_key,
            settings.LOGIN_RATE_LIMIT,
            settings.LOGIN_RATE_WINDOW,
        )
        if not allowed:
            raise RateLimitExceededError()

        existing = await authcrud.get_by_email(db, normalized_email)
        if existing:
            raise InvalidCredentialsError("Пользователь с таким email уже существует")

        pending_data = await verification_service.get_signup_pending(normalized_email)
        if not pending_data:
            raise BaseAppException(
                status_code=404,
                message="Регистрация не найдена или истекла. Заполните форму заново.",
            )

        code = await verification_service.create_signup_verification(
            normalized_email,
            pending_data,
        )

        await email_service.send_signup_code(normalized_email, code)

        logger.info(f"Registration code resent for {normalized_email}")
        return {
            "message": "Код подтверждения отправлен повторно",
            "verification_required": True,
            "email": normalized_email,
        }