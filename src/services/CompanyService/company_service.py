from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any, Optional
import logging
import re

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.core.constants import ApplicationStatus
from src.models.model import (
    Applicant,
    Application,
    City,
    Company,
    CompanyType,
    Currency,
    District,
    Education,
    EmploymentType,
    Experience,
    Profession,
    Resume,
    ResumeChange,
    Skill,
    Status,
    User,
    Vacancy,
    WorkSchedule,
)
from src.schemas.application_schema import ApplicationUpdate
from src.schemas.company_schemas.company_schema import CompanyUpdate
from src.schemas.company_schemas.employer_application_schema import (
    EmployerApplicationStatusUpdate,
)
from src.schemas.company_schemas.vacancy_schema import VacancyCreate, VacancyUpdate


logger = logging.getLogger(__name__)


class CompanyService:
    DEFAULT_VACANCY_STATUS_ID = 1

    # ---------- loaders ----------

    async def get_company_by_user_id_with_details(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Company | None:
        stmt = (
            select(Company)
            .join(User, User.company_id == Company.id)
            .where(User.id == user_id)
            .options(
                selectinload(Company.company_type),

                selectinload(Company.cities)
                .joinedload(City.district)
                .joinedload(District.region),

                selectinload(Company.cities)
                .joinedload(City.settlement_type),

                selectinload(Company.vacancies).selectinload(Vacancy.profession),
                selectinload(Company.vacancies).selectinload(Vacancy.city),
                selectinload(Company.vacancies).selectinload(Vacancy.employment_type),
                selectinload(Company.vacancies).selectinload(Vacancy.work_schedule),
                selectinload(Company.vacancies).selectinload(Vacancy.currency),
                selectinload(Company.vacancies).selectinload(Vacancy.experience),
                selectinload(Company.vacancies).selectinload(Vacancy.status),
                selectinload(Company.vacancies).selectinload(Vacancy.skills),
            )
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_company_by_id_with_details(
        self,
        db: AsyncSession,
        company_id: int,
    ) -> Company | None:
        stmt = (
            select(Company)
            .where(Company.id == company_id)
            .options(
                selectinload(Company.company_type),

                selectinload(Company.cities)
                .joinedload(City.district)
                .joinedload(District.region),

                selectinload(Company.cities)
                .joinedload(City.settlement_type),

                selectinload(Company.vacancies).selectinload(Vacancy.profession),
                selectinload(Company.vacancies).selectinload(Vacancy.city),
                selectinload(Company.vacancies).selectinload(Vacancy.employment_type),
                selectinload(Company.vacancies).selectinload(Vacancy.work_schedule),
                selectinload(Company.vacancies).selectinload(Vacancy.currency),
                selectinload(Company.vacancies).selectinload(Vacancy.experience),
                selectinload(Company.vacancies).selectinload(Vacancy.status),
                selectinload(Company.vacancies).selectinload(Vacancy.skills),
            )
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_vacancy_with_details(
        self,
        db: AsyncSession,
        vacancy_id: int,
    ) -> Vacancy | None:
        stmt = (
            select(Vacancy)
            .where(Vacancy.id == vacancy_id)
            .options(
                selectinload(Vacancy.company),
                selectinload(Vacancy.city),
                selectinload(Vacancy.profession),
                selectinload(Vacancy.employment_type),
                selectinload(Vacancy.work_schedule),
                selectinload(Vacancy.currency),
                selectinload(Vacancy.experience),
                selectinload(Vacancy.status),
                selectinload(Vacancy.skills),
            )
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_company_vacancy_or_404(
        self,
        db: AsyncSession,
        vacancy_id: int,
        company_id: int,
    ) -> Vacancy:
        vacancy = await self.get_vacancy_with_details(db, vacancy_id)

        if not vacancy or vacancy.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вакансия не найдена",
            )

        return vacancy

    async def get_application_with_details(
        self,
        db: AsyncSession,
        vacancy_id: int,
        resume_id: int,
    ) -> Application | None:
        stmt = (
            select(Application)
            .where(
                Application.vacancy_id == vacancy_id,
                Application.resume_id == resume_id,
            )
            .options(
                selectinload(Application.vacancy).selectinload(Vacancy.company),
                selectinload(Application.vacancy).selectinload(Vacancy.city),
                selectinload(Application.vacancy).selectinload(Vacancy.currency),
                selectinload(Application.vacancy).selectinload(Vacancy.profession),
                selectinload(Application.resume).selectinload(Resume.profession),
                selectinload(Application.resume).selectinload(Resume.applicant),
            )
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ---------- common helpers ----------

    def _status_value(self, value) -> str:
        return value.value if hasattr(value, "value") else str(value)

    def _parse_optional_int_list(self, value: Optional[str]) -> list[int]:
        if not value:
            return []

        result: list[int] = []

        for item in value.split(","):
            normalized = item.strip()

            if normalized.isdigit():
                result.append(int(normalized))

        return result

    def _to_date(self, value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date()

        return value

    def _normalize_text(self, value: str | None) -> str:
        return (value or "").strip().lower()

    def _get_skill_names(self, skills) -> list[str]:
        return [
            skill.name
            for skill in skills or []
            if getattr(skill, "name", None)
        ]

    def _get_applicant_full_name(self, applicant: Applicant | None) -> str:
        if not applicant:
            return "Соискатель"

        parts = [
            applicant.last_name,
            applicant.first_name,
            applicant.middle_name,
        ]

        full_name = " ".join(part for part in parts if part)

        return full_name or f"Соискатель #{applicant.id}"

    def _get_applicant_age(self, birth_date) -> Optional[int]:
        normalized_birth_date = self._to_date(birth_date)

        if not normalized_birth_date:
            return None

        today = date.today()
        age = today.year - normalized_birth_date.year

        if (today.month, today.day) < (
            normalized_birth_date.month,
            normalized_birth_date.day,
        ):
            age -= 1

        return age if age >= 0 else None

    def _calculate_experience_years(self, work_experiences) -> float:
        today = date.today()
        total_months = 0

        for experience in work_experiences or []:
            start_date = self._to_date(getattr(experience, "start_date", None))
            end_date = self._to_date(getattr(experience, "end_date", None)) or today

            if not start_date or end_date < start_date:
                continue

            months = (end_date.year - start_date.year) * 12
            months += end_date.month - start_date.month

            if end_date.day >= start_date.day:
                months += 1

            total_months += max(months, 0)

        if total_months <= 0:
            return 0

        return round(total_months / 12, 1)

    def _get_latest_experience(self, work_experiences):
        items = list(work_experiences or [])

        if not items:
            return None

        def sort_key(item):
            end_date = self._to_date(getattr(item, "end_date", None)) or date.today()
            start_date = self._to_date(getattr(item, "start_date", None)) or date.min

            return end_date, start_date

        return max(items, key=sort_key)

    def _has_cover_letter(self, application: Application) -> bool:
        return bool((application.cover_letter or "").strip())

    def _get_application_status_label(self, value: str | None) -> str:
        if value == ApplicationStatus.ACCEPTED.value:
            return "Собеседование"

        if value == ApplicationStatus.REJECTED.value:
            return "Отказ"

        if value == ApplicationStatus.PENDING.value:
            return "Новый отклик"

        return "Неизвестный статус"

    # ---------- suspicion helpers ----------

    def _risk_scale(
        self,
        value: float,
        start: float,
        full: float,
        max_score: float,
    ) -> float:
        if value <= start:
            return 0

        if value >= full:
            return max_score

        return ((value - start) / (full - start)) * max_score

    def _normalize_cover_letter_for_risk(self, value: str | None) -> str:
        if not value:
            return ""

        normalized = value.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[^\wа-яё0-9 ]+", "", normalized, flags=re.IGNORECASE)

        return normalized.strip()

    def _get_suspicion_level(self, score: int) -> str:
        if score >= 75:
            return "very_suspicious"

        if score >= 50:
            return "suspicious"

        if score >= 25:
            return "attention"

        return "normal"

    def _get_suspicion_label(self, score: int) -> str:
        if score >= 75:
            return "Очень подозрительно"

        if score >= 50:
            return "Подозрительно"

        if score >= 25:
            return "Стоит проверить"

        return "Нормально"

    def _calculate_cover_letter_risk(
        self,
        applications: list[Application],
    ) -> tuple[float, dict[str, Any], list[str]]:
        reasons: list[str] = []

        if not applications:
            return 0, {
                "empty_cover_letters": 0,
                "short_cover_letters": 0,
                "duplicate_cover_letter_ratio": 0,
                "empty_cover_letter_ratio": 0,
                "short_cover_letter_ratio": 0,
            }, reasons

        normalized_letters: list[str] = []
        empty_count = 0
        short_count = 0

        for application in applications:
            normalized = self._normalize_cover_letter_for_risk(application.cover_letter)

            if not normalized:
                empty_count += 1
                continue

            if len(normalized) < 70:
                short_count += 1

            normalized_letters.append(normalized)

        total = len(applications)
        non_empty_count = len(normalized_letters)

        empty_ratio = empty_count / total if total else 0
        short_ratio = short_count / total if total else 0

        duplicate_ratio = 0

        if non_empty_count >= 2:
            counter = Counter(normalized_letters)
            most_common_count = counter.most_common(1)[0][1]
            duplicate_ratio = most_common_count / non_empty_count

        score = 0

        if total >= 10:
            empty_score = self._risk_scale(
                value=empty_ratio,
                start=0.45,
                full=0.9,
                max_score=7,
            )

            short_score = self._risk_scale(
                value=short_ratio,
                start=0.55,
                full=0.95,
                max_score=5,
            )

            duplicate_score = self._risk_scale(
                value=duplicate_ratio,
                start=0.45,
                full=0.85,
                max_score=12,
            )

            score += empty_score + short_score + duplicate_score

            if empty_score >= 4:
                reasons.append("Много откликов без сопроводительного письма.")

            if short_score >= 3:
                reasons.append("Много очень коротких сопроводительных писем.")

            if duplicate_score >= 5:
                reasons.append("Сопроводительные письма часто повторяются.")

        return min(score, 20), {
            "empty_cover_letters": empty_count,
            "short_cover_letters": short_count,
            "duplicate_cover_letter_ratio": round(duplicate_ratio, 2),
            "empty_cover_letter_ratio": round(empty_ratio, 2),
            "short_cover_letter_ratio": round(short_ratio, 2),
        }, reasons

    # ---------- mappers ----------
    @staticmethod
    def _format_city_full_name(city: City) -> str:
        settlement_type = city.settlement_type.name if city.settlement_type else ""
        district = city.district.name if city.district else ""
        region = city.district.region.name if city.district and city.district.region else ""

        title = f"{settlement_type} {city.name}".strip()

        parts = [
            title,
            district,
            region,
        ]

        return ", ".join(part for part in parts if part)

    def _city_to_dict(self, city: City) -> dict:
        return {
            "id": city.id,
            "name": city.name,
            "full_name": self._format_city_full_name(city),
            "district_id": city.district_id,
            "district_name": city.district.name if city.district else None,
            "region_id": city.district.region_id if city.district else None,
            "region_name": (
                city.district.region.name
                if city.district and city.district.region
                else None
            ),
            "settlement_type_id": city.settlement_type_id,
            "settlement_type_name": (
                city.settlement_type.name
                if city.settlement_type
                else None
            ),
        }
    
    def map_vacancy(self, vacancy: Vacancy) -> dict:
        return {
            "id": vacancy.id,
            "title": vacancy.title,
            "description": vacancy.description,
            "employment_type_id": vacancy.employment_type_id,
            "work_schedule_id": vacancy.work_schedule_id,
            "currency_id": vacancy.currency_id,
            "experience_id": vacancy.experience_id,
            "status_id": vacancy.status_id,
            "company_id": vacancy.company_id,
            "city_id": vacancy.city_id,
            "profession_id": vacancy.profession_id,
            "salary_min": vacancy.salary_min,
            "salary_max": vacancy.salary_max,
            "employment_type_name": vacancy.employment_type.name if vacancy.employment_type else None,
            "work_schedule_name": vacancy.work_schedule.name if vacancy.work_schedule else None,
            "currency_name": vacancy.currency.name if vacancy.currency else None,
            "currency": vacancy.currency.name if vacancy.currency else None,
            "experience_name": vacancy.experience.name if vacancy.experience else None,
            "status_name": vacancy.status.name if vacancy.status else None,
            "company_name": vacancy.company.name if vacancy.company else None,
            "city_name": vacancy.city.name if vacancy.city else None,
            "profession_name": vacancy.profession.name if vacancy.profession else None,
            "skills": [
                {
                    "id": skill.id,
                    "name": skill.name,
                }
                for skill in vacancy.skills or []
            ],
            "created_at": vacancy.created_at,
            "updated_at": vacancy.updated_at,
        }

    def map_company(self, company: Company) -> dict:
        cities = list(company.cities or [])

        return {
            "id": company.id,
            "name": company.name,
            "description": company.description,
            "website": company.website,
            "logo": company.logo,
            "founded_year": company.founded_year,
            "employee_count": company.employee_count,

            "company_type_id": company.company_type_id,
            "company_type_name": company.company_type.name if company.company_type else None,

            # Для совместимости со старым фронтом
            "city_names": [
                self._format_city_full_name(city)
                for city in cities
            ],

            # Для нового фронта офисов
            "city_ids": [
                city.id
                for city in cities
            ],
            "cities": [
                self._city_to_dict(city)
                for city in cities
            ],

            "vacancies": [
                self.map_vacancy(vacancy)
                for vacancy in company.vacancies or []
            ],
        }

    def map_application(self, application: Application) -> dict:
        vacancy = application.vacancy
        resume = application.resume
        applicant = resume.applicant if resume else None

        applicant_name = None

        if applicant:
            parts = [
                applicant.last_name,
                applicant.first_name,
                applicant.middle_name,
            ]
            applicant_name = " ".join(part for part in parts if part) or f"Соискатель #{applicant.id}"

        return {
            "id": application.id,
            "vacancy_id": application.vacancy_id,
            "resume_id": application.resume_id,
            "status": application.status,
            "cover_letter": application.cover_letter,
            "created_at": application.created_at,
            "updated_at": application.updated_at,
            "vacancy_title": vacancy.title if vacancy else None,
            "company_name": vacancy.company.name if vacancy and vacancy.company else None,
            "applicant_id": applicant.id if applicant else None,
            "applicant_name": applicant_name,
            "resume_profession": resume.profession.name if resume and resume.profession else None,
            "city_name": vacancy.city.name if vacancy and vacancy.city else None,
            "salary_min": vacancy.salary_min if vacancy else None,
            "salary_max": vacancy.salary_max if vacancy else None,
            "currency": vacancy.currency.name if vacancy and vacancy.currency else None,
        }

    # ---------- validators ----------

    async def validate_vacancy_foreign_keys(
        self,
        db: AsyncSession,
        data: dict,
    ) -> None:
        checks = {
            "profession_id": (Profession, "Профессия"),
            "city_id": (City, "Город"),
            "currency_id": (Currency, "Валюта"),
            "experience_id": (Experience, "Опыт работы"),
            "employment_type_id": (EmploymentType, "Тип занятости"),
            "work_schedule_id": (WorkSchedule, "График работы"),
            "status_id": (Status, "Статус"),
        }

        for field, item in checks.items():
            model, label = item
            value = data.get(field)

            if value is None:
                continue

            exists = await db.get(model, value)

            if not exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{label} с ID {value} не найден",
                )

    async def get_or_create_skill(
        self,
        db: AsyncSession,
        name: str,
    ) -> Skill:
        normalized_name = name.strip()

        if not normalized_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Название навыка не может быть пустым",
            )

        result = await db.execute(
            select(Skill).where(func.lower(Skill.name) == normalized_name.lower())
        )
        skill = result.scalar_one_or_none()

        if skill:
            return skill

        skill = Skill(name=normalized_name)
        db.add(skill)
        await db.flush()

        return skill

    # ---------- company profile ----------

    async def get_profile(self, company: Company) -> dict:
        return self.map_company(company)

    async def update_profile(
        self,
        db: AsyncSession,
        company: Company,
        update_data: CompanyUpdate,
    ) -> dict:
        try:
            update_dict = update_data.model_dump(exclude_unset=True)

            city_ids = update_dict.pop("city_ids", None)

            if "company_type_id" in update_dict and update_dict["company_type_id"] is not None:
                company_type = await db.get(CompanyType, update_dict["company_type_id"])

                if not company_type:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Тип компании с ID {update_dict['company_type_id']} не найден",
                    )

            for key, value in update_dict.items():
                setattr(company, key, value)

            if city_ids is not None:
                unique_city_ids = list(dict.fromkeys(city_ids))

                if unique_city_ids:
                    result = await db.execute(
                        select(City)
                        .where(City.id.in_(unique_city_ids))
                        .options(
                            joinedload(City.district).joinedload(District.region),
                            joinedload(City.settlement_type),
                        )
                    )
                    cities = result.scalars().unique().all()

                    if len(cities) != len(unique_city_ids):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Один или несколько городов не найдены",
                        )

                    company.cities = cities
                else:
                    company.cities = []

            await db.commit()

            loaded_company = await self.get_company_by_id_with_details(db, company.id)

            if not loaded_company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Компания не найдена",
                )

            return self.map_company(loaded_company)

        except HTTPException:
            await db.rollback()
            raise

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error in update_profile: {e}")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Компания с таким названием уже существует",
            )

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in update_profile: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных",
            )

    # ---------- vacancies ----------

    async def create_vacancy(
        self,
        db: AsyncSession,
        company_id: int,
        vacancy_data: VacancyCreate,
    ) -> dict:
        try:
            vacancy_dict = vacancy_data.model_dump(exclude_unset=True)

            if not vacancy_dict.get("status_id"):
                vacancy_dict["status_id"] = self.DEFAULT_VACANCY_STATUS_ID

            await self.validate_vacancy_foreign_keys(db, vacancy_dict)

            now = datetime.utcnow()

            vacancy = Vacancy(
                **vacancy_dict,
                company_id=company_id,
                created_at=now,
                updated_at=now,
            )

            db.add(vacancy)
            await db.commit()

            loaded_vacancy = await self.get_vacancy_with_details(db, vacancy.id)

            if not loaded_vacancy:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Вакансия не найдена после создания",
                )

            return self.map_vacancy(loaded_vacancy)

        except HTTPException:
            await db.rollback()
            raise

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error in create_vacancy: {e}")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка целостности данных. Проверьте ID справочников",
            )

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in create_vacancy: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных",
            )

    async def get_vacancies(
        self,
        db: AsyncSession,
        company_id: int,
        skip: int = 0,
        limit: int = 10,
    ) -> list[dict]:
        stmt = (
            select(Vacancy)
            .where(Vacancy.company_id == company_id)
            .options(
                selectinload(Vacancy.company),
                selectinload(Vacancy.city),
                selectinload(Vacancy.profession),
                selectinload(Vacancy.employment_type),
                selectinload(Vacancy.work_schedule),
                selectinload(Vacancy.currency),
                selectinload(Vacancy.experience),
                selectinload(Vacancy.status),
                selectinload(Vacancy.skills),
            )
            .order_by(Vacancy.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        vacancies = result.scalars().all()

        return [self.map_vacancy(vacancy) for vacancy in vacancies]

    async def get_vacancy_detail(
        self,
        db: AsyncSession,
        vacancy_id: int,
        company_id: int,
    ) -> dict:
        vacancy = await self.get_company_vacancy_or_404(db, vacancy_id, company_id)
        return self.map_vacancy(vacancy)

    async def update_vacancy(
        self,
        db: AsyncSession,
        vacancy_id: int,
        company_id: int,
        vacancy_data: VacancyUpdate,
    ) -> dict:
        try:
            vacancy = await self.get_company_vacancy_or_404(db, vacancy_id, company_id)

            update_dict = vacancy_data.model_dump(exclude_unset=True)

            if "salary_min" in update_dict or "salary_max" in update_dict:
                salary_min = update_dict.get("salary_min", vacancy.salary_min)
                salary_max = update_dict.get("salary_max", vacancy.salary_max)

                if salary_min > salary_max:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="salary_min не может быть больше salary_max",
                    )

            await self.validate_vacancy_foreign_keys(db, update_dict)

            for key, value in update_dict.items():
                setattr(vacancy, key, value)

            vacancy.updated_at = datetime.utcnow()

            await db.commit()

            loaded_vacancy = await self.get_vacancy_with_details(db, vacancy.id)

            if not loaded_vacancy:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Вакансия не найдена",
                )

            return self.map_vacancy(loaded_vacancy)

        except HTTPException:
            await db.rollback()
            raise

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error in update_vacancy: {e}")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка целостности данных. Проверьте ID справочников",
            )

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in update_vacancy: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных",
            )

    async def delete_vacancy(
        self,
        db: AsyncSession,
        vacancy_id: int,
        company_id: int,
    ) -> None:
        try:
            vacancy = await self.get_company_vacancy_or_404(db, vacancy_id, company_id)

            await db.delete(vacancy)
            await db.commit()

        except HTTPException:
            await db.rollback()
            raise

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in delete_vacancy: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных",
            )

    # ---------- vacancy skills ----------

    async def add_skill_to_vacancy(
        self,
        db: AsyncSession,
        vacancy_id: int,
        company_id: int,
        skill_name: str,
    ) -> dict:
        try:
            vacancy = await self.get_company_vacancy_or_404(db, vacancy_id, company_id)
            skill = await self.get_or_create_skill(db, skill_name)

            if all(existing_skill.id != skill.id for existing_skill in vacancy.skills):
                vacancy.skills.append(skill)

            vacancy.updated_at = datetime.utcnow()

            await db.commit()

            loaded_vacancy = await self.get_vacancy_with_details(db, vacancy.id)

            if not loaded_vacancy:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Вакансия не найдена",
                )

            return self.map_vacancy(loaded_vacancy)

        except HTTPException:
            await db.rollback()
            raise

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error in add_skill_to_vacancy: {e}")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось добавить навык",
            )

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in add_skill_to_vacancy: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных",
            )

    async def remove_skill_from_vacancy(
        self,
        db: AsyncSession,
        vacancy_id: int,
        company_id: int,
        skill_id: int,
    ) -> dict:
        try:
            vacancy = await self.get_company_vacancy_or_404(db, vacancy_id, company_id)

            vacancy.skills = [
                skill
                for skill in vacancy.skills
                if skill.id != skill_id
            ]

            vacancy.updated_at = datetime.utcnow()

            await db.commit()

            loaded_vacancy = await self.get_vacancy_with_details(db, vacancy.id)

            if not loaded_vacancy:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Вакансия не найдена",
                )

            return self.map_vacancy(loaded_vacancy)

        except HTTPException:
            await db.rollback()
            raise

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in remove_skill_from_vacancy: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных",
            )

    # ---------- old applications by vacancy ----------

    async def get_vacancy_applications(
        self,
        db: AsyncSession,
        vacancy_id: int,
        company_id: int,
        skip: int = 0,
        limit: int = 10,
        status_filter: Optional[str] = None,
    ) -> list[dict]:
        await self.get_company_vacancy_or_404(db, vacancy_id, company_id)

        stmt = (
            select(Application)
            .where(Application.vacancy_id == vacancy_id)
            .options(
                selectinload(Application.vacancy).selectinload(Vacancy.company),
                selectinload(Application.vacancy).selectinload(Vacancy.city),
                selectinload(Application.vacancy).selectinload(Vacancy.currency),
                selectinload(Application.resume).selectinload(Resume.profession),
                selectinload(Application.resume).selectinload(Resume.applicant),
            )
            .order_by(Application.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if status_filter:
            stmt = stmt.where(Application.status == status_filter)

        result = await db.execute(stmt)
        applications = result.scalars().all()

        return [
            self.map_application(application)
            for application in applications
        ]

    async def get_application_detail(
        self,
        db: AsyncSession,
        vacancy_id: int,
        resume_id: int,
        company_id: int,
    ) -> dict:
        await self.get_company_vacancy_or_404(db, vacancy_id, company_id)

        application = await self.get_application_with_details(db, vacancy_id, resume_id)

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Отклик не найден",
            )

        return self.map_application(application)

    async def update_application_status(
        self,
        db: AsyncSession,
        vacancy_id: int,
        resume_id: int,
        company_id: int,
        status_data: ApplicationUpdate,
    ) -> dict:
        try:
            await self.get_company_vacancy_or_404(db, vacancy_id, company_id)

            application = await self.get_application_with_details(db, vacancy_id, resume_id)

            if not application:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Отклик не найден",
                )

            application.status = self._status_value(status_data.status)
            application.updated_at = datetime.utcnow()

            await db.commit()

            loaded_application = await self.get_application_with_details(db, vacancy_id, resume_id)

            if not loaded_application:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Отклик не найден",
                )

            return self.map_application(loaded_application)

        except HTTPException:
            await db.rollback()
            raise

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in update_application_status: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных",
            )

    # ---------- employer applications page ----------

    def _application_detail_options(self):
        return (
            selectinload(Application.vacancy).selectinload(Vacancy.company),
            selectinload(Application.vacancy).selectinload(Vacancy.city),
            selectinload(Application.vacancy).selectinload(Vacancy.currency),
            selectinload(Application.vacancy).selectinload(Vacancy.profession),
            selectinload(Application.vacancy).selectinload(Vacancy.employment_type),
            selectinload(Application.vacancy).selectinload(Vacancy.work_schedule),
            selectinload(Application.vacancy).selectinload(Vacancy.experience),
            selectinload(Application.vacancy).selectinload(Vacancy.status),
            selectinload(Application.vacancy).selectinload(Vacancy.skills),
            selectinload(Application.resume).selectinload(Resume.profession),
            selectinload(Application.resume).selectinload(Resume.skills),
            selectinload(Application.resume).selectinload(Resume.work_experiences),
            selectinload(Application.resume).selectinload(Resume.changes),
            selectinload(Application.resume)
            .selectinload(Resume.applicant)
            .selectinload(Applicant.city),
            selectinload(Application.resume)
            .selectinload(Resume.applicant)
            .selectinload(Applicant.educations)
            .selectinload(Education.institution),
        )

    async def get_company_application_or_404(
        self,
        db: AsyncSession,
        application_id: int,
        company_id: int,
    ) -> Application:
        stmt = (
            select(Application)
            .join(Vacancy, Vacancy.id == Application.vacancy_id)
            .where(
                Application.id == application_id,
                Vacancy.company_id == company_id,
            )
            .options(*self._application_detail_options())
        )

        result = await db.execute(stmt)
        application = result.scalars().unique().one_or_none()

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Отклик не найден",
            )

        return application

    async def get_application_suspicion_stats(
        self,
        db: AsyncSession,
        application: Application,
        period_days: int = 30,
    ) -> dict:
        period_days = max(1, min(period_days, 365))

        now = datetime.utcnow()
        period_from = now - timedelta(days=period_days)
        since_7 = now - timedelta(days=7)
        since_30 = now - timedelta(days=30)
        since_180 = now - timedelta(days=180)

        resume = application.resume
        applicant_id = resume.applicant_id if resume else None

        if not applicant_id:
            return {
                "period_days": period_days,
                "period_from": period_from,
                "applications_count": 0,
                "pending_count": 0,
                "accepted_count": 0,
                "rejected_count": 0,
                "resume_changes_count": 0,
                "applicant_resume_changes_count": 0,
                "suspicion_score": 0,
                "is_suspicious": False,
                "suspicion_level": "normal",
                "suspicion_label": "Нормально",
                "reasons": [],
                "suspicion_reasons": [],
                "suspicion_metrics": {},
            }

        applications_stmt = (
            select(Application)
            .join(Resume, Resume.id == Application.resume_id)
            .where(
                Resume.applicant_id == applicant_id,
                Application.created_at >= since_180,
            )
            .order_by(Application.created_at.desc())
        )

        applications_result = await db.execute(applications_stmt)
        applications = list(applications_result.scalars().all())

        changes_stmt = (
            select(ResumeChange)
            .join(Resume, Resume.id == ResumeChange.resume_id)
            .where(
                Resume.applicant_id == applicant_id,
                ResumeChange.changed_at >= since_180,
            )
            .order_by(ResumeChange.changed_at.desc())
        )

        changes_result = await db.execute(changes_stmt)
        resume_changes = list(changes_result.scalars().all())

        applications_period = [
            item for item in applications
            if item.created_at and item.created_at >= period_from
        ]

        applications_7 = [
            item for item in applications
            if item.created_at and item.created_at >= since_7
        ]

        applications_30 = [
            item for item in applications
            if item.created_at and item.created_at >= since_30
        ]

        changes_period = [
            item for item in resume_changes
            if item.changed_at and item.changed_at >= period_from
        ]

        changes_7 = [
            item for item in resume_changes
            if item.changed_at and item.changed_at >= since_7
        ]

        changes_30 = [
            item for item in resume_changes
            if item.changed_at and item.changed_at >= since_30
        ]

        current_resume_changes_period = [
            item for item in changes_period
            if item.resume_id == application.resume_id
        ]

        applications_180_count = len(applications)
        applications_30_count = len(applications_30)
        applications_7_count = len(applications_7)

        changes_180_count = len(resume_changes)
        changes_30_count = len(changes_30)
        changes_7_count = len(changes_7)

        applications_count = len(applications_period)

        pending_count = sum(
            1 for item in applications_period
            if item.status == ApplicationStatus.PENDING.value
        )
        accepted_count = sum(
            1 for item in applications_period
            if item.status == ApplicationStatus.ACCEPTED.value
        )
        rejected_count = sum(
            1 for item in applications_period
            if item.status == ApplicationStatus.REJECTED.value
        )

        resume_changes_count = len(current_resume_changes_period)
        applicant_resume_changes_count = len(changes_period)

        reasons: list[str] = []

        # 1. Массовость откликов во времени — до 30 баллов.
        application_burst_score_7 = self._risk_scale(
            value=applications_7_count,
            start=15,
            full=60,
            max_score=30,
        )

        application_burst_score_30 = self._risk_scale(
            value=applications_30_count,
            start=60,
            full=180,
            max_score=25,
        )

        application_burst_score_180 = self._risk_scale(
            value=applications_180_count,
            start=300,
            full=700,
            max_score=10,
        )

        application_burst_score = max(
            application_burst_score_7,
            application_burst_score_30,
            application_burst_score_180,
        )

        if application_burst_score_7 >= 15:
            reasons.append("Слишком много откликов за последние 7 дней.")
        elif application_burst_score_30 >= 12:
            reasons.append("Высокая активность откликов за последние 30 дней.")

        # 2. Резкие изменения резюме — до 25 баллов.
        resume_change_burst_score_7 = self._risk_scale(
            value=changes_7_count,
            start=2,
            full=8,
            max_score=25,
        )

        resume_change_burst_score_30 = self._risk_scale(
            value=changes_30_count,
            start=6,
            full=18,
            max_score=18,
        )

        resume_change_burst_score_180 = self._risk_scale(
            value=changes_180_count,
            start=30,
            full=80,
            max_score=8,
        )

        resume_change_burst_score = max(
            resume_change_burst_score_7,
            resume_change_burst_score_30,
            resume_change_burst_score_180,
        )

        if resume_change_burst_score_7 >= 15:
            reasons.append("Много изменений резюме за последнюю неделю.")
        elif resume_change_burst_score_30 >= 10:
            reasons.append("Частые изменения резюме за последние 30 дней.")

        # 3. Соотношение изменений к откликам — до 25 баллов.
        ratio_180 = changes_180_count / max(applications_180_count, 1)
        ratio_30 = changes_30_count / max(applications_30_count, 1)

        ratio_score_180 = self._risk_scale(
            value=ratio_180,
            start=0.08,
            full=0.5,
            max_score=22,
        )

        ratio_score_30 = self._risk_scale(
            value=ratio_30,
            start=0.15,
            full=0.75,
            max_score=25,
        )

        edit_to_application_ratio_score = max(
            ratio_score_180,
            ratio_score_30,
        )

        if changes_180_count >= 3 and applications_180_count <= 5:
            edit_to_application_ratio_score = max(edit_to_application_ratio_score, 22)
            reasons.append("Количество изменений резюме слишком велико относительно числа откликов.")
        elif edit_to_application_ratio_score >= 12:
            reasons.append("Резюме часто менялось относительно количества откликов.")

        # 4. Сопроводительные письма — до 20 баллов.
        cover_letter_score, cover_letter_metrics, cover_letter_reasons = (
            self._calculate_cover_letter_risk(applications_30)
        )

        reasons.extend(cover_letter_reasons)

        # 5. Положительная поправка за стабильную активность.
        stability_bonus = 0

        if (
            applications_180_count >= 80
            and changes_7_count <= 2
            and ratio_180 <= 0.08
            and cover_letter_metrics["duplicate_cover_letter_ratio"] < 0.45
        ):
            stability_bonus = 10
            reasons.append(
                "Активность выглядит стабильной: много откликов за долгий период без резких изменений резюме."
            )

        raw_score = (
            application_burst_score
            + resume_change_burst_score
            + edit_to_application_ratio_score
            + cover_letter_score
            - stability_bonus
        )

        suspicion_score = max(0, min(100, round(raw_score)))
        is_suspicious = suspicion_score >= 50
        suspicion_level = self._get_suspicion_level(suspicion_score)
        suspicion_label = self._get_suspicion_label(suspicion_score)

        suspicion_metrics = {
            "applications_7_days": applications_7_count,
            "applications_30_days": applications_30_count,
            "applications_180_days": applications_180_count,
            "resume_changes_7_days": changes_7_count,
            "resume_changes_30_days": changes_30_count,
            "resume_changes_180_days": changes_180_count,
            "changes_per_application_30_days": round(ratio_30, 3),
            "changes_per_application_180_days": round(ratio_180, 3),
            "application_burst_score": round(application_burst_score, 1),
            "resume_change_burst_score": round(resume_change_burst_score, 1),
            "edit_to_application_ratio_score": round(edit_to_application_ratio_score, 1),
            "cover_letter_score": round(cover_letter_score, 1),
            "stability_bonus": stability_bonus,
            **cover_letter_metrics,
        }

        return {
            "period_days": period_days,
            "period_from": period_from,

            "applications_count": applications_count,
            "pending_count": pending_count,
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,

            "resume_changes_count": resume_changes_count,
            "applicant_resume_changes_count": applicant_resume_changes_count,

            "suspicion_score": suspicion_score,
            "is_suspicious": is_suspicious,
            "suspicion_level": suspicion_level,
            "suspicion_label": suspicion_label,

            "reasons": reasons,
            "suspicion_reasons": reasons,
            "suspicion_metrics": suspicion_metrics,
        }

    def calculate_application_match(
        self,
        application: Application,
        suspicion: dict | None = None,
    ) -> dict:
        vacancy = application.vacancy
        resume = application.resume
        applicant = resume.applicant if resume else None

        vacancy_skill_names = self._get_skill_names(vacancy.skills if vacancy else [])
        resume_skill_names = self._get_skill_names(resume.skills if resume else [])

        vacancy_skill_set = {
            self._normalize_text(skill)
            for skill in vacancy_skill_names
            if self._normalize_text(skill)
        }
        resume_skill_set = {
            self._normalize_text(skill)
            for skill in resume_skill_names
            if self._normalize_text(skill)
        }

        matching_normalized = vacancy_skill_set.intersection(resume_skill_set)

        matching_skills = [
            skill
            for skill in resume_skill_names
            if self._normalize_text(skill) in matching_normalized
        ]

        missing_skills = [
            skill
            for skill in vacancy_skill_names
            if self._normalize_text(skill) not in resume_skill_set
        ]

        if vacancy_skill_set:
            skills_match_percent = round(len(matching_normalized) / len(vacancy_skill_set) * 100)
            skills_score = round(skills_match_percent * 0.45)
        else:
            skills_match_percent = 0
            skills_score = 10 if resume_skill_set else 0

        profession_score = 0

        if vacancy and resume and vacancy.profession_id == resume.profession_id:
            profession_score = 30

        cover_letter_score = 0
        cover_letter_length = len((application.cover_letter or "").strip())

        if cover_letter_length >= 80:
            cover_letter_score = 10
        elif cover_letter_length > 0:
            cover_letter_score = 6

        city_score = 0

        if vacancy and applicant and applicant.city_id and applicant.city_id == vacancy.city_id:
            city_score = 5

        experience_years = self._calculate_experience_years(
            resume.work_experiences if resume else []
        )
        experience_score = min(10, round(experience_years * 2))

        freshness_score = 0

        if application.created_at:
            days_old = max((datetime.utcnow() - application.created_at).days, 0)
            freshness_score = max(0, 5 - min(days_old, 5))

        suspicion_penalty = 0

        if suspicion and suspicion.get("is_suspicious"):
            suspicion_penalty = 15

        score = (
            profession_score
            + skills_score
            + cover_letter_score
            + city_score
            + experience_score
            + freshness_score
            - suspicion_penalty
        )

        score = max(0, min(100, score))

        return {
            "score": score,
            "profession_score": profession_score,
            "skills_score": skills_score,
            "cover_letter_score": cover_letter_score,
            "city_score": city_score,
            "experience_score": experience_score,
            "freshness_score": freshness_score,
            "suspicion_penalty": suspicion_penalty,
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "skills_match_percent": skills_match_percent,
        }

    def map_employer_application(
        self,
        application: Application,
        suspicion: dict,
    ) -> dict:
        vacancy = application.vacancy
        resume = application.resume
        applicant = resume.applicant if resume else None

        latest_experience = self._get_latest_experience(
            resume.work_experiences if resume else []
        )

        resume_profession_name = (
            resume.profession.name
            if resume and resume.profession
            else None
        )

        vacancy_skill_names = self._get_skill_names(vacancy.skills if vacancy else [])
        resume_skill_names = self._get_skill_names(resume.skills if resume else [])

        match = self.calculate_application_match(application, suspicion)

        return {
            "id": application.id,
            "vacancy_id": application.vacancy_id,
            "resume_id": application.resume_id,
            "status": application.status,
            "status_label": self._get_application_status_label(application.status),
            "cover_letter": application.cover_letter,
            "has_cover_letter": self._has_cover_letter(application),
            "created_at": application.created_at,
            "updated_at": application.updated_at,
            "vacancy": {
                "id": vacancy.id,
                "title": vacancy.title,
                "city_name": vacancy.city.name if vacancy and vacancy.city else None,
                "profession_name": vacancy.profession.name if vacancy and vacancy.profession else None,
                "salary_min": vacancy.salary_min if vacancy else None,
                "salary_max": vacancy.salary_max if vacancy else None,
                "currency": vacancy.currency.name if vacancy and vacancy.currency else None,
                "skills": vacancy_skill_names,
            } if vacancy else None,
            "applicant": {
                "id": applicant.id if applicant else None,
                "full_name": self._get_applicant_full_name(applicant),
                "first_name": applicant.first_name if applicant else None,
                "last_name": applicant.last_name if applicant else None,
                "middle_name": applicant.middle_name if applicant else None,
                "city_name": (
                    applicant.city.name
                    if applicant and getattr(applicant, "city", None)
                    else None
                ),
                "age": self._get_applicant_age(applicant.birth_date if applicant else None),
                "gender": applicant.gender if applicant else None,
                "phone": applicant.phone if applicant else None,
                "photo": getattr(applicant, "photo", None) if applicant else None,
            },
            "resume": {
                "id": resume.id if resume else None,
                "profession_id": resume.profession_id if resume else None,
                "profession_name": resume_profession_name,
                "title": resume_profession_name or f"Резюме #{resume.id}" if resume else "Резюме",
                "skills": resume_skill_names,
                "experience_years": self._calculate_experience_years(
                    resume.work_experiences if resume else []
                ),
                "latest_position": latest_experience.position if latest_experience else None,
                "latest_company": latest_experience.company_name if latest_experience else None,
                "educations_count": len(applicant.educations or []) if applicant else 0,
                "work_experiences_count": len(resume.work_experiences or []) if resume else 0,
                "created_at": resume.created_at if resume else None,
                "updated_at": resume.updated_at if resume else None,
            },
            "match": match,
            "suspicion": suspicion,
        }

    async def get_company_applications_page(
        self,
        db: AsyncSession,
        company_id: int,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        vacancy_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        city_id: Optional[int] = None,
        profession_id: Optional[int] = None,
        skill_id: Optional[int] = None,
        skill_ids: Optional[str] = None,
        has_cover_letter: Optional[bool] = None,
        suspicious_only: Optional[bool] = None,
        score_from: Optional[int] = None,
        score_to: Optional[int] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        period_days: int = 30,
        sort_by: str = "smart",
    ) -> dict:
        try:
            stmt = (
                select(Application)
                .join(Vacancy, Vacancy.id == Application.vacancy_id)
                .where(Vacancy.company_id == company_id)
                .options(*self._application_detail_options())
            )

            if vacancy_id:
                stmt = stmt.where(Application.vacancy_id == vacancy_id)

            if status_filter:
                stmt = stmt.where(Application.status == status_filter)

            if city_id:
                stmt = stmt.where(
                    Application.resume.has(
                        Resume.applicant.has(Applicant.city_id == city_id)
                    )
                )

            if profession_id:
                stmt = stmt.where(
                    or_(
                        Vacancy.profession_id == profession_id,
                        Application.resume.has(Resume.profession_id == profession_id),
                    )
                )

            parsed_skill_ids = self._parse_optional_int_list(skill_ids)

            if skill_id:
                parsed_skill_ids.append(skill_id)

            parsed_skill_ids = list(dict.fromkeys(parsed_skill_ids))

            if parsed_skill_ids:
                stmt = stmt.where(
                    Application.resume.has(
                        Resume.skills.any(Skill.id.in_(parsed_skill_ids))
                    )
                )

            if has_cover_letter is True:
                stmt = stmt.where(
                    Application.cover_letter.is_not(None),
                    func.length(func.trim(Application.cover_letter)) > 0,
                )

            if has_cover_letter is False:
                stmt = stmt.where(
                    or_(
                        Application.cover_letter.is_(None),
                        func.length(func.trim(Application.cover_letter)) == 0,
                    )
                )

            if created_from:
                stmt = stmt.where(Application.created_at >= created_from)

            if created_to:
                stmt = stmt.where(Application.created_at <= created_to)

            if search:
                search_value = f"%{search.strip().lower()}%"

                stmt = stmt.where(
                    or_(
                        func.lower(Vacancy.title).like(search_value),
                        Vacancy.profession.has(
                            func.lower(Profession.name).like(search_value)
                        ),
                        Vacancy.skills.any(
                            func.lower(Skill.name).like(search_value)
                        ),
                        Application.resume.has(
                            Resume.profession.has(
                                func.lower(Profession.name).like(search_value)
                            )
                        ),
                        Application.resume.has(
                            Resume.skills.any(
                                func.lower(Skill.name).like(search_value)
                            )
                        ),
                        Application.resume.has(
                            Resume.applicant.has(
                                or_(
                                    func.lower(Applicant.first_name).like(search_value),
                                    func.lower(Applicant.last_name).like(search_value),
                                    func.lower(Applicant.middle_name).like(search_value),
                                )
                            )
                        ),
                    )
                )

            stmt = stmt.order_by(Application.created_at.desc(), Application.id.desc())

            result = await db.execute(stmt)
            applications = result.scalars().unique().all()

            mapped_items = []

            for application in applications:
                suspicion = await self.get_application_suspicion_stats(
                    db=db,
                    application=application,
                    period_days=period_days,
                )

                item = self.map_employer_application(application, suspicion)

                if suspicious_only is True and not item["suspicion"]["is_suspicious"]:
                    continue

                if suspicious_only is False and item["suspicion"]["is_suspicious"]:
                    continue

                if score_from is not None and item["match"]["score"] < score_from:
                    continue

                if score_to is not None and item["match"]["score"] > score_to:
                    continue

                mapped_items.append(item)

            if sort_by == "new":
                mapped_items.sort(
                    key=lambda item: item["created_at"] or datetime.min,
                    reverse=True,
                )
            elif sort_by == "old":
                mapped_items.sort(
                    key=lambda item: item["created_at"] or datetime.min,
                )
            elif sort_by == "suspicious":
                mapped_items.sort(
                    key=lambda item: item["suspicion"]["suspicion_score"],
                    reverse=True,
                )
            else:
                mapped_items.sort(
                    key=lambda item: (
                        item["match"]["score"],
                        item["has_cover_letter"],
                        item["created_at"] or datetime.min,
                    ),
                    reverse=True,
                )

            total = len(mapped_items)
            page_items = mapped_items[skip:skip + limit]

            pending = sum(
                1 for item in mapped_items
                if item["status"] == ApplicationStatus.PENDING.value
            )
            accepted = sum(
                1 for item in mapped_items
                if item["status"] == ApplicationStatus.ACCEPTED.value
            )
            rejected = sum(
                1 for item in mapped_items
                if item["status"] == ApplicationStatus.REJECTED.value
            )
            suspicious = sum(
                1 for item in mapped_items
                if item["suspicion"]["is_suspicious"]
            )
            with_cover_letter = sum(
                1 for item in mapped_items
                if item["has_cover_letter"]
            )

            average_match_score = 0

            if mapped_items:
                average_match_score = round(
                    sum(item["match"]["score"] for item in mapped_items) / len(mapped_items)
                )

            return {
                "items": page_items,
                "total": total,
                "stats": {
                    "total": total,
                    "pending": pending,
                    "accepted": accepted,
                    "rejected": rejected,
                    "suspicious": suspicious,
                    "with_cover_letter": with_cover_letter,
                    "average_match_score": average_match_score,
                },
            }

        except HTTPException:
            raise

        except SQLAlchemyError as e:
            logger.error(f"DB error in get_company_applications_page: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных",
            )

    async def get_company_application_detail_by_id(
        self,
        db: AsyncSession,
        application_id: int,
        company_id: int,
        period_days: int = 30,
    ) -> dict:
        application = await self.get_company_application_or_404(
            db=db,
            application_id=application_id,
            company_id=company_id,
        )

        suspicion = await self.get_application_suspicion_stats(
            db=db,
            application=application,
            period_days=period_days,
        )

        return self.map_employer_application(application, suspicion)

    async def get_company_application_suspicion_by_id(
        self,
        db: AsyncSession,
        application_id: int,
        company_id: int,
        period_days: int = 30,
    ) -> dict:
        application = await self.get_company_application_or_404(
            db=db,
            application_id=application_id,
            company_id=company_id,
        )

        return await self.get_application_suspicion_stats(
            db=db,
            application=application,
            period_days=period_days,
        )

    async def update_company_application_status_by_id(
        self,
        db: AsyncSession,
        application_id: int,
        company_id: int,
        status_data: EmployerApplicationStatusUpdate,
        period_days: int = 30,
    ) -> dict:
        try:
            application = await self.get_company_application_or_404(
                db=db,
                application_id=application_id,
                company_id=company_id,
            )

            application.status = self._status_value(status_data.status)
            application.updated_at = datetime.utcnow()

            await db.commit()

            loaded_application = await self.get_company_application_or_404(
                db=db,
                application_id=application_id,
                company_id=company_id,
            )

            suspicion = await self.get_application_suspicion_stats(
                db=db,
                application=loaded_application,
                period_days=period_days,
            )

            return self.map_employer_application(loaded_application, suspicion)

        except HTTPException:
            await db.rollback()
            raise

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in update_company_application_status_by_id: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных",
            )

    # ---------- candidate resumes catalog ----------

    def map_candidate_resume(self, resume: Resume) -> dict:
        applicant = resume.applicant
        profession = resume.profession
        skills = list(resume.skills or [])
        work_experiences = list(resume.work_experiences or [])
        applications = list(resume.applications or [])
        educations = list(applicant.educations or []) if applicant else []

        latest_experience = self._get_latest_experience(work_experiences)

        applicant_photo = None

        if applicant:
            applicant_photo = getattr(applicant, "photo", None)

        return {
            "id": resume.id,
            "applicant_id": resume.applicant_id,
            "applicant_full_name": self._get_applicant_full_name(applicant),
            "applicant_first_name": applicant.first_name if applicant else None,
            "applicant_last_name": applicant.last_name if applicant else None,
            "applicant_middle_name": applicant.middle_name if applicant else None,
            "applicant_city_name": (
                applicant.city.name
                if applicant and getattr(applicant, "city", None)
                else None
            ),
            "applicant_photo": applicant_photo,
            "applicant_age": self._get_applicant_age(
                applicant.birth_date if applicant else None
            ),
            "applicant_gender": applicant.gender if applicant else None,
            "applicant_phone": applicant.phone if applicant else None,
            "applicant_birth_date": self._to_date(applicant.birth_date) if applicant else None,
            "profession_id": resume.profession_id,
            "profession_name": profession.name if profession else None,
            "skills": [
                skill.name
                for skill in skills
                if getattr(skill, "name", None)
            ],
            "work_experiences": [
                {
                    "id": experience.id,
                    "company_name": experience.company_name,
                    "position": experience.position,
                    "start_date": self._to_date(experience.start_date),
                    "end_date": self._to_date(experience.end_date),
                    "description": experience.description,
                }
                for experience in work_experiences
            ],
            "educations": [
                {
                    "id": education.id,
                    "institution_id": education.institution_id,
                    "institution_name": (
                        education.institution.name
                        if getattr(education, "institution", None)
                        else None
                    ),
                    "start_date": self._to_date(education.start_date),
                    "end_date": self._to_date(education.end_date),
                }
                for education in educations
            ],
            "work_experiences_count": len(work_experiences),
            "applications_count": len(applications),
            "latest_position": (
                latest_experience.position
                if latest_experience
                else None
            ),
            "latest_company": (
                latest_experience.company_name
                if latest_experience
                else None
            ),
            "experience_years": self._calculate_experience_years(work_experiences),
            "created_at": getattr(resume, "created_at", None),
            "updated_at": getattr(resume, "updated_at", None),
        }

    def _candidate_resume_options(self):
        return (
            selectinload(Resume.applicant).selectinload(Applicant.city),
            selectinload(Resume.applicant)
            .selectinload(Applicant.educations)
            .selectinload(Education.institution),
            selectinload(Resume.profession),
            selectinload(Resume.skills),
            selectinload(Resume.work_experiences),
            selectinload(Resume.applications),
        )

    async def get_candidate_resumes(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 12,
        search: Optional[str] = None,
        city_id: Optional[int] = None,
        profession_id: Optional[int] = None,
        skill_id: Optional[int] = None,
        skill_ids: Optional[str] = None,
        experience_from: Optional[float] = None,
        experience_to: Optional[float] = None,
        has_education: Optional[bool] = None,
        education_institution_id: Optional[int] = None,
        age_from: Optional[int] = None,
        age_to: Optional[int] = None,
    ) -> dict:
        try:
            stmt = select(Resume).options(*self._candidate_resume_options())

            if city_id:
                stmt = stmt.where(
                    Resume.applicant.has(Applicant.city_id == city_id)
                )

            if profession_id:
                stmt = stmt.where(Resume.profession_id == profession_id)

            parsed_skill_ids = self._parse_optional_int_list(skill_ids)

            if skill_id:
                parsed_skill_ids.append(skill_id)

            parsed_skill_ids = list(dict.fromkeys(parsed_skill_ids))

            if parsed_skill_ids:
                stmt = stmt.where(
                    Resume.skills.any(Skill.id.in_(parsed_skill_ids))
                )

            if search:
                search_value = f"%{search.strip().lower()}%"

                stmt = stmt.where(
                    or_(
                        Resume.profession.has(
                            func.lower(Profession.name).like(search_value)
                        ),
                        Resume.applicant.has(
                            or_(
                                func.lower(Applicant.first_name).like(search_value),
                                func.lower(Applicant.last_name).like(search_value),
                                func.lower(Applicant.middle_name).like(search_value),
                            )
                        ),
                        Resume.skills.any(
                            func.lower(Skill.name).like(search_value)
                        ),
                    )
                )

            stmt = stmt.order_by(
                Resume.updated_at.desc(),
                Resume.created_at.desc(),
                Resume.id.desc(),
            )

            result = await db.execute(stmt)
            resumes = result.scalars().unique().all()

            mapped_items = [
                self.map_candidate_resume(resume)
                for resume in resumes
            ]

            if experience_from is not None:
                mapped_items = [
                    item
                    for item in mapped_items
                    if item["experience_years"] >= experience_from
                ]

            if experience_to is not None:
                mapped_items = [
                    item
                    for item in mapped_items
                    if item["experience_years"] <= experience_to
                ]

            if has_education is not None:
                mapped_items = [
                    item
                    for item in mapped_items
                    if (len(item.get("educations") or []) > 0) == has_education
                ]

            if education_institution_id is not None:
                mapped_items = [
                    item
                    for item in mapped_items
                    if any(
                        education.get("institution_id") == education_institution_id
                        for education in item.get("educations") or []
                    )
                ]

            if age_from is not None:
                mapped_items = [
                    item
                    for item in mapped_items
                    if item.get("applicant_age") is not None
                    and item["applicant_age"] >= age_from
                ]

            if age_to is not None:
                mapped_items = [
                    item
                    for item in mapped_items
                    if item.get("applicant_age") is not None
                    and item["applicant_age"] <= age_to
                ]

            total = len(mapped_items)

            return {
                "items": mapped_items[skip:skip + limit],
                "total": total,
            }

        except SQLAlchemyError as e:
            logger.error(f"DB error in get_candidate_resumes: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных",
            )

    async def get_candidate_resume_detail(
        self,
        db: AsyncSession,
        resume_id: int,
    ) -> dict:
        try:
            stmt = (
                select(Resume)
                .where(Resume.id == resume_id)
                .options(*self._candidate_resume_options())
            )

            result = await db.execute(stmt)
            resume = result.scalars().unique().one_or_none()

            if not resume:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Резюме не найдено",
                )

            return self.map_candidate_resume(resume)

        except HTTPException:
            raise

        except SQLAlchemyError as e:
            logger.error(f"DB error in get_candidate_resume_detail: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных",
            )


company_service = CompanyService()