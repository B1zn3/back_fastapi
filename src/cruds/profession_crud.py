from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import Profession

class ProfessionCrud(BaseCrud):
    def __init__(self):
        super().__init__(Profession)

    async def get_by_name(self, db: AsyncSession, name: str) -> Profession | None:
        stmt = select(Profession).where(Profession.name == name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

professioncrud = ProfessionCrud()