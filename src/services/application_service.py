from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from src.cruds.application_crud import applicationcrud
from src.cruds.company_cruds.vacancy_crud import vacancycrud
from src.cruds.applicant_cruds.resume_crud import resumecrud
from src.cruds.applicant_cruds.applicant_crud import applicantcrud
from src.cruds.company_cruds.company_crud import companycrud
from src.redis.redis_client import RedisClient
from src.schemas.application_schema import ApplicationCreate, ApplicationUpdate
from src.models.model import Application

class ApplicationService:
    def __init__(self, redis_client: RedisClient):
        self.applicationcrud = applicationcrud
        self.vacancycrud = vacancycrud
        self.resumecrud = resumecrud
        self.applicantcrud = applicantcrud
        self.companycrud = companycrud
        self.redis = redis_client

    async def get_applicant_by_user(self, db: AsyncSession, user_id: int):
        applicant = await self.applicantcrud.get_by_user_id(db, user_id)
        if not applicant:
            raise HTTPException(status_code=404, detail="Профиль соискателя не найден")
        return applicant

    async def get_company_by_user(self, db: AsyncSession, user_id: int):
        company = await self.companycrud.get_by_user_id(db, user_id)
        if not company:
            raise HTTPException(status_code=404, detail="Профиль компании не найден")
        return company

    async def apply_to_vacancy(self, db: AsyncSession, applicant_id: int, application_data: ApplicationCreate):
        vacancy = await self.vacancycrud.get(db, application_data.vacancy_id)
        if not vacancy or not vacancy.is_active:
            raise HTTPException(status_code=404, detail="Вакансия не найдена или неактивна")

        resume = await self.resumecrud.get(db, application_data.resume_id)
        if not resume or resume.applicant_id != applicant_id:
            raise HTTPException(status_code=404, detail="Резюме не найдено или не принадлежит вам")

        existing = await self.applicationcrud.get_by_vacancy_and_resume(db, application_data.vacancy_id, application_data.resume_id)
        if existing:
            raise HTTPException(status_code=400, detail="Вы уже откликались на эту вакансию")

        app_dict = application_data.model_dump()
        app_dict["status"] = "pending"
        application = await self.applicationcrud.create(db, app_dict)
        await db.commit()

        await self.redis.increment_counter(f"vacancy:applications:{application_data.vacancy_id}")

        return application

    async def get_vacancy_applications(self, db: AsyncSession, vacancy_id: int, company_id: int):
        vacancy = await self.vacancycrud.get(db, vacancy_id)
        if not vacancy or vacancy.company_id != company_id:
            raise HTTPException(status_code=404, detail="Вакансия не найдена или не принадлежит вам")
        applications = await self.applicationcrud.get_by_vacancy(db, vacancy_id)
        return applications

    async def update_application_status(self, db: AsyncSession, vacancy_id: int, resume_id: int, company_id: int, status: str):
        application = await self.applicationcrud.get_by_vacancy_and_resume(db, vacancy_id, resume_id)
        if not application:
            raise HTTPException(status_code=404, detail="Отклик не найден")
        vacancy = await self.vacancycrud.get(db, vacancy_id)
        if not vacancy or vacancy.company_id != company_id:
            raise HTTPException(status_code=403, detail="Доступ запрещён")
        application.status = status
        await db.commit()
        return application

    async def get_application_count(self, vacancy_id: int) -> int:
        return await self.redis.get_counter(f"vacancy:applications:{vacancy_id}")