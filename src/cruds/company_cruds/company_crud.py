from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import Company, Profile

class CompanyCrud(BaseCrud):
    def __init__(self):
        super().__init__(Company)

    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> Company | None:
        stmt = select(Company).join(Profile, Profile.company_id == Company.id).where(Profile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

companycrud = CompanyCrud()