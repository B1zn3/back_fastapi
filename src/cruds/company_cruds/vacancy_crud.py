from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import Vacancy

class VacancyCrud(BaseCrud):
    def __init__(self):
        super().__init__(Vacancy)

    async def get_active(self, db: AsyncSession, vacancy_id: int) -> Vacancy | None:
        stmt = select(Vacancy).where(Vacancy.id == vacancy_id, Vacancy.is_active)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_company(self, db: AsyncSession, company_id: int) -> list[Vacancy]:
        stmt = select(Vacancy).where(Vacancy.company_id == company_id)
        result = await db.execute(stmt)
        return result.scalars().all()

vacancycrud = VacancyCrud()