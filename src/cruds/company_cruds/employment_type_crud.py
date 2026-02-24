from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import EmploymentType

class EmploymentTypeCrud(BaseCrud):
    def __init__(self):
        super().__init__(EmploymentType)

    async def get_by_name(self, db: AsyncSession, name: str) -> EmploymentType | None:
        stmt = select(EmploymentType).where(EmploymentType.name == name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

employmenttypecrud = EmploymentTypeCrud()