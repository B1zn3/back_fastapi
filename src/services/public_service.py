from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.models.model import (
    City,
    Company,
    EducationalInstitution,
    EmploymentType,
    Experience,
    Profession,
    Skill,
    Status,
    Vacancy,
    WorkSchedule,
    company_cities,
)


class PublicService:
    active_status_name = "Активна"

    catalog_map = {
        "cities": City,
        "professions": Profession,
        "experiences": Experience,
        "work-schedules": WorkSchedule,
        "employment-types": EmploymentType,
        "educational-institutions": EducationalInstitution,
        "skills": Skill,
    }

    @staticmethod
    def _parse_ids_csv(value: Optional[str]) -> list[int]:
        if not value:
            return []

        ids: list[int] = []
        for item in value.split(","):
            item = item.strip()
            if not item:
                continue
            if item.isdigit():
                ids.append(int(item))

        return ids

    async def get_catalog_items(self, db: AsyncSession, catalog_name: str, skip: int, limit: int):
        model = self.catalog_map.get(catalog_name)
        if not model:
            raise HTTPException(status_code=404, detail="Справочник не найден")

        result = await db.execute(
            select(model).order_by(model.name.asc()).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def list_catalog_items(self, db: AsyncSession, catalog_name: str, skip: int, limit: int):
        return await self.get_catalog_items(db, catalog_name, skip, limit)

    async def get_vacancies(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
        city_id: Optional[int] = None,
        profession_id: Optional[int] = None,
        company_id: Optional[int] = None,
        employment_type_id: Optional[int] = None,
        experience_id: Optional[int] = None,
        work_schedule_id: Optional[int] = None,
        salary_from: Optional[int] = None,
        salary_to: Optional[int] = None,
        search: Optional[str] = None,
    ):
        stmt = (
            select(Vacancy)
            .join(Vacancy.status)
            .where(Status.name == self.active_status_name)
            .options(
                joinedload(Vacancy.company),
                joinedload(Vacancy.city),
                joinedload(Vacancy.profession),
                joinedload(Vacancy.employment_type),
                joinedload(Vacancy.work_schedule),
                joinedload(Vacancy.currency),
                joinedload(Vacancy.experience),
                selectinload(Vacancy.skills),
            )
            .order_by(Vacancy.created_at.desc())
        )

        if city_id:
            stmt = stmt.where(Vacancy.city_id == city_id)
        if profession_id:
            stmt = stmt.where(Vacancy.profession_id == profession_id)
        if company_id:
            stmt = stmt.where(Vacancy.company_id == company_id)
        if employment_type_id:
            stmt = stmt.where(Vacancy.employment_type_id == employment_type_id)
        if experience_id:
            stmt = stmt.where(Vacancy.experience_id == experience_id)
        if work_schedule_id:
            stmt = stmt.where(Vacancy.work_schedule_id == work_schedule_id)
        if salary_from is not None:
            stmt = stmt.where(Vacancy.salary_max >= salary_from)
        if salary_to is not None:
            stmt = stmt.where(Vacancy.salary_min <= salary_to)

        if search:
            search_value = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Vacancy.title).like(search_value),
                    func.lower(Vacancy.description).like(search_value),
                    func.lower(Company.name).like(search_value),
                )
            ).join(Vacancy.company)

        result = await db.execute(stmt.offset(skip).limit(limit))
        vacancies = result.scalars().unique().all()

        return [
            {
                "id": v.id,
                "title": v.title,
                "description": v.description,
                "salary_min": v.salary_min,
                "salary_max": v.salary_max,
                "created_at": v.created_at,
                "company_name": v.company.name if v.company else None,
                "city_name": v.city.name if v.city else None,
                "profession_name": v.profession.name if v.profession else None,
                "employment_type": v.employment_type.name if v.employment_type else None,
                "work_schedule": v.work_schedule.name if v.work_schedule else None,
                "experience": v.experience.name if v.experience else None,
                "currency": v.currency.name if v.currency else None,
                "skills": [s.name for s in v.skills] if v.skills else [],
            }
            for v in vacancies
        ]

    async def get_vacancy_detail(self, db: AsyncSession, vacancy_id: int):
        stmt = (
            select(Vacancy)
            .join(Vacancy.status)
            .where(Vacancy.id == vacancy_id, Status.name == self.active_status_name)
            .options(
                joinedload(Vacancy.company).selectinload(Company.cities),
                joinedload(Vacancy.company).joinedload(Company.company_type),
                joinedload(Vacancy.city),
                joinedload(Vacancy.profession),
                joinedload(Vacancy.employment_type),
                joinedload(Vacancy.work_schedule),
                joinedload(Vacancy.currency),
                joinedload(Vacancy.experience),
                selectinload(Vacancy.skills),
            )
        )
        result = await db.execute(stmt)
        vacancy = result.scalar_one_or_none()

        if not vacancy:
            raise HTTPException(status_code=404, detail="Вакансия не найдена или недоступна")

        return {
            "id": vacancy.id,
            "title": vacancy.title,
            "description": vacancy.description,
            "salary_min": vacancy.salary_min,
            "salary_max": vacancy.salary_max,
            "created_at": vacancy.created_at,
            "updated_at": vacancy.updated_at,
            "company_name": vacancy.company.name if vacancy.company else None,
            "city_name": vacancy.city.name if vacancy.city else None,
            "profession_name": vacancy.profession.name if vacancy.profession else None,
            "employment_type": vacancy.employment_type.name if vacancy.employment_type else None,
            "work_schedule": vacancy.work_schedule.name if vacancy.work_schedule else None,
            "currency": vacancy.currency.name if vacancy.currency else None,
            "experience": vacancy.experience.name if vacancy.experience else None,
            "skills": [s.name for s in vacancy.skills],
            "company_type_name": (
                vacancy.company.company_type.name
                if vacancy.company and vacancy.company.company_type
                else None
            ),
            "company_description": vacancy.company.description if vacancy.company else None,
            "company_website": vacancy.company.website if vacancy.company else None,
            "company_logo": vacancy.company.logo if vacancy.company else None,
            "company_founded_year": vacancy.company.founded_year if vacancy.company else None,
            "company_employee_count": vacancy.company.employee_count if vacancy.company else None,
            "company_cities": [city.name for city in vacancy.company.cities] if vacancy.company else [],
        }

    async def get_companies(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
        city_ids: Optional[str] = None,
        has_vacancies_only: bool = False,
        search: Optional[str] = None,
    ):
        parsed_city_ids = self._parse_ids_csv(city_ids)

        vacancies_subq = (
            select(
                Vacancy.company_id.label("company_id"),
                func.count(Vacancy.id).label("vacancies_count"),
            )
            .join(Vacancy.status)
            .where(Status.name == self.active_status_name)
            .group_by(Vacancy.company_id)
            .subquery()
        )

        stmt = (
            select(
                Company,
                func.coalesce(vacancies_subq.c.vacancies_count, 0).label("vacancies_count"),
            )
            .outerjoin(vacancies_subq, vacancies_subq.c.company_id == Company.id)
            .options(
                selectinload(Company.cities),
                joinedload(Company.company_type),
            )
            .order_by(Company.name.asc())
        )

        if parsed_city_ids:
            company_ids_subq = (
                select(company_cities.c.company_id)
                .where(company_cities.c.city_id.in_(parsed_city_ids))
                .distinct()
            )
            stmt = stmt.where(Company.id.in_(company_ids_subq))

        if has_vacancies_only:
            stmt = stmt.where(func.coalesce(vacancies_subq.c.vacancies_count, 0) > 0)

        if search:
            stmt = stmt.where(func.lower(Company.name).like(f"%{search.lower()}%"))

        result = await db.execute(stmt.offset(skip).limit(limit))
        rows = result.unique().all()

        items = []
        for company, vacancies_count in rows:
            first_letter = company.name.strip()[0].upper() if company.name and company.name.strip() else "#"

            items.append(
                {
                    "id": company.id,
                    "name": company.name,
                    "description": company.description,
                    "website": company.website,
                    "logo": company.logo,
                    "founded_year": company.founded_year,
                    "employee_count": company.employee_count,
                    "vacancies_count": int(vacancies_count or 0),
                    "city_names": [city.name for city in company.cities],
                    "first_letter": first_letter,
                    "company_type_name": company.company_type.name if company.company_type else None,
                }
            )

        return items

    async def get_company_detail(self, db: AsyncSession, company_id: int):
        vacancies_subq = (
            select(
                Vacancy.company_id.label("company_id"),
                func.count(Vacancy.id).label("vacancies_count"),
            )
            .join(Vacancy.status)
            .where(Status.name == self.active_status_name)
            .group_by(Vacancy.company_id)
            .subquery()
        )

        stmt = (
            select(
                Company,
                func.coalesce(vacancies_subq.c.vacancies_count, 0).label("vacancies_count"),
            )
            .outerjoin(vacancies_subq, vacancies_subq.c.company_id == Company.id)
            .where(Company.id == company_id)
            .options(
                selectinload(Company.cities),
                joinedload(Company.company_type),
            )
        )

        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Компания не найдена или недоступна")

        company, vacancies_count = row

        return {
            "id": company.id,
            "name": company.name,
            "description": company.description,
            "website": company.website,
            "logo": company.logo,
            "founded_year": company.founded_year,
            "employee_count": company.employee_count,
            "vacancies_count": int(vacancies_count or 0),
            "city_names": [city.name for city in company.cities],
            "first_letter": company.name.strip()[0].upper() if company.name and company.name.strip() else "#",
            "company_type_name": company.company_type.name if company.company_type else None,
        }

    async def get_professions(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
    ):
        stmt = select(Profession).order_by(Profession.name.asc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        professions = result.scalars().all()

        return [
            {
                "id": profession.id,
                "name": profession.name,
            }
            for profession in professions
        ]


public_service = PublicService()