from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import City

class CityCrud(BaseCrud):
    def __init__(self):
        super().__init__(City)

    async def get_by_name(self, db: AsyncSession, name: str) -> City | None:
        stmt = select(City).where(City.name == name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, db: AsyncSession, name: str) -> City:
        city = await self.get_by_name(db, name)
        if not city:
            city = await self.create(db, {"name": name})
            await db.flush()
        return city

citycrud = CityCrud()