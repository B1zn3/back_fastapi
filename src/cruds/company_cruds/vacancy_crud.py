from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.cruds.base_crud import BaseCrud
from src.models.model import Vacancy

class VacancyCrud(BaseCrud):
    def __init__(self):
        super().__init__(Vacancy)

    async def get_by_company(self, db: AsyncSession, company_id: int):
        stmt = select(Vacancy).where(Vacancy.company_id == company_id)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_company_with_details(
        self, 
        db: AsyncSession, 
        company_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[Vacancy]:
        """Получить все вакансии компании с пагинацией"""
        result = await db.execute(
            select(Vacancy)
            .where(Vacancy.company_id == company_id)
            .options(
                selectinload(Vacancy.profession),
                selectinload(Vacancy.city),
                selectinload(Vacancy.employment_type),
                selectinload(Vacancy.work_schedule),
                selectinload(Vacancy.currency),
                selectinload(Vacancy.experience),
                selectinload(Vacancy.status),
                selectinload(Vacancy.skills)  # company не обязателен для списка
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_with_details(self, db: AsyncSession, vacancy_id: int):
        stmt = select(Vacancy).where(Vacancy.id == vacancy_id).options(
            selectinload(Vacancy.profession),
            selectinload(Vacancy.employment_type),
            selectinload(Vacancy.work_schedule),
            selectinload(Vacancy.skills)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

vacancycrud = VacancyCrud()