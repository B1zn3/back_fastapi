from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from src.cruds.applicant_cruds.applicant_crud import applicantcrud
from src.cruds.profile_crud import profilecrud
from src.cruds.applicant_cruds.resume_crud import resumecrud
from src.cruds.city_crud import citycrud
from src.cruds.skill_crud import skillcrud
from src.cruds.applicant_cruds.work_experience_crud import workexperiencecrud
from src.cruds.applicant_cruds.education_crud import educationcrud
from src.schemas.applicant_schemas.applicant_schema import ApplicantUpdate
from src.schemas.applicant_schemas.resume_schema import ResumeCreate, ResumeUpdate
from src.schemas.skill_schema import SkillCreate
from src.schemas.applicant_schemas.work_experience_schema import WorkExperienceCreate, WorkExperienceUpdate
from src.schemas.applicant_schemas.education_schema import EducationCreate, EducationUpdate
from src.models.model import Applicant

class ApplicantService:
    def __init__(self):
        self.applicantcrud = applicantcrud
        self.profilecrud = profilecrud
        self.resumecrud = resumecrud
        self.citycrud = citycrud
        self.skillcrud = skillcrud
        self.workexperiencecrud = workexperiencecrud
        self.educationcrud = educationcrud

    async def get_applicant_profile(self, db: AsyncSession, applicant: Applicant):
        return applicant

    async def update_applicant_profile(self, db: AsyncSession, applicant: Applicant, update_data: ApplicantUpdate, user_id: int):

        for field in ["photo", "phone", "address", "birth_date", "gender"]:
            value = getattr(update_data, field, None)
            if value is not None:
                setattr(applicant, field, value)

        if update_data.city_name is not None:
            city = await self.citycrud.get_or_create(db, update_data.city_name)
            applicant.city_id = city.id

        profile = applicant.profile   
        if not profile:
            profile = await self.profilecrud.create(db, {"user_id": user_id, "applicant_id": applicant.id})
            applicant.profile = profile

        for field in ["first_name", "last_name", "middle_name"]:
            value = getattr(update_data, field, None)
            if value is not None:
                setattr(profile, field, value)

        await db.commit()
        await db.refresh(applicant, ["city", "profile", "resumes"])
        return applicant

    async def create_resume(self, db: AsyncSession, applicant_id: int, resume_data: ResumeCreate):
        resume_dict = resume_data.model_dump()
        resume_dict["applicant_id"] = applicant_id
        resume_dict["created_at"] = datetime.utcnow()    
        resume_dict["updated_at"] = datetime.utcnow()  
        resume = await self.resumecrud.create(db, resume_dict)
        await db.commit()
        await db.refresh(resume, ["profession", "skills", "work_experiences", "educations"])
        return resume

    async def get_resumes(self, db: AsyncSession, applicant_id: int):
        return await self.resumecrud.get_by_applicant(db, applicant_id)

    async def get_resume_detail(self, db: AsyncSession, resume_id: int, applicant_id: int):
        resume = await self.resumecrud.get_with_details(db, resume_id)
        if not resume or resume.applicant_id != applicant_id:
            raise HTTPException(status_code=404, detail="Резюме не найдено")
        return resume

    async def update_resume(self, db: AsyncSession, resume_id: int, applicant_id: int, resume_data: ResumeUpdate):
        resume = await self.resumecrud.get(db, resume_id)
        if not resume or resume.applicant_id != applicant_id:
            raise HTTPException(status_code=404, detail="Резюме не найдено")
        updated = await self.resumecrud.update(db, resume_data.model_dump(exclude_unset=True), resume_id)
        await db.commit()
        await db.refresh(resume, ["profession", "skills", "work_experiences", "educations"])
        return updated

    async def delete_resume(self, db: AsyncSession, resume_id: int, applicant_id: int):
        resume = await self.resumecrud.get(db, resume_id)
        if not resume or resume.applicant_id != applicant_id:
            raise HTTPException(status_code=404, detail="Резюме не найдено")
        await self.resumecrud.delete(db, resume_id)
        await db.commit()

    async def add_skill_to_resume(self, db: AsyncSession, resume_id: int, applicant_id: int, skill_name: str):
        resume = await self.resumecrud.get_with_details(db, resume_id)
        if not resume or resume.applicant_id != applicant_id:
            raise HTTPException(status_code=404, detail="Резюме не найдено")
        skill = await self.skillcrud.get_or_create(db, skill_name)
        if skill not in resume.skills:
            resume.skills.append(skill)
            await db.commit()
            await db.refresh(resume, ["skills"])
        return resume

    async def remove_skill_from_resume(self, db: AsyncSession, resume_id: int, applicant_id: int, skill_id: int):
        resume = await self.resumecrud.get_with_details(db, resume_id)
        if not resume or resume.applicant_id != applicant_id:
            raise HTTPException(status_code=404, detail="Резюме не найдено")
        skill = await self.skillcrud.get(db, skill_id)
        if skill and skill in resume.skills:
            resume.skills.remove(skill)
            await db.commit()
            await db.refresh(resume, ["skills"])
        return resume

    async def add_work_experience(self, db: AsyncSession, resume_id: int, applicant_id: int, exp_data: WorkExperienceCreate):
        resume = await self.resumecrud.get(db, resume_id)
        if not resume or resume.applicant_id != applicant_id:
            raise HTTPException(status_code=404, detail="Резюме не найдено")
        exp_dict = exp_data.model_dump()
        exp_dict["resume_id"] = resume_id
        exp = await self.workexperiencecrud.create(db, exp_dict)
        await db.commit()
        return exp

    async def update_work_experience(self, db: AsyncSession, exp_id: int, resume_id: int, applicant_id: int, exp_data: WorkExperienceUpdate):
        exp = await self.workexperiencecrud.get(db, exp_id)
        if not exp or exp.resume_id != resume_id:
            raise HTTPException(status_code=404, detail="Опыт работы не найден")
        resume = await self.resumecrud.get(db, resume_id)
        if not resume or resume.applicant_id != applicant_id:
            raise HTTPException(status_code=403, detail="Доступ запрещён")
        updated = await self.workexperiencecrud.update(db, exp_data.model_dump(exclude_unset=True), exp_id)
        await db.commit()
        return updated

    async def delete_work_experience(self, db: AsyncSession, exp_id: int, resume_id: int, applicant_id: int):
        exp = await self.workexperiencecrud.get(db, exp_id)
        if not exp or exp.resume_id != resume_id:
            raise HTTPException(status_code=404, detail="Опыт работы не найден")
        resume = await self.resumecrud.get(db, resume_id)
        if not resume or resume.applicant_id != applicant_id:
            raise HTTPException(status_code=403, detail="Доступ запрещён")
        await self.workexperiencecrud.delete(db, exp_id)
        await db.commit()


applicant_service = ApplicantService()