from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cruds.base_crud import BaseCrud
from src.models.model import Application, Resume


class ApplicationCrud(BaseCrud):
    def __init__(self):
        super().__init__(Application)

    async def get_by_vacancy_and_resume(
        self,
        db: AsyncSession,
        vacancy_id: int,
        resume_id: int,
    ) -> Application | None:
        stmt = select(Application).where(
            and_(
                Application.vacancy_id == vacancy_id,
                Application.resume_id == resume_id,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_vacancy(self, db: AsyncSession, vacancy_id: int) -> list[Application]:
        stmt = (
            select(Application)
            .where(Application.vacancy_id == vacancy_id)
            .order_by(Application.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_resume(self, db: AsyncSession, resume_id: int) -> list[Application]:
        stmt = (
            select(Application)
            .where(Application.resume_id == resume_id)
            .order_by(Application.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_applicant(self, db: AsyncSession, applicant_id: int) -> list[Application]:
        stmt = (
            select(Application)
            .join(Resume, Resume.id == Application.resume_id)
            .where(Resume.applicant_id == applicant_id)
            .order_by(Application.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()


applicationcrud = ApplicationCrud()