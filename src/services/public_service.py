from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.models.model import (
    City,
    EducationalInstitution,
    EmploymentType,
    Experience,
    Profession,
    Status,
    WorkSchedule,
    Vacancy,
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
    }

    async def get_catalog_items(self, db: AsyncSession, catalog_name: str, skip: int, limit: int):
        model = self.catalog_map.get(catalog_name)
        if not model:
            raise HTTPException(status_code=404, detail="Справочник не найден")

        result = await db.execute(select(model).order_by(model.id).offset(skip).limit(limit))
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
        search: Optional[str] = None,
    ):
        stmt = (
            select(Vacancy)
            .join(Vacancy.status)
            .where(Status.name == self.active_status_name)
            .options(joinedload(Vacancy.company), joinedload(Vacancy.city), joinedload(Vacancy.profession))
            .order_by(Vacancy.created_at.desc())
        )

        if city_id:
            stmt = stmt.where(Vacancy.city_id == city_id)
        if profession_id:
            stmt = stmt.where(Vacancy.profession_id == profession_id)
        if company_id:
            stmt = stmt.where(Vacancy.company_id == company_id)
        if search:
            stmt = stmt.where(func.lower(Vacancy.title).like(f"%{search.lower()}%"))

        result = await db.execute(stmt.offset(skip).limit(limit))
        vacancies = result.scalars().all()
        return [
            {
                "id": v.id,
                "title": v.title,
                "description": v.description,
                "salary_min": v.salary_min,
                "salary_max": v.salary_max,
                "created_at": v.created_at,
                "company_name": v.company.name,
                "city_name": v.city.name,
                "profession_name": v.profession.name,
            }
            for v in vacancies
        ]

    async def get_vacancy_detail(self, db: AsyncSession, vacancy_id: int):
        stmt = (
            select(Vacancy)
            .join(Vacancy.status)
            .where(Vacancy.id == vacancy_id, Status.name == self.active_status_name)
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
            "company_name": vacancy.company.name,
            "city_name": vacancy.city.name,
            "profession_name": vacancy.profession.name,
            "employment_type": vacancy.employment_type.name,
            "work_schedule": vacancy.work_schedule.name,
            "currency": vacancy.currency.name,
            "experience": vacancy.experience.name,
            "skills": [s.name for s in vacancy.skills],
                        "company_description": vacancy.company.description,
            "company_website": vacancy.company.website,
            "company_logo": vacancy.company.logo,
            "company_founded_year": vacancy.company.founded_year,
            "company_employee_count": vacancy.company.employee_count,
        }


public_service = PublicService()
