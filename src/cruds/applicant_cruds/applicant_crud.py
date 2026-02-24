from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.cruds.base_crud import BaseCrud
from src.models.model import Applicant, Profile, Resume

class ApplicantCrud(BaseCrud):
    def __init__(self):
        super().__init__(Applicant)

    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> Applicant | None:
        stmt = select(Applicant).join(Profile, Profile.applicant_id == Applicant.id).where(Profile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_user_id_with_details(self, db: AsyncSession, user_id: int) -> Applicant | None:
        stmt = select(Applicant).join(Profile).where(Profile.user_id == user_id).options(
            selectinload(Applicant.city),
            selectinload(Applicant.profile),
            selectinload(Applicant.resumes).selectinload(Resume.profession), 
            selectinload(Applicant.resumes).selectinload(Resume.skills),
            selectinload(Applicant.resumes).selectinload(Resume.work_experiences),
            selectinload(Applicant.resumes).selectinload(Resume.educations)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

applicantcrud = ApplicantCrud()