from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import City

class CityCrud(BaseCrud):
    def __init__(self):
        super().__init__(City)

    async def get_or_create(self, db: AsyncSession, name: str) -> City:
        result = await db.execute(select(City).where(City.name == name))
        city = result.scalar_one_or_none()
        if not city:
            raise HTTPException(status_code=422, detail="Выберите город только из списка.")
        return city

citycrud = CityCrud()