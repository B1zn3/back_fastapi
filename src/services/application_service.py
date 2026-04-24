from sqlalchemy.ext.asyncio import AsyncSession
from src.cruds.application_crud import applicationcrud
from src.cruds.company_cruds.vacancy_crud import vacancycrud
from src.cruds.applicant_cruds.resume_crud import resumecrud
from src.schemas.application_schema import ApplicationCreate
from src.core.exceptions import (
    VacancyNotFoundError,
    ResumeNotFoundError,
    DuplicateApplicationError,
    AccessDeniedError,
    ApplicationNotFoundError,
)
from src.redis.cache_service import cache_service
from src.redis.lock_service import lock_service
from src.core.constants import ApplicationStatus
from src.utils.logger import logger


class ApplicationService:
    def __init__(self):
        self.applicationcrud = applicationcrud
        self.vacancycrud = vacancycrud
        self.resumecrud = resumecrud

    async def _invalidate_vacancy_cache(self, vacancy_id: int):
        await cache_service.delete(f"vacancy:applications:{vacancy_id}")

    async def _get_vacancy_or_raise(self, db: AsyncSession, vacancy_id: int):
        vacancy = await self.vacancycrud.get(db, vacancy_id)
        if not vacancy:
            raise VacancyNotFoundError()
        return vacancy

    async def _get_resume_or_raise(self, db: AsyncSession, resume_id: int, applicant_id: int):
        resume = await self.resumecrud.get(db, resume_id)
        if not resume:
            raise ResumeNotFoundError()
        if resume.applicant_id != applicant_id:
            raise AccessDeniedError("Резюме не принадлежит текущему пользователю")
        return resume

    async def _get_default_resume_or_raise(self, db: AsyncSession, applicant_id: int):
        resumes = await self.resumecrud.get_by_applicant(db, applicant_id)
        if not resumes:
            raise ResumeNotFoundError("У вас нет резюме для отклика")
        return resumes[0]

    async def apply_to_vacancy(
        self,
        db: AsyncSession,
        applicant_id: int,
        application_data: ApplicationCreate
    ):
        await self._get_vacancy_or_raise(db, application_data.vacancy_id)

        if application_data.resume_id is not None:
            resume = await self._get_resume_or_raise(db, application_data.resume_id, applicant_id)
        else:
            resume = await self._get_default_resume_or_raise(db, applicant_id)

        lock_key = f"application_lock:{application_data.vacancy_id}:{resume.id}"
        if not await lock_service.acquire_lock(lock_key):
            raise DuplicateApplicationError("Обработка отклика уже выполняется")

        try:
            existing = await self.applicationcrud.get_by_vacancy_and_resume(
                db,
                application_data.vacancy_id,
                resume.id,
            )
            if existing:
                raise DuplicateApplicationError("Вы уже откликались на эту вакансию этим резюме")

            app_dict = {
                "vacancy_id": application_data.vacancy_id,
                "resume_id": resume.id,
                "status": ApplicationStatus.PENDING,
            }

            application = await self.applicationcrud.create(db, app_dict)

            await self._invalidate_vacancy_cache(application_data.vacancy_id)
            await db.commit()
            await db.refresh(application)

            logger.info(
                f"Applicant {applicant_id} applied to vacancy {application_data.vacancy_id} with resume {resume.id}"
            )
            return application
        except Exception:
            await db.rollback()
            raise
        finally:
            await lock_service.release_lock(lock_key)

    async def get_applicant_applications(
        self,
        db: AsyncSession,
        applicant_id: int,
        skip: int = 0,
        limit: int = 10
    ):
        resumes = await self.resumecrud.get_by_applicant(db, applicant_id)
        resume_ids = [r.id for r in resumes]
        if not resume_ids:
            return []

        applications = []
        for rid in resume_ids:
            apps = await self.applicationcrud.get_by_resume(db, rid)
            applications.extend(apps)

        applications.sort(
            key=lambda a: getattr(a, "updated_at", None) or getattr(a, "created_at", None) or 0,
            reverse=True,
        )
        return applications[skip:skip + limit]

    async def get_vacancy_applications(
        self,
        db: AsyncSession,
        vacancy_id: int,
        company_id: int,
        skip: int = 0,
        limit: int = 10
    ):
        vacancy = await self._get_vacancy_or_raise(db, vacancy_id)
        if vacancy.company_id != company_id:
            raise AccessDeniedError("Вакансия не принадлежит вашей компании")

        applications = await self.applicationcrud.get_by_vacancy(db, vacancy_id)
        return applications[skip:skip + limit]

    async def update_application_status(
        self,
        db: AsyncSession,
        vacancy_id: int,
        resume_id: int,
        company_id: int,
        status: ApplicationStatus
    ):
        vacancy = await self._get_vacancy_or_raise(db, vacancy_id)
        if vacancy.company_id != company_id:
            raise AccessDeniedError("Вакансия не принадлежит вашей компании")

        application = await self.applicationcrud.get_by_vacancy_and_resume(db, vacancy_id, resume_id)
        if not application:
            raise ApplicationNotFoundError()

        application.status = status
        await db.flush()
        await self._invalidate_vacancy_cache(vacancy_id)
        await db.commit()
        await db.refresh(application)
        return application


application_service = ApplicationService()