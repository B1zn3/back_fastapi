from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import Profession

class ProfessionCrud(BaseCrud):
    def __init__(self):
        super().__init__(Profession)

    async def get_or_create(self, db: AsyncSession, name: str) -> Profession:
        result = await db.execute(select(Profession).where(Profession.name == name))
        prof = result.scalar_one_or_none()
        if not prof:
            prof = Profession(name=name)
            db.add(prof)
            await db.flush()
        return prof

professioncrud = ProfessionCrud()