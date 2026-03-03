from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.cruds.base_crud import BaseCrud
from src.models.model import Resume, WorkExperience, Education

class ResumeCrud(BaseCrud):
    def __init__(self):
        super().__init__(Resume)

    async def get_by_applicant(self, db: AsyncSession, applicant_id: int):
        stmt = select(Resume).where(Resume.applicant_id == applicant_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_with_details(self, db: AsyncSession, resume_id: int):
        stmt = (
            select(Resume)
            .where(Resume.id == resume_id)
            .options(
                selectinload(Resume.profession),
                selectinload(Resume.skills),
                selectinload(Resume.work_experiences),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_applicant_with_details(self, db: AsyncSession, applicant_id: int):
        stmt = (
            select(Resume)
            .where(Resume.applicant_id == applicant_id)
            .options(
                selectinload(Resume.profession),
                selectinload(Resume.skills),
                selectinload(Resume.work_experiences),
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()

resumecrud = ResumeCrud()