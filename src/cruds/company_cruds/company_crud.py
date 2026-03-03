from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.cruds.base_crud import BaseCrud
from src.models.model import Company, Vacancy, User

class CompanyCrud(BaseCrud):
    def __init__(self):
        super().__init__(Company)

    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> Company | None:
        stmt = select(Company).join(User, User.company_id == Company.id).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id_with_details(self, db: AsyncSession, user_id: int) -> Company | None:
        stmt = select(Company).join(User, User.company_id == Company.id).where(User.id == user_id).options(
            selectinload(Company.vacancies).selectinload(Vacancy.profession),
            selectinload(Company.vacancies).selectinload(Vacancy.city),
            selectinload(Company.vacancies).selectinload(Vacancy.employment_type),
            selectinload(Company.vacancies).selectinload(Vacancy.work_schedule),
            selectinload(Company.vacancies).selectinload(Vacancy.currency),
            selectinload(Company.vacancies).selectinload(Vacancy.experience),
            selectinload(Company.vacancies).selectinload(Vacancy.status),
            selectinload(Company.vacancies).selectinload(Vacancy.skills)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

companycrud = CompanyCrud()