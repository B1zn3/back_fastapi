from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.models.model import (
    City,
    Company,
    Currency,
    District,
    EducationalInstitution,
    EmploymentType,
    Experience,
    Profession,
    Region,
    SettlementType,
    Skill,
    Status,
    Vacancy,
    WorkSchedule,
    company_cities,
)


class PublicService:
    active_status_name = "Активна"

    catalog_map = {
        "regions": Region,
        "districts": District,
        "settlement-types": SettlementType,
        "professions": Profession,
        "experiences": Experience,
        "work-schedules": WorkSchedule,
        "employment-types": EmploymentType,
        "educational-institutions": EducationalInstitution,
        "skills": Skill,
        "currencies": Currency,
        "statuses": Status,
    }

    @staticmethod
    def _parse_ids_csv(value: Optional[str]) -> list[int]:
        if not value:
            return []

        ids: list[int] = []

        for item in value.split(","):
            item = item.strip()

            if item and item.isdigit():
                ids.append(int(item))

        return ids

    @staticmethod
    def _format_city_full_name(city: City | None) -> Optional[str]:
        if not city:
            return None

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

    def _city_to_dict(self, city: City | None) -> Optional[dict]:
        if not city:
            return None

        return {
            "id": city.id,
            "name": city.name,
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
            "full_name": self._format_city_full_name(city),
        }

    def _company_city_names(self, company: Company | None) -> list[str]:
        if not company:
            return []

        return [
            full_name
            for full_name in (
                self._format_city_full_name(city)
                for city in company.cities or []
            )
            if full_name
        ]

    def _company_cities(self, company: Company | None) -> list[dict]:
        if not company:
            return []

        return [
            city_dict
            for city_dict in (
                self._city_to_dict(city)
                for city in company.cities or []
            )
            if city_dict
        ]

    def _map_vacancy_list_item(self, vacancy: Vacancy) -> dict:
        city_full_name = self._format_city_full_name(vacancy.city)

        return {
            "id": vacancy.id,
            "title": vacancy.title,
            "description": vacancy.description,
            "salary_min": vacancy.salary_min,
            "salary_max": vacancy.salary_max,
            "created_at": vacancy.created_at,

            "company_id": vacancy.company_id,
            "company_name": vacancy.company.name if vacancy.company else None,

            "city_id": vacancy.city_id,
            "city_name": city_full_name,
            "city_full_name": city_full_name,
            "city": self._city_to_dict(vacancy.city),

            "profession_name": vacancy.profession.name if vacancy.profession else None,
            "employment_type": vacancy.employment_type.name if vacancy.employment_type else None,
            "work_schedule": vacancy.work_schedule.name if vacancy.work_schedule else None,
            "experience": vacancy.experience.name if vacancy.experience else None,
            "currency": vacancy.currency.name if vacancy.currency else None,
            "skills": [skill.name for skill in vacancy.skills] if vacancy.skills else [],
        }

    def _map_vacancy_detail(self, vacancy: Vacancy) -> dict:
        company = vacancy.company
        city_full_name = self._format_city_full_name(vacancy.city)

        return {
            "id": vacancy.id,
            "title": vacancy.title,
            "description": vacancy.description,
            "salary_min": vacancy.salary_min,
            "salary_max": vacancy.salary_max,
            "created_at": vacancy.created_at,
            "updated_at": vacancy.updated_at,

            "company_id": vacancy.company_id,
            "company_name": company.name if company else None,

            "city_id": vacancy.city_id,
            "city_name": city_full_name,
            "city_full_name": city_full_name,
            "city": self._city_to_dict(vacancy.city),

            "profession_name": vacancy.profession.name if vacancy.profession else None,
            "employment_type": vacancy.employment_type.name if vacancy.employment_type else None,
            "work_schedule": vacancy.work_schedule.name if vacancy.work_schedule else None,
            "currency": vacancy.currency.name if vacancy.currency else None,
            "experience": vacancy.experience.name if vacancy.experience else None,
            "skills": [skill.name for skill in vacancy.skills] if vacancy.skills else [],

            "company_type_name": (
                company.company_type.name
                if company and company.company_type
                else None
            ),
            "company_description": company.description if company else None,
            "company_website": company.website if company else None,
            "company_logo": company.logo if company else None,
            "company_founded_year": company.founded_year if company else None,
            "company_employee_count": company.employee_count if company else None,

            # Совместимость со старым фронтом
            "company_city_names": self._company_city_names(company),

            # Новая логика: можно читать полные объекты городов
            "company_cities": self._company_cities(company),
        }

    async def get_catalog_items(
        self,
        db: AsyncSession,
        catalog_name: str,
        skip: int = 0,
        limit: int = 100,
    ):
        if catalog_name == "regions":
            result = await db.execute(
                select(Region)
                .order_by(Region.name.asc())
                .offset(skip)
                .limit(limit)
            )

            regions = result.scalars().all()

            return [
                {
                    "id": region.id,
                    "name": region.name,
                }
                for region in regions
            ]

        if catalog_name == "districts":
            result = await db.execute(
                select(District)
                .options(joinedload(District.region))
                .order_by(District.name.asc())
                .offset(skip)
                .limit(limit)
            )

            districts = result.scalars().unique().all()

            return [
                {
                    "id": district.id,
                    "name": district.name,
                    "region_id": district.region_id,
                    "region_name": district.region.name if district.region else None,
                }
                for district in districts
            ]

        if catalog_name == "cities":
            result = await db.execute(
                select(City)
                .options(
                    joinedload(City.district).joinedload(District.region),
                    joinedload(City.settlement_type),
                )
                .order_by(City.name.asc())
                .offset(skip)
                .limit(limit)
            )

            cities = result.scalars().unique().all()

            return [
                self._city_to_dict(city)
                for city in cities
            ]

        model = self.catalog_map.get(catalog_name)

        if not model:
            raise HTTPException(status_code=404, detail="Справочник не найден")

        result = await db.execute(
            select(model)
            .order_by(model.name.asc())
            .offset(skip)
            .limit(limit)
        )

        items = result.scalars().all()

        return [
            {
                "id": item.id,
                "name": item.name,
            }
            for item in items
        ]

    async def list_catalog_items(
        self,
        db: AsyncSession,
        catalog_name: str,
        skip: int,
        limit: int,
    ):
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
                joinedload(Vacancy.city).joinedload(City.district).joinedload(District.region),
                joinedload(Vacancy.city).joinedload(City.settlement_type),
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
            stmt = (
                stmt
                .join(Vacancy.company)
                .where(
                    or_(
                        func.lower(Vacancy.title).like(search_value),
                        func.lower(Vacancy.description).like(search_value),
                        func.lower(Company.name).like(search_value),
                    )
                )
            )

        result = await db.execute(stmt.offset(skip).limit(limit))
        vacancies = result.scalars().unique().all()

        return [
            self._map_vacancy_list_item(vacancy)
            for vacancy in vacancies
        ]

    async def get_vacancy_detail(
        self,
        db: AsyncSession,
        vacancy_id: int,
    ):
        stmt = (
            select(Vacancy)
            .join(Vacancy.status)
            .where(
                Vacancy.id == vacancy_id,
                Status.name == self.active_status_name,
            )
            .options(
                joinedload(Vacancy.company).joinedload(Company.company_type),
                joinedload(Vacancy.company)
                .selectinload(Company.cities)
                .joinedload(City.district)
                .joinedload(District.region),
                joinedload(Vacancy.company)
                .selectinload(Company.cities)
                .joinedload(City.settlement_type),
                joinedload(Vacancy.city).joinedload(City.district).joinedload(District.region),
                joinedload(Vacancy.city).joinedload(City.settlement_type),
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

        return self._map_vacancy_detail(vacancy)

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
                selectinload(Company.cities).joinedload(City.district).joinedload(District.region),
                selectinload(Company.cities).joinedload(City.settlement_type),
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
            first_letter = (
                company.name.strip()[0].upper()
                if company.name and company.name.strip()
                else "#"
            )

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
                    "city_names": self._company_city_names(company),
                    "cities": self._company_cities(company),
                    "first_letter": first_letter,
                    "company_type_name": company.company_type.name if company.company_type else None,
                }
            )

        return items

    async def get_company_detail(
        self,
        db: AsyncSession,
        company_id: int,
    ):
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
                selectinload(Company.cities).joinedload(City.district).joinedload(District.region),
                selectinload(Company.cities).joinedload(City.settlement_type),
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
            "city_names": self._company_city_names(company),
            "cities": self._company_cities(company),
            "first_letter": (
                company.name.strip()[0].upper()
                if company.name and company.name.strip()
                else "#"
            ),
            "company_type_name": company.company_type.name if company.company_type else None,
        }

    async def get_professions(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
    ):
        stmt = (
            select(Profession)
            .order_by(Profession.name.asc())
            .offset(skip)
            .limit(limit)
        )

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