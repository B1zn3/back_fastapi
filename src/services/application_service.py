from datetime import datetime, timezone

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


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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

    def _normalize_cover_letter(self, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        if not normalized:
            return None

        return normalized

    def _status_value(self, status: ApplicationStatus | str) -> str:
        return status.value if hasattr(status, "value") else str(status)

    def _get_application_label(self, status: str | None) -> str:
        if status == ApplicationStatus.REJECTED.value:
            return "Вам отказали"

        if status == ApplicationStatus.ACCEPTED.value:
            return "Собеседование"

        if status == ApplicationStatus.PENDING.value:
            return "Вы откликнулись"

        return "Можно откликнуться"

    def _serialize_application(self, application):
        vacancy = application.vacancy
        resume = application.resume

        profession_name = None
        if resume and resume.profession:
            profession_name = resume.profession.name

        vacancy_profession_name = None
        if vacancy and vacancy.profession:
            vacancy_profession_name = vacancy.profession.name

        return {
            "id": application.id,
            "vacancy_id": application.vacancy_id,
            "resume_id": application.resume_id,
            "status": application.status,
            "cover_letter": application.cover_letter,
            "created_at": application.created_at,
            "updated_at": application.updated_at,
            "vacancy": {
                "id": vacancy.id,
                "title": vacancy.title,
                "salary_min": vacancy.salary_min,
                "salary_max": vacancy.salary_max,
                "currency": vacancy.currency.name if vacancy.currency else None,
                "company_id": vacancy.company_id,
                "company_name": vacancy.company.name if vacancy.company else None,
                "city_name": vacancy.city.name if vacancy.city else None,
                "profession_name": vacancy_profession_name,
            } if vacancy else None,
            "resume": {
                "id": resume.id,
                "profession_id": resume.profession_id,
                "profession_name": profession_name,
                "title": profession_name or f"Резюме #{resume.id}",
            } if resume else None,
        }

    async def apply_to_vacancy(
        self,
        db: AsyncSession,
        applicant_id: int,
        application_data: ApplicationCreate,
    ):
        await self._get_vacancy_or_raise(db, application_data.vacancy_id)

        resume = await self._get_resume_or_raise(
            db,
            application_data.resume_id,
            applicant_id,
        )

        lock_key = f"application_lock:{application_data.vacancy_id}:{applicant_id}"

        if not await lock_service.acquire_lock(lock_key):
            raise DuplicateApplicationError("Обработка отклика уже выполняется")

        try:
            existing = await self.applicationcrud.get_by_vacancy_and_applicant(
                db,
                application_data.vacancy_id,
                applicant_id,
            )

            if existing:
                raise DuplicateApplicationError("Вы уже откликались на эту вакансию")

            now = utc_now_naive()

            application_dict = {
                "vacancy_id": application_data.vacancy_id,
                "resume_id": resume.id,
                "status": ApplicationStatus.PENDING.value,
                "cover_letter": self._normalize_cover_letter(application_data.cover_letter),
                "created_at": now,
                "updated_at": now,
            }

            application = await self.applicationcrud.create(db, application_dict)

            await self._invalidate_vacancy_cache(application_data.vacancy_id)
            await db.commit()

            created_application = await self.applicationcrud.get_by_vacancy_and_resume(
                db,
                application.vacancy_id,
                application.resume_id,
            )

            logger.info(
                f"Applicant {applicant_id} applied to vacancy "
                f"{application_data.vacancy_id} with resume {resume.id}"
            )

            return self._serialize_application(created_application or application)

        except Exception:
            await db.rollback()
            raise

        finally:
            await lock_service.release_lock(lock_key)

    async def get_applicant_application_state(
        self,
        db: AsyncSession,
        applicant_id: int,
        vacancy_id: int,
    ):
        await self._get_vacancy_or_raise(db, vacancy_id)

        application = await self.applicationcrud.get_by_vacancy_and_applicant(
            db,
            vacancy_id,
            applicant_id,
        )

        if not application:
            return {
                "vacancy_id": vacancy_id,
                "applied": False,
                "status": None,
                "label": "Можно откликнуться",
                "resume_id": None,
                "cover_letter": None,
                "created_at": None,
                "updated_at": None,
            }

        return {
            "id": application.id,
            "vacancy_id": vacancy_id,
            "applied": True,
            "status": application.status,
            "label": self._get_application_label(application.status),
            "resume_id": application.resume_id,
            "cover_letter": application.cover_letter,
            "created_at": application.created_at,
            "updated_at": application.updated_at,
        }

    async def get_applicant_applications(
        self,
        db: AsyncSession,
        applicant_id: int,
        skip: int = 0,
        limit: int = 10,
    ):
        applications = await self.applicationcrud.get_by_applicant(
            db,
            applicant_id,
            skip=skip,
            limit=limit,
        )

        return [self._serialize_application(application) for application in applications]

    async def get_vacancy_applications(
        self,
        db: AsyncSession,
        vacancy_id: int,
        company_id: int,
        skip: int = 0,
        limit: int = 10,
    ):
        vacancy = await self._get_vacancy_or_raise(db, vacancy_id)

        if vacancy.company_id != company_id:
            raise AccessDeniedError("Вакансия не принадлежит вашей компании")

        applications = await self.applicationcrud.get_by_vacancy(
            db,
            vacancy_id,
            skip=skip,
            limit=limit,
        )

        return [self._serialize_application(application) for application in applications]

    async def update_application_status(
        self,
        db: AsyncSession,
        vacancy_id: int,
        resume_id: int,
        company_id: int,
        status: ApplicationStatus,
    ):
        vacancy = await self._get_vacancy_or_raise(db, vacancy_id)

        if vacancy.company_id != company_id:
            raise AccessDeniedError("Вакансия не принадлежит вашей компании")

        application = await self.applicationcrud.get_by_vacancy_and_resume(
            db,
            vacancy_id,
            resume_id,
        )

        if not application:
            raise ApplicationNotFoundError()

        application.status = self._status_value(status)
        application.updated_at = utc_now_naive()

        await self._invalidate_vacancy_cache(vacancy_id)
        await db.commit()

        updated_application = await self.applicationcrud.get_by_vacancy_and_resume(
            db,
            vacancy_id,
            resume_id,
        )

        return self._serialize_application(updated_application or application)


application_service = ApplicationService()