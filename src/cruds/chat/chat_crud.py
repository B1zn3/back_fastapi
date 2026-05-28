from datetime import datetime
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.cruds.base_crud import BaseCrud
from src.models.model import (
    Application,
    Chat,
    Message,
    MessageAttachment,
    Resume,
    Vacancy,
)


class ChatCrud(BaseCrud):
    def __init__(self):
        super().__init__(Chat)

    async def get_by_application_id(
        self,
        db: AsyncSession,
        application_id: int,
    ) -> Optional[Chat]:
        result = await db.execute(
            select(Chat)
            .where(Chat.application_id == application_id)
            .options(
                selectinload(Chat.application),
                selectinload(Chat.messages).selectinload(Message.sender),
                selectinload(Chat.messages).selectinload(Message.attachments),
            )
        )

        return result.scalar_one_or_none()

    async def get_with_details(
        self,
        db: AsyncSession,
        chat_id: int,
    ) -> Optional[Chat]:
        result = await db.execute(
            select(Chat)
            .where(Chat.id == chat_id)
            .options(
                selectinload(Chat.application)
                .selectinload(Application.vacancy)
                .selectinload(Vacancy.company),
                selectinload(Chat.application)
                .selectinload(Application.resume)
                .selectinload(Resume.applicant),
                selectinload(Chat.messages).selectinload(Message.sender),
                selectinload(Chat.messages).selectinload(Message.attachments),
            )
        )

        return result.scalar_one_or_none()

    async def get_by_applicant_id(
        self,
        db: AsyncSession,
        applicant_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Chat]:
        result = await db.execute(
            select(Chat)
            .join(Application, Application.id == Chat.application_id)
            .join(Resume, Resume.id == Application.resume_id)
            .where(Resume.applicant_id == applicant_id)
            .options(
                selectinload(Chat.application),
                selectinload(Chat.messages).selectinload(Message.sender),
                selectinload(Chat.messages).selectinload(Message.attachments),
            )
            .order_by(Chat.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return list(result.scalars().unique().all())

    async def get_by_company_id(
        self,
        db: AsyncSession,
        company_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Chat]:
        result = await db.execute(
            select(Chat)
            .join(Application, Application.id == Chat.application_id)
            .join(Vacancy, Vacancy.id == Application.vacancy_id)
            .where(Vacancy.company_id == company_id)
            .options(
                selectinload(Chat.application),
                selectinload(Chat.messages).selectinload(Message.sender),
                selectinload(Chat.messages).selectinload(Message.attachments),
            )
            .order_by(Chat.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return list(result.scalars().unique().all())


class MessageCrud(BaseCrud):
    def __init__(self):
        super().__init__(Message)

    async def get_by_chat_id(
        self,
        db: AsyncSession,
        chat_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .options(
                selectinload(Message.sender),
                selectinload(Message.attachments),
            )
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )

        return list(result.scalars().unique().all())

    async def count_unread_by_chat_id(
        self,
        db: AsyncSession,
        chat_id: int,
        current_user_id: int,
    ) -> int:
        result = await db.execute(
            select(func.count(Message.id))
            .where(Message.chat_id == chat_id)
            .where(Message.sender_id != current_user_id)
            .where(Message.read_at.is_(None))
        )

        return result.scalar_one()

    async def mark_chat_messages_as_read(
        self,
        db: AsyncSession,
        chat_id: int,
        current_user_id: int,
        read_at: datetime,
    ) -> int:
        result = await db.execute(
            update(Message)
            .where(Message.chat_id == chat_id)
            .where(Message.sender_id != current_user_id)
            .where(Message.read_at.is_(None))
            .values(read_at=read_at)
        )

        return result.rowcount or 0


class MessageAttachmentCrud(BaseCrud):
    def __init__(self):
        super().__init__(MessageAttachment)


chatcrud = ChatCrud()
messagecrud = MessageCrud()
messageattachmentcrud = MessageAttachmentCrud()