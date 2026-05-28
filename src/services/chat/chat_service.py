from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AccessDeniedError
from src.cruds.chat.chat_crud import chatcrud, messagecrud
from src.models.model import Chat, User
from src.schemas.chat.chat_schema import ChatMessageCreate


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ChatService:
    def __init__(self):
        self.chatcrud = chatcrud
        self.messagecrud = messagecrud

    def _get_last_message(self, chat: Chat):
        if not chat.messages:
            return None

        return sorted(
            chat.messages,
            key=lambda message: message.created_at,
        )[-1]

    def _is_applicant_chat_member(
        self,
        chat: Chat,
        applicant_id: int,
    ) -> bool:
        application = chat.application

        if not application:
            return False

        resume = application.resume

        if not resume:
            return False

        return resume.applicant_id == applicant_id

    def _is_company_chat_member(
        self,
        chat: Chat,
        company_id: int,
    ) -> bool:
        application = chat.application

        if not application:
            return False

        vacancy = application.vacancy

        if not vacancy:
            return False

        return vacancy.company_id == company_id

    def _check_chat_access(
        self,
        chat: Chat,
        current_user: User,
    ) -> None:
        if current_user.applicant_id:
            if self._is_applicant_chat_member(
                chat=chat,
                applicant_id=current_user.applicant_id,
            ):
                return

        if current_user.company_id:
            if self._is_company_chat_member(
                chat=chat,
                company_id=current_user.company_id,
            ):
                return

        raise AccessDeniedError("У вас нет доступа к этому чату")

    def _serialize_message(self, message) -> dict[str, Any]:
        return {
            "id": message.id,
            "chat_id": message.chat_id,
            "sender_id": message.sender_id,
            "text": message.text,
            "created_at": message.created_at,
            "read_at": message.read_at,
            "sender": {
                "id": message.sender.id,
                "email": message.sender.email,
                "is_online": message.sender.is_online,
                "last_seen_at": message.sender.last_seen_at,
            } if message.sender else None,
            "attachments": [
                {
                    "id": attachment.id,
                    "file_url": attachment.file_url,
                    "file_name": attachment.file_name,
                    "file_type": attachment.file_type,
                    "file_size": attachment.file_size,
                    "created_at": attachment.created_at,
                }
                for attachment in message.attachments
            ],
        }

    async def _serialize_chat_list_item(
        self,
        db: AsyncSession,
        chat: Chat,
        current_user: User,
    ) -> dict[str, Any]:
        last_message = self._get_last_message(chat)

        unread_count = await self.messagecrud.count_unread_by_chat_id(
            db=db,
            chat_id=chat.id,
            current_user_id=current_user.id,
        )

        return {
            "id": chat.id,
            "application_id": chat.application_id,
            "created_at": chat.created_at,
            "application": {
                "id": chat.application.id,
                "vacancy_id": chat.application.vacancy_id,
                "resume_id": chat.application.resume_id,
                "status": chat.application.status,
                "created_at": chat.application.created_at,
            } if chat.application else None,
            "last_message": self._serialize_message(last_message) if last_message else None,
            "unread_count": unread_count,
        }

    def _serialize_chat_detail(self, chat: Chat) -> dict[str, Any]:
        return {
            "id": chat.id,
            "application_id": chat.application_id,
            "created_at": chat.created_at,
            "application": {
                "id": chat.application.id,
                "vacancy_id": chat.application.vacancy_id,
                "resume_id": chat.application.resume_id,
                "status": chat.application.status,
                "created_at": chat.application.created_at,
            } if chat.application else None,
            "messages": [
                self._serialize_message(message)
                for message in sorted(
                    chat.messages,
                    key=lambda item: item.created_at,
                )
            ],
        }

    async def get_my_chats(
        self,
        db: AsyncSession,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
    ):
        if current_user.applicant_id:
            chats = await self.chatcrud.get_by_applicant_id(
                db=db,
                applicant_id=current_user.applicant_id,
                skip=skip,
                limit=limit,
            )

            result = []

            for chat in chats:
                result.append(
                    await self._serialize_chat_list_item(
                        db=db,
                        chat=chat,
                        current_user=current_user,
                    )
                )

            return result

        if current_user.company_id:
            chats = await self.chatcrud.get_by_company_id(
                db=db,
                company_id=current_user.company_id,
                skip=skip,
                limit=limit,
            )

            result = []

            for chat in chats:
                result.append(
                    await self._serialize_chat_list_item(
                        db=db,
                        chat=chat,
                        current_user=current_user,
                    )
                )

            return result

        raise AccessDeniedError("У пользователя нет профиля соискателя или компании")

    async def get_chat_detail(
        self,
        db: AsyncSession,
        chat_id: int,
        current_user: User,
    ):
        chat = await self.chatcrud.get_with_details(
            db=db,
            chat_id=chat_id,
        )

        if not chat:
            raise AccessDeniedError("Чат не найден или нет доступа")

        self._check_chat_access(
            chat=chat,
            current_user=current_user,
        )

        return self._serialize_chat_detail(chat)

    async def get_chat_messages(
        self,
        db: AsyncSession,
        chat_id: int,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
    ):
        chat = await self.chatcrud.get_with_details(
            db=db,
            chat_id=chat_id,
        )

        if not chat:
            raise AccessDeniedError("Чат не найден или нет доступа")

        self._check_chat_access(
            chat=chat,
            current_user=current_user,
        )

        messages = await self.messagecrud.get_by_chat_id(
            db=db,
            chat_id=chat_id,
            skip=skip,
            limit=limit,
        )

        return [
            self._serialize_message(message)
            for message in messages
        ]

    async def send_message(
        self,
        db: AsyncSession,
        chat_id: int,
        current_user: User,
        message_data: ChatMessageCreate,
    ):
        chat = await self.chatcrud.get_with_details(
            db=db,
            chat_id=chat_id,
        )

        if not chat:
            raise AccessDeniedError("Чат не найден или нет доступа")

        self._check_chat_access(
            chat=chat,
            current_user=current_user,
        )

        text = message_data.text.strip()

        if not text:
            raise ValueError("Сообщение не может быть пустым")

        message = await self.messagecrud.create(
            db=db,
            obj_data={
                "chat_id": chat_id,
                "sender_id": current_user.id,
                "text": text,
                "created_at": utc_now_naive(),
                "read_at": None,
            },
        )

        await db.commit()

        messages = await self.messagecrud.get_by_chat_id(
            db=db,
            chat_id=chat_id,
            skip=0,
            limit=1_000_000,
        )

        created_message = next(
            item for item in messages if item.id == message.id
        )

        return self._serialize_message(created_message)

    async def mark_chat_as_read(
        self,
        db: AsyncSession,
        chat_id: int,
        current_user: User,
    ):
        chat = await self.chatcrud.get_with_details(
            db=db,
            chat_id=chat_id,
        )

        if not chat:
            raise AccessDeniedError("Чат не найден или нет доступа")

        self._check_chat_access(
            chat=chat,
            current_user=current_user,
        )

        read_at = utc_now_naive()

        read_messages_count = await self.messagecrud.mark_chat_messages_as_read(
            db=db,
            chat_id=chat_id,
            current_user_id=current_user.id,
            read_at=read_at,
        )

        await db.commit()

        return {
            "chat_id": chat_id,
            "read_messages_count": read_messages_count,
            "read_at": read_at,
        }

    async def check_user_has_chat_access(
        self,
        db: AsyncSession,
        chat_id: int,
        current_user: User,
    ) -> Chat:
        chat = await self.chatcrud.get_with_details(
            db=db,
            chat_id=chat_id,
        )

        if not chat:
            raise AccessDeniedError("Чат не найден или нет доступа")

        self._check_chat_access(
            chat=chat,
            current_user=current_user,
        )

        return chat


chat_service = ChatService()