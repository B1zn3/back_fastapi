from json import JSONDecodeError
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import BaseAppException
from src.deps.auth_deps import get_current_user
from src.deps.db_deps import get_db
from src.schemas.auth_schema import (
    AuthMeResponse,
    CredentialsUpdateRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    ResendCodeRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    RegisterConfirmRequest,
    RegisterStartResponse,
)
from src.services.auth_service import AuthService

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


@auth_router.post("/register", response_model=RegisterStartResponse, summary="Начало регистрации")
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await auth_service.start_registration(db, user_data)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    
@auth_router.post("/register/confirm", response_model=TokenResponse, summary="Подверждение кода")
async def confirm_register(
    request: Request,
    payload: RegisterConfirmRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        tokens = await auth_service.confirm_registration(
            db=db,
            email=payload.email,
            code=payload.code,
            request=request,
        )
        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="strict",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        )
        return tokens
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    
@auth_router.post("/login", response_model=TokenResponse, summary="Логин")
async def login(
    request: Request,
    user_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        tokens = await auth_service.login(db, user_data, request)
        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="strict",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        )
        return tokens
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.post("/refresh", response_model=TokenResponse, summary="Создание новой пары токенов")
async def refresh(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = None,
):
    token_from_cookie = request.cookies.get("refresh_token")
    if token_from_cookie:
        refresh_token = token_from_cookie
    else:
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except (JSONDecodeError, Exception):
            refresh_token = None

    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token required")

    try:
        tokens = await auth_service.refresh_tokens(refresh_token, request)
        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="strict",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        )
        return tokens
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.post("/logout", summary="Выход из аккаунта на этом устройстве")
async def logout(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing access token")
    access_token = auth_header.split(" ")[1]

    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except (JSONDecodeError, Exception):
            refresh_token = None

    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token required")

    try:
        await auth_service.logout(access_token, current_user.id, refresh_token, request)
        response.delete_cookie("refresh_token")
        return {"msg": "Успешный выход"}
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.post("/logout-all", summary="Выход из аккаунта на всех устройствах")
async def logout_all(
    response: Response,
    current_user=Depends(get_current_user),
):
    try:
        await auth_service.logout_all(current_user.id)
        response.delete_cookie("refresh_token")
        return {"msg": "Вы вышли со всех устройств"}
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.get("/me", response_model=AuthMeResponse, summary="Получение данных пользователя")
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await auth_service.get_me(db, current_user.id)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.patch("/me/credentials", summary="Изменение почты и телефона")
async def update_my_credentials(
    payload: CredentialsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await auth_service.update_credentials(db, current_user.id, payload)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.patch("/me/password", summary="Изменение пароля")
async def change_my_password(
    payload: PasswordChangeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        result = await auth_service.change_password(db, current_user.id, payload)
        response.delete_cookie("refresh_token")
        return result
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@auth_router.post("/password-reset/request", summary="Начало восстановления пароля")
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await auth_service.request_password_reset(db, payload, request)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.post("/password-reset/confirm", summary="Восстановление пароля")
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await auth_service.confirm_password_reset(db, payload)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    
@auth_router.post("/register/resend-code", response_model=RegisterStartResponse, summary="Повторная отправка кода регистрации")
async def resend_register_code(
    payload: ResendCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await auth_service.resend_registration_code(
            db=db,
            email=payload.email,
            request=request,
        )
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)