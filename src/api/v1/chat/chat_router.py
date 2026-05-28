from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.encoders import jsonable_encoder
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.websocket_manager import chat_ws_manager
from src.core.exceptions import BaseAppException
from src.cruds.auth_crud import authcrud
from src.db.database import async_session
from src.deps.auth_deps import get_current_user
from src.deps.db_deps import get_db
from src.deps.ws_auth_deps import get_current_user_from_ws
from src.models.model import User
from src.schemas.chat.chat_schema import (
    ChatDetailResponse,
    ChatListItemResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatReadResponse,
)
from src.services.chat.chat_service import chat_service


chat_router = APIRouter(prefix="/chats", tags=["Чаты"])


async def get_current_chat_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.role or current_user.role.name not in ("applicant", "company"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён. Требуется роль: applicant или company",
        )

    return current_user


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def set_user_online_status(
    user_id: int,
    is_online: bool,
) -> None:
    async with async_session() as db:
        values = {
            "is_online": is_online,
        }

        if not is_online:
            values["last_seen_at"] = utc_now_naive()

        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**values)
        )

        await db.commit()


@chat_router.get(
    "",
    response_model=list[ChatListItemResponse],
)
async def get_my_chats(
    current_user: User = Depends(get_current_chat_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    try:
        return await chat_service.get_my_chats(
            db=db,
            current_user=current_user,
            skip=skip,
            limit=limit,
        )
    except BaseAppException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )


@chat_router.get(
    "/{chat_id}",
    response_model=ChatDetailResponse,
)
async def get_chat_detail(
    chat_id: int,
    current_user: User = Depends(get_current_chat_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await chat_service.get_chat_detail(
            db=db,
            chat_id=chat_id,
            current_user=current_user,
        )
    except BaseAppException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )


@chat_router.get(
    "/{chat_id}/messages",
    response_model=list[ChatMessageResponse],
)
async def get_chat_messages(
    chat_id: int,
    current_user: User = Depends(get_current_chat_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    try:
        return await chat_service.get_chat_messages(
            db=db,
            chat_id=chat_id,
            current_user=current_user,
            skip=skip,
            limit=limit,
        )
    except BaseAppException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )


@chat_router.post(
    "/{chat_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_chat_message_http(
    chat_id: int,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_chat_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await chat_service.send_message(
            db=db,
            chat_id=chat_id,
            current_user=current_user,
            message_data=message_data,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except BaseAppException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )


@chat_router.post(
    "/{chat_id}/read",
    response_model=ChatReadResponse,
)
async def mark_chat_as_read(
    chat_id: int,
    current_user: User = Depends(get_current_chat_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await chat_service.mark_chat_as_read(
            db=db,
            chat_id=chat_id,
            current_user=current_user,
        )
    except BaseAppException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )


@chat_router.websocket("/{chat_id}/ws")
async def chat_websocket(
    websocket: WebSocket,
    chat_id: int,
):
    user_id: int | None = None

    async with async_session() as db:
        current_user = await get_current_user_from_ws(
            websocket=websocket,
            db=db,
        )

        if not current_user:
            return

        user_id = current_user.id

        try:
            await chat_service.check_user_has_chat_access(
                db=db,
                chat_id=chat_id,
                current_user=current_user,
            )
        except BaseAppException as e:
            await websocket.close(
                code=1008,
                reason=e.message,
            )
            return

    await chat_ws_manager.connect(
        chat_id=chat_id,
        user_id=user_id,
        websocket=websocket,
    )

    await set_user_online_status(
        user_id=user_id,
        is_online=True,
    )

    await chat_ws_manager.broadcast_to_chat(
        chat_id=chat_id,
        payload={
            "type": "user_online",
            "user_id": user_id,
            "is_online": True,
        },
    )

    await websocket.send_json(
        {
            "type": "connected",
            "chat_id": chat_id,
            "user_id": user_id,
            "message": "WebSocket connected",
        }
    )

    try:
        while True:
            data = await websocket.receive_json()

            event_type = data.get("type", "message")

            if event_type == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                    }
                )
                continue

            if event_type == "read":
                async with async_session() as db:
                    current_user = await authcrud.get_with_role(
                        db=db,
                        user_id=user_id,
                    )

                    if not current_user:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "detail": "Пользователь не найден",
                            }
                        )
                        continue

                    try:
                        read_result = await chat_service.mark_chat_as_read(
                            db=db,
                            chat_id=chat_id,
                            current_user=current_user,
                        )
                    except BaseAppException as e:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "detail": e.message,
                            }
                        )
                        continue

                await chat_ws_manager.broadcast_to_chat(
                    chat_id=chat_id,
                    payload={
                        "type": "read",
                        "chat_id": chat_id,
                        "user_id": user_id,
                        "read_messages_count": read_result["read_messages_count"],
                        "read_at": jsonable_encoder(read_result["read_at"]),
                    },
                )

                continue

            if event_type != "message":
                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": "Unknown event type",
                    }
                )
                continue

            text = str(data.get("text") or "").strip()

            if not text:
                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": "Сообщение не может быть пустым",
                    }
                )
                continue

            async with async_session() as db:
                current_user = await authcrud.get_with_role(
                    db=db,
                    user_id=user_id,
                )

                if not current_user:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "detail": "Пользователь не найден",
                        }
                    )
                    continue

                try:
                    message = await chat_service.send_message(
                        db=db,
                        chat_id=chat_id,
                        current_user=current_user,
                        message_data=ChatMessageCreate(text=text),
                    )
                except BaseAppException as e:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "detail": e.message,
                        }
                    )
                    continue
                except ValueError as e:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "detail": str(e),
                        }
                    )
                    continue

            await chat_ws_manager.broadcast_to_chat(
                chat_id=chat_id,
                payload={
                    "type": "message",
                    "message": jsonable_encoder(message),
                },
            )

    except WebSocketDisconnect:
        pass

    finally:
        if user_id is not None:
            chat_ws_manager.disconnect(
                chat_id=chat_id,
                user_id=user_id,
                websocket=websocket,
            )

            if not chat_ws_manager.is_user_online(user_id):
                await set_user_online_status(
                    user_id=user_id,
                    is_online=False,
                )

                await chat_ws_manager.broadcast_to_chat(
                    chat_id=chat_id,
                    payload={
                        "type": "user_online",
                        "user_id": user_id,
                        "is_online": False,
                        "last_seen_at": jsonable_encoder(utc_now_naive()),
                    },
                )