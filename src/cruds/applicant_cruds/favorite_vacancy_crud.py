from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.model import (
    FavoriteVacancy,
    Resume,
    Vacancy,
    resume_favorite_vacancies,
)


class FavoriteVacancyCrud:
    def _favorite_options(self):
        return (
            selectinload(FavoriteVacancy.vacancy).selectinload(Vacancy.company),
            selectinload(FavoriteVacancy.vacancy).selectinload(Vacancy.city),
            selectinload(FavoriteVacancy.vacancy).selectinload(Vacancy.profession),
            selectinload(FavoriteVacancy.vacancy).selectinload(Vacancy.employment_type),
            selectinload(FavoriteVacancy.vacancy).selectinload(Vacancy.work_schedule),
            selectinload(FavoriteVacancy.vacancy).selectinload(Vacancy.currency),
            selectinload(FavoriteVacancy.vacancy).selectinload(Vacancy.experience),
            selectinload(FavoriteVacancy.vacancy).selectinload(Vacancy.status),
            selectinload(FavoriteVacancy.vacancy).selectinload(Vacancy.skills),
        )

    async def get_by_id(
        self,
        db: AsyncSession,
        favorite_id: int,
    ) -> FavoriteVacancy | None:
        stmt = (
            select(FavoriteVacancy)
            .options(*self._favorite_options())
            .where(FavoriteVacancy.id == favorite_id)
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_vacancy_id(
        self,
        db: AsyncSession,
        vacancy_id: int,
    ) -> FavoriteVacancy | None:
        stmt = (
            select(FavoriteVacancy)
            .options(*self._favorite_options())
            .where(FavoriteVacancy.vacancy_id == vacancy_id)
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        vacancy_id: int,
    ) -> FavoriteVacancy:
        favorite = FavoriteVacancy(vacancy_id=vacancy_id)

        db.add(favorite)
        await db.flush()

        return favorite

    async def link_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        favorite_vacancy_id: int,
    ) -> bool:
        exists_stmt = (
            select(resume_favorite_vacancies.c.resume_id)
            .where(
                resume_favorite_vacancies.c.resume_id == resume_id,
                resume_favorite_vacancies.c.favorite_vacancy_id == favorite_vacancy_id,
            )
        )

        exists_result = await db.execute(exists_stmt)

        if exists_result.scalar_one_or_none() is not None:
            return False

        await db.execute(
            insert(resume_favorite_vacancies).values(
                resume_id=resume_id,
                favorite_vacancy_id=favorite_vacancy_id,
            )
        )

        await db.flush()

        return True

    async def unlink_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        favorite_vacancy_id: int,
    ) -> bool:
        result = await db.execute(
            delete(resume_favorite_vacancies).where(
                resume_favorite_vacancies.c.resume_id == resume_id,
                resume_favorite_vacancies.c.favorite_vacancy_id == favorite_vacancy_id,
            )
        )

        await db.flush()

        return bool(result.rowcount)

    async def count_links(
        self,
        db: AsyncSession,
        favorite_vacancy_id: int,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(resume_favorite_vacancies)
            .where(resume_favorite_vacancies.c.favorite_vacancy_id == favorite_vacancy_id)
        )

        result = await db.execute(stmt)
        return int(result.scalar_one() or 0)

    async def delete_favorite_record(
        self,
        db: AsyncSession,
        favorite_vacancy_id: int,
    ) -> None:
        await db.execute(
            delete(FavoriteVacancy).where(FavoriteVacancy.id == favorite_vacancy_id)
        )

        await db.flush()

    async def get_for_resume_and_vacancy(
        self,
        db: AsyncSession,
        resume_id: int,
        vacancy_id: int,
    ) -> tuple[FavoriteVacancy, Resume] | None:
        stmt = (
            select(FavoriteVacancy, Resume)
            .join(
                resume_favorite_vacancies,
                resume_favorite_vacancies.c.favorite_vacancy_id == FavoriteVacancy.id,
            )
            .join(Resume, Resume.id == resume_favorite_vacancies.c.resume_id)
            .options(
                *self._favorite_options(),
                selectinload(Resume.profession),
            )
            .where(
                Resume.id == resume_id,
                FavoriteVacancy.vacancy_id == vacancy_id,
            )
        )

        result = await db.execute(stmt)
        row = result.first()

        if not row:
            return None

        return row[0], row[1]

    async def get_first_for_applicant_and_vacancy(
        self,
        db: AsyncSession,
        applicant_id: int,
        vacancy_id: int,
    ) -> tuple[FavoriteVacancy, Resume] | None:
        stmt = (
            select(FavoriteVacancy, Resume)
            .join(
                resume_favorite_vacancies,
                resume_favorite_vacancies.c.favorite_vacancy_id == FavoriteVacancy.id,
            )
            .join(Resume, Resume.id == resume_favorite_vacancies.c.resume_id)
            .options(
                *self._favorite_options(),
                selectinload(Resume.profession),
            )
            .where(
                Resume.applicant_id == applicant_id,
                FavoriteVacancy.vacancy_id == vacancy_id,
            )
            .order_by(Resume.updated_at.desc(), Resume.id.desc())
            .limit(1)
        )

        result = await db.execute(stmt)
        row = result.first()

        if not row:
            return None

        return row[0], row[1]

    async def get_by_applicant(
        self,
        db: AsyncSession,
        applicant_id: int,
        skip: int = 0,
        limit: int = 10,
        resume_id: int | None = None,
    ) -> list[tuple[FavoriteVacancy, Resume]]:
        stmt = (
            select(FavoriteVacancy, Resume)
            .join(
                resume_favorite_vacancies,
                resume_favorite_vacancies.c.favorite_vacancy_id == FavoriteVacancy.id,
            )
            .join(Resume, Resume.id == resume_favorite_vacancies.c.resume_id)
            .options(
                *self._favorite_options(),
                selectinload(Resume.profession),
            )
            .where(Resume.applicant_id == applicant_id)
            .order_by(FavoriteVacancy.id.desc())
            .offset(skip)
            .limit(limit)
        )

        if resume_id is not None:
            stmt = stmt.where(Resume.id == resume_id)

        result = await db.execute(stmt)
        rows = result.all()

        return [(row[0], row[1]) for row in rows]


favoritevacancycrud = FavoriteVacancyCrud()