from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.cruds.base_crud import BaseCrud
from src.models.model import Applicant, User


class AuthCrud(BaseCrud):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_email_with_role(self, db: AsyncSession, email: str) -> User | None:
        stmt = (
            select(User)
            .where(User.email == email)
            .options(selectinload(User.role))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_role(self, db: AsyncSession, user_id: int) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.role))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_applicant_for_user(self, db: AsyncSession, user_id: int) -> Applicant | None:
        stmt = (
            select(Applicant)
            .join(User, User.applicant_id == Applicant.id)
            .where(User.id == user_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def is_email_taken_by_other(
        self,
        db: AsyncSession,
        email: str,
        user_id: int,
    ) -> bool:
        stmt = select(User).where(User.email == email, User.id != user_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        return existing is not None

    async def update_user_email(
        self,
        db: AsyncSession,
        user: User,
        email: str,
    ) -> User:
        user.email = email
        user.updated_at = datetime.utcnow()
        await db.flush()
        return user

    async def update_user_password(
        self,
        db: AsyncSession,
        user: User,
        password_hash: str,
    ) -> User:
        user.password = password_hash
        user.updated_at = datetime.utcnow()
        await db.flush()
        return user

    async def update_applicant_phone(
        self,
        db: AsyncSession,
        applicant: Applicant,
        phone: str | None,
    ) -> Applicant:
        applicant.phone = phone
        await db.flush()
        return applicant

    async def commit(self, db: AsyncSession):
        await db.commit()

    async def refresh_user(self, db: AsyncSession, user: User):
        await db.refresh(user)

    async def refresh_applicant(self, db: AsyncSession, applicant: Applicant):
        await db.refresh(applicant)

    async def is_phone_taken_by_other(
        self,
        db: AsyncSession,
        phone: str,
        applicant_id: int,
    ) -> bool:
        stmt = select(Applicant).where(
            Applicant.phone == phone,
            Applicant.id != applicant_id,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        return existing is not None

authcrud = AuthCrud()