from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

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
from src.models.model import Applicant, Education, Resume, WorkExperience
from src.core.exceptions import (
    ApplicantNotFoundError, ResumeNotFoundError, AccessDeniedError,
    EducationNotFoundError
)
from src.utils.logger import logger

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

    # ---------- Вспомогательные методы ----------
    async def _get_applicant_or_raise(self, db: AsyncSession, user_id: int) -> Applicant:
        applicant = await self.applicantcrud.get_by_user_id_with_details(db, user_id)
        if not applicant:
            raise ApplicantNotFoundError()
        return applicant

    async def _get_resume_or_raise(self, db: AsyncSession, resume_id: int, applicant_id: int) -> Resume:
        resume = await self.resumecrud.get_with_details(db, resume_id)
        if not resume:
            raise ResumeNotFoundError()
        if resume.applicant_id != applicant_id:
            raise AccessDeniedError("Резюме не принадлежит текущему пользователю")
        return resume

    async def _get_work_exp_or_raise(self, db: AsyncSession, exp_id: int, resume_id: int, applicant_id: int) -> WorkExperience:
        exp = await self.workexperiencecrud.get(db, exp_id)
        if not exp:
            raise HTTPException(status_code=404, detail="Work experience not found")
        if exp.resume_id != resume_id:
            raise AccessDeniedError("Опыт работы не принадлежит данному резюме")
        await self._get_resume_or_raise(db, resume_id, applicant_id)
        return exp

    # ---------- Профиль ----------
    async def get_profile(self, db: AsyncSession, user_id: int) -> Applicant:
        return await self._get_applicant_or_raise(db, user_id)

    async def update_profile(self, db: AsyncSession, user_id: int, update_data: ApplicantUpdate) -> Applicant:
        applicant = await self._get_applicant_or_raise(db, user_id)
        try:
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
            raise HTTPException(status_code=400, detail="Data error")
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error")

    # ---------- Резюме ----------
    async def create_resume(self, db: AsyncSession, applicant_id: int, data: ResumeCreate) -> Resume:
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
            raise HTTPException(status_code=400, detail="Invalid profession_id or duplicate")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=500, detail="Internal error")

    async def get_resumes(self, db: AsyncSession, applicant_id: int, skip: int = 0, limit: int = 10) -> list[Resume]:
        return await self.resumecrud.get_by_applicant_with_details_paginated(db, applicant_id, skip, limit)

    async def get_resume_detail(self, db: AsyncSession, resume_id: int, applicant_id: int) -> Resume:
        return await self._get_resume_or_raise(db, resume_id, applicant_id)

    async def update_resume(self, db: AsyncSession, resume_id: int, applicant_id: int, data: ResumeUpdate) -> Resume:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)
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
            raise HTTPException(status_code=500, detail="Internal error")

    async def delete_resume(self, db: AsyncSession, resume_id: int, applicant_id: int) -> None:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)
        try:
            await self.resumecrud.delete(db, resume_id)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=500, detail="Internal error")

    # ---------- Навыки резюме ----------
    async def add_skill_to_resume(self, db: AsyncSession, resume_id: int, applicant_id: int, skill_name: str) -> Resume:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)
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
            raise HTTPException(status_code=500, detail="Internal error")

    async def remove_skill_from_resume(self, db: AsyncSession, resume_id: int, applicant_id: int, skill_id: int) -> Resume:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)
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
            raise HTTPException(status_code=500, detail="Internal error")

    async def add_skills_batch(self, db: AsyncSession, resume_id: int, applicant_id: int, skill_names: list[str]) -> Resume:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)
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
            raise HTTPException(status_code=500, detail="Internal error")

    # ---------- Опыт работы ----------
    async def add_work_experience(self, db: AsyncSession, resume_id: int, applicant_id: int, data: WorkExperienceCreate) -> WorkExperience:
        await self._get_resume_or_raise(db, resume_id, applicant_id)
        try:
            exp_dict = data.model_dump()
            exp_dict["resume_id"] = resume_id
            exp = await self.workexperiencecrud.create(db, exp_dict)
            await db.commit()
            return exp
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=500, detail="Internal error")

    async def update_work_experience(self, db: AsyncSession, exp_id: int, resume_id: int, applicant_id: int, data: WorkExperienceUpdate) -> WorkExperience:
        exp = await self._get_work_exp_or_raise(db, exp_id, resume_id, applicant_id)
        try:
            updated = await self.workexperiencecrud.update(db, data.model_dump(exclude_unset=True), exp_id)
            await db.commit()
            return updated
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=500, detail="Internal error")

    async def delete_work_experience(self, db: AsyncSession, exp_id: int, resume_id: int, applicant_id: int) -> None:
        exp = await self._get_work_exp_or_raise(db, exp_id, resume_id, applicant_id)
        try:
            await self.workexperiencecrud.delete(db, exp_id)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=500, detail="Internal error")

    # ---------- Образование ----------
    async def add_education(self, db: AsyncSession, applicant_id: int, data: EducationCreate) -> Education:
        applicant = await self._get_applicant_or_raise(db, applicant_id)  
        try:
            institution = await educationalinstitutioncrud.get(db, data.institution_id)
            if not institution:
                raise HTTPException(status_code=400, detail="Учебное заведение не найдено")

            edu_dict = data.model_dump()
            edu_dict["applicant_id"] = applicant.id 
            edu_dict["institution_id"] = institution.id
            edu = await self.educationcrud.create(db, edu_dict)
            await db.commit()
            await db.refresh(edu, ["institution"])
            return edu
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="Некорректные данные")
        except HTTPException:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error in add_education: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Внутренняя ошибка")

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"❌ IntegrityError: {e}")
            raise HTTPException(status_code=400, detail="Нарушение целостности данных (возможно, дубликат)")
        except HTTPException:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Непредвиденная ошибка: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

    async def update_education(self, db: AsyncSession, edu_id: int, applicant_id: int, data: EducationUpdate) -> Education:
        edu = await self.educationcrud.get_with_institution(db, edu_id)
        if not edu or edu.applicant_id != applicant_id:
            raise EducationNotFoundError()

        try:
            # Если передан institution_id, обновляем учебное заведение
            if data.institution_id is not None:
                institution = await self.educationalinstitutioncrud.get(db, data.institution_id)
                if not institution:
                    raise HTTPException(status_code=400, detail="Учебное заведение не найдено")
                edu.institution_id = institution.id

            # Обновляем остальные поля (даты)
            # Исключаем institution_id, так как уже обработали отдельно
            update_data = data.model_dump(exclude={"institution_id"}, exclude_unset=True)
            for field, value in update_data.items():
                setattr(edu, field, value)

            await db.commit()
            await db.refresh(edu, ["institution"])
            return edu

        except HTTPException:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error in update_education: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Внутренняя ошибка")

    async def delete_education(self, db: AsyncSession, edu_id: int, applicant_id: int) -> None:
        edu = await self.educationcrud.get(db, edu_id)
        if not edu or edu.applicant_id != applicant_id:
            raise EducationNotFoundError()
        try:
            await self.educationcrud.delete(db, edu_id)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=500, detail="Internal error")

applicant_service = ApplicantService()