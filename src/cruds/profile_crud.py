from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import Profile

class ProfileCrud(BaseCrud):
    def __init__(self):
        super().__init__(Profile)

    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> Profile | None:
        stmt = select(Profile).where(Profile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

profilecrud = ProfileCrud()