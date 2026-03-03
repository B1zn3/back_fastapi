from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging

from src.cruds.applicant_cruds.applicant_crud import applicantcrud
from src.cruds.applicant_cruds.resume_crud import resumecrud
from src.cruds.applicant_cruds.work_experience_crud import workexperiencecrud
from src.cruds.applicant_cruds.education_crud import educationcrud
from src.cruds.city_crud import citycrud
from src.cruds.profession_crud import professioncrud
from src.cruds.skill_crud import skillcrud
from src.cruds.educational_institution_crud import educationalinstitutioncrud
from src.schemas.applicant_schemas.applicant_schema import ApplicantUpdate
from src.schemas.applicant_schemas.resume_schema import ResumeCreate, ResumeUpdate
from src.schemas.applicant_schemas.work_experience_schema import WorkExperienceCreate, WorkExperienceUpdate
from src.schemas.applicant_schemas.education_schema import EducationCreate, EducationUpdate
from src.models.model import Applicant, Resume

logger = logging.getLogger(__name__)

class ApplicantService:
    def __init__(self):
        self.applicantcrud = applicantcrud
        self.resumecrud = resumecrud
        self.workexperiencecrud = workexperiencecrud
        self.educationcrud = educationcrud
        self.citycrud = citycrud
        self.professioncrud = professioncrud
        self.skillcrud = skillcrud
        self.educationalinstitutioncrud = educationalinstitutioncrud

    # ---------- Вспомогательные методы для проверки владения ----------
    async def _get_resume_or_404(self, db: AsyncSession, resume_id: int, applicant_id: int) -> Resume:
        resume = await self.resumecrud.get(db, resume_id)
        if not resume or resume.applicant_id != applicant_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
        return resume

    async def _get_work_exp_or_404(self, db: AsyncSession, exp_id: int, resume_id: int, applicant_id: int):
        exp = await self.workexperiencecrud.get(db, exp_id)
        if not exp or exp.resume_id != resume_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Work experience not found")
        await self._get_resume_or_404(db, resume_id, applicant_id)
        return exp

    # ---------- Профиль ----------
    async def get_profile(self, applicant: Applicant):
        return applicant

    async def update_profile(self, db: AsyncSession, applicant: Applicant, update_data: ApplicantUpdate):
        try:
            # Обновляем поля, кроме city_name
            for field, value in update_data.model_dump(exclude_unset=True, exclude={"city_name"}).items():
                setattr(applicant, field, value)
            if update_data.city_name:
                city = await self.citycrud.get_or_create(db, update_data.city_name)
                applicant.city_id = city.id
            await db.commit()
            await db.refresh(applicant, ["city"])
            return applicant
        except (IntegrityError, SQLAlchemyError) as e:
            await db.rollback()
            logger.error(f"DB error in update_profile: {e}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Data error")
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    # ---------- Резюме ----------
    async def create_resume(self, db: AsyncSession, applicant_id: int, data: ResumeCreate):
        try:
            resume_dict = data.model_dump()
            resume_dict["applicant_id"] = applicant_id
            resume_dict["created_at"] = resume_dict["updated_at"] = datetime.utcnow()
            resume = await self.resumecrud.create(db, resume_dict)
            await db.commit()
            await db.refresh(resume, ["profession", "skills", "work_experiences"])
            return resume
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid profession_id or duplicate")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    async def get_resumes(self, db: AsyncSession, applicant_id: int):
        return await self.resumecrud.get_by_applicant_with_details(db, applicant_id)

    async def get_resume_detail(self, db: AsyncSession, resume_id: int, applicant_id: int):
        resume = await self.resumecrud.get_with_details(db, resume_id)
        if not resume or resume.applicant_id != applicant_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
        return resume

    async def update_resume(self, db: AsyncSession, resume_id: int, applicant_id: int, data: ResumeUpdate):
        resume = await self._get_resume_or_404(db, resume_id, applicant_id)
        try:
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(resume, field, value)
            resume.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(resume, ["profession", "skills", "work_experiences"])
            return resume
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    async def delete_resume(self, db: AsyncSession, resume_id: int, applicant_id: int):
        resume = await self._get_resume_or_404(db, resume_id, applicant_id)
        try:
            await self.resumecrud.delete(db, resume_id)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    # ---------- Навыки резюме ----------
    async def add_skill_to_resume(self, db: AsyncSession, resume_id: int, applicant_id: int, skill_name: str):
        resume = await self._get_resume_or_404(db, resume_id, applicant_id)
        try:
            skill = await self.skillcrud.get_or_create(db, skill_name)
            if skill not in resume.skills:
                resume.skills.append(skill)
                await db.commit()
                await db.refresh(resume, ["skills"])
            return resume
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    async def remove_skill_from_resume(self, db: AsyncSession, resume_id: int, applicant_id: int, skill_id: int):
        resume = await self._get_resume_or_404(db, resume_id, applicant_id)
        try:
            skill = await self.skillcrud.get(db, skill_id)
            if skill and skill in resume.skills:
                resume.skills.remove(skill)
                await db.commit()
                await db.refresh(resume, ["skills"])
            return resume
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    async def add_skills_batch(self, db: AsyncSession, resume_id: int, applicant_id: int, skill_names: list[str]):
        resume = await self._get_resume_or_404(db, resume_id, applicant_id)
        try:
            skills_map = await self.skillcrud.get_or_create_many(db, skill_names)
            existing_ids = {s.id for s in resume.skills}
            to_add = [s for name, s in skills_map.items() if s.id not in existing_ids]
            if to_add:
                resume.skills.extend(to_add)
                await db.commit()
                await db.refresh(resume, ["skills"])
            return resume
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    # ---------- Опыт работы ----------
    async def add_work_experience(self, db: AsyncSession, resume_id: int, applicant_id: int, data: WorkExperienceCreate):
        await self._get_resume_or_404(db, resume_id, applicant_id)
        try:
            exp_dict = data.model_dump()
            exp_dict["resume_id"] = resume_id
            exp = await self.workexperiencecrud.create(db, exp_dict)
            await db.commit()
            return exp
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    async def update_work_experience(self, db: AsyncSession, exp_id: int, resume_id: int, applicant_id: int, data: WorkExperienceUpdate):
        exp = await self._get_work_exp_or_404(db, exp_id, resume_id, applicant_id)
        try:
            updated = await self.workexperiencecrud.update(db, data.model_dump(exclude_unset=True), exp_id)
            await db.commit()
            return updated
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    async def delete_work_experience(self, db: AsyncSession, exp_id: int, resume_id: int, applicant_id: int):
        exp = await self._get_work_exp_or_404(db, exp_id, resume_id, applicant_id)
        try:
            await self.workexperiencecrud.delete(db, exp_id)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    # ---------- Образование ----------
    async def add_education(self, db: AsyncSession, applicant_id: int, data: EducationCreate):
        try:
            applicant = await self.applicantcrud.get(db, applicant_id)
            if not applicant:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Applicant not found")
            institution = await self.educationalinstitutioncrud.get_or_create(db, data.institution_name)
            edu_dict = data.model_dump(exclude={"institution_name"})
            edu_dict["applicant_id"] = applicant_id
            edu_dict["institution_id"] = institution.id
            edu = await self.educationcrud.create(db, edu_dict)
            await db.commit()
            await db.refresh(edu, ["institution"])
            # Возвращаем словарь с institution_name для корректной сериализации
            return {
                "id": edu.id,
                "institution_name": edu.institution.name,
                "start_date": edu.start_date,
                "end_date": edu.end_date
            }
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid data")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    async def update_education(self, db: AsyncSession, edu_id: int, applicant_id: int, data: EducationUpdate):
        edu = await self.educationcrud.get(db, edu_id)
        if not edu or edu.applicant_id != applicant_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Education not found")
        try:
            if data.institution_name:
                institution = await self.educationalinstitutioncrud.get_or_create(db, data.institution_name)
                edu.institution_id = institution.id
            for field, value in data.model_dump(exclude={"institution_name"}, exclude_unset=True).items():
                setattr(edu, field, value)
            await db.commit()
            await db.refresh(edu, ["institution"])
            # Возвращаем словарь с institution_name
            return {
                "id": edu.id,
                "institution_name": edu.institution.name,
                "start_date": edu.start_date,
                "end_date": edu.end_date
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    async def delete_education(self, db: AsyncSession, edu_id: int, applicant_id: int):
        edu = await self.educationcrud.get(db, edu_id)
        if not edu or edu.applicant_id != applicant_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Education not found")
        try:
            await self.educationcrud.delete(db, edu_id)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

applicant_service = ApplicantService()