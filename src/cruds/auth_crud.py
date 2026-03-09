from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.cruds.base_crud import BaseCrud
from src.models.model import User

class AuthCrud(BaseCrud):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_email_with_role(self, db: AsyncSession, email: str) -> User | None:
        stmt = select(User).where(User.email == email).options(
            selectinload(User.role)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_role(self, db: AsyncSession, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id).options(
            selectinload(User.role)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

authcrud = AuthCrud()