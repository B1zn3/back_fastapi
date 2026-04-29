from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.cruds.base_crud import BaseCrud
from src.models.model import Application, Resume, Vacancy


class ApplicationCrud(BaseCrud):
    def __init__(self):
        super().__init__(Application)

    def _detail_options(self):
        return (
            selectinload(Application.vacancy).selectinload(Vacancy.company),
            selectinload(Application.vacancy).selectinload(Vacancy.city),
            selectinload(Application.vacancy).selectinload(Vacancy.currency),
            selectinload(Application.vacancy).selectinload(Vacancy.profession),
            selectinload(Application.resume).selectinload(Resume.profession),
        )

    async def get_by_vacancy_and_resume(
        self,
        db: AsyncSession,
        vacancy_id: int,
        resume_id: int,
    ) -> Application | None:
        stmt = (
            select(Application)
            .options(*self._detail_options())
            .where(
                and_(
                    Application.vacancy_id == vacancy_id,
                    Application.resume_id == resume_id,
                )
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_vacancy_and_applicant(
        self,
        db: AsyncSession,
        vacancy_id: int,
        applicant_id: int,
    ) -> Application | None:
        stmt = (
            select(Application)
            .options(*self._detail_options())
            .join(Resume, Resume.id == Application.resume_id)
            .where(
                and_(
                    Application.vacancy_id == vacancy_id,
                    Resume.applicant_id == applicant_id,
                )
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_vacancy(
        self,
        db: AsyncSession,
        vacancy_id: int,
        skip: int = 0,
        limit: int = 10,
    ) -> list[Application]:
        stmt = (
            select(Application)
            .options(*self._detail_options())
            .where(Application.vacancy_id == vacancy_id)
            .order_by(Application.created_at.desc(), Application.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        skip: int = 0,
        limit: int = 10,
    ) -> list[Application]:
        stmt = (
            select(Application)
            .options(*self._detail_options())
            .where(Application.resume_id == resume_id)
            .order_by(Application.created_at.desc(), Application.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_applicant(
        self,
        db: AsyncSession,
        applicant_id: int,
        skip: int = 0,
        limit: int = 10,
    ) -> list[Application]:
        stmt = (
            select(Application)
            .options(*self._detail_options())
            .join(Resume, Resume.id == Application.resume_id)
            .where(Resume.applicant_id == applicant_id)
            .order_by(Application.created_at.desc(), Application.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


applicationcrud = ApplicationCrud()