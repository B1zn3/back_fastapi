from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.models.model import (
    Applicant,
    Application,
    City,
    Company,
    Currency,
    EducationalInstitution,
    EmploymentType,
    Experience,
    Profession,
    Role,
    Skill,
    Status,
    User,
    Vacancy,
    WorkSchedule,
)


class AdminService:
    catalog_map: dict[str, Any] = {
        "cities": City,
        "professions": Profession,
        "skills": Skill,
        "currencies": Currency,
        "experiences": Experience,
        "statuses": Status,
        "work-schedules": WorkSchedule,
        "employment-types": EmploymentType,
        "educational-institutions": EducationalInstitution,
    }

    def _get_catalog_model(self, catalog_name: str):
        model = self.catalog_map.get(catalog_name)
        if not model:
            raise HTTPException(status_code=404, detail="Справочник не найден")
        return model

    async def list_catalog_items(self, db: AsyncSession, catalog_name: str, skip: int, limit: int):
        model = self._get_catalog_model(catalog_name)
        result = await db.execute(select(model).order_by(model.id).offset(skip).limit(limit))
        return result.scalars().all()

    async def create_catalog_item(self, db: AsyncSession, catalog_name: str, name: str):
        model = self._get_catalog_model(catalog_name)
        instance = model(name=name)
        db.add(instance)
        try:
            await db.commit()
            await db.refresh(instance)
            return instance
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Элемент с таким названием уже существует")

    async def update_catalog_item(self, db: AsyncSession, catalog_name: str, item_id: int, name: str):
        model = self._get_catalog_model(catalog_name)
        instance = await db.get(model, item_id)
        if not instance:
            raise HTTPException(status_code=404, detail="Элемент справочника не найден")
        instance.name = name
        try:
            await db.commit()
            await db.refresh(instance)
            return instance
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Элемент с таким названием уже существует")

    async def delete_catalog_item(self, db: AsyncSession, catalog_name: str, item_id: int):
        model = self._get_catalog_model(catalog_name)
        instance = await db.get(model, item_id)
        if not instance:
            raise HTTPException(status_code=404, detail="Элемент справочника не найден")
        await db.delete(instance)
        await db.commit()

    async def list_users(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ):
        stmt = select(User).options(joinedload(User.role)).order_by(User.id)
        if role:
            stmt = stmt.join(User.role).where(Role.name == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if search:
            stmt = stmt.where(func.lower(User.email).like(f"%{search.lower()}%"))

        result = await db.execute(stmt.offset(skip).limit(limit))
        return result.scalars().all()

    async def update_user_status(self, db: AsyncSession, user_id: int, is_active: bool):
        user = await db.get(User, user_id, options=[joinedload(User.role)])
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        user.is_active = is_active
        await db.commit()
        await db.refresh(user)
        return user

    async def list_companies(self, db: AsyncSession, skip: int, limit: int, search: Optional[str] = None):
        stmt = select(Company).options(selectinload(Company.vacancies)).order_by(Company.id)
        if search:
            stmt = stmt.where(func.lower(Company.name).like(f"%{search.lower()}%"))
        result = await db.execute(stmt.offset(skip).limit(limit))
        return result.scalars().all()

    async def delete_company(self, db: AsyncSession, company_id: int):
        company = await db.get(Company, company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Компания не найдена")
        await db.delete(company)
        await db.commit()

    async def list_applicants(self, db: AsyncSession, skip: int, limit: int):
        stmt = (
            select(Applicant)
            .options(selectinload(Applicant.city), selectinload(Applicant.resumes), selectinload(Applicant.educations))
            .order_by(Applicant.id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def delete_applicant(self, db: AsyncSession, applicant_id: int):
        applicant = await db.get(Applicant, applicant_id)
        if not applicant:
            raise HTTPException(status_code=404, detail="Соискатель не найден")
        await db.delete(applicant)
        await db.commit()

    async def list_vacancies(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
        search: Optional[str] = None,
        status_id: Optional[int] = None,
        city_id: Optional[int] = None,
        profession_id: Optional[int] = None,
        company_id: Optional[int] = None,
    ):
        stmt = (
            select(Vacancy)
            .options(
                joinedload(Vacancy.company),
                joinedload(Vacancy.city),
                joinedload(Vacancy.profession),
                joinedload(Vacancy.employment_type),
                joinedload(Vacancy.work_schedule),
                joinedload(Vacancy.currency),
                joinedload(Vacancy.experience),
                joinedload(Vacancy.status),
                selectinload(Vacancy.skills),
            )
            .order_by(Vacancy.created_at.desc())
        )

        if search:
            stmt = stmt.where(func.lower(Vacancy.title).like(f"%{search.lower()}%"))
        if status_id:
            stmt = stmt.where(Vacancy.status_id == status_id)
        if city_id:
            stmt = stmt.where(Vacancy.city_id == city_id)
        if profession_id:
            stmt = stmt.where(Vacancy.profession_id == profession_id)
        if company_id:
            stmt = stmt.where(Vacancy.company_id == company_id)

        result = await db.execute(stmt.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_vacancy(self, db: AsyncSession, vacancy_id: int):
        stmt = (
            select(Vacancy)
            .where(Vacancy.id == vacancy_id)
            .options(
                joinedload(Vacancy.company),
                joinedload(Vacancy.city),
                joinedload(Vacancy.profession),
                joinedload(Vacancy.employment_type),
                joinedload(Vacancy.work_schedule),
                joinedload(Vacancy.currency),
                joinedload(Vacancy.experience),
                joinedload(Vacancy.status),
                selectinload(Vacancy.skills),
            )
        )
        result = await db.execute(stmt)
        vacancy = result.scalar_one_or_none()
        if not vacancy:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        return vacancy

    async def update_vacancy_status(self, db: AsyncSession, vacancy_id: int, status_id: int):
        vacancy = await db.get(Vacancy, vacancy_id)
        if not vacancy:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        status_entity = await db.get(Status, status_id)
        if not status_entity:
            raise HTTPException(status_code=404, detail="Статус не найден")
        vacancy.status_id = status_id
        await db.commit()
        return await self.get_vacancy(db, vacancy_id)

    async def delete_vacancy(self, db: AsyncSession, vacancy_id: int):
        vacancy = await db.get(Vacancy, vacancy_id)
        if not vacancy:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        await db.delete(vacancy)
        await db.commit()

    async def list_applications(self, db: AsyncSession, skip: int, limit: int, status_filter: Optional[str] = None):
        stmt = (
            select(Application)
            .options(joinedload(Application.vacancy), joinedload(Application.resume))
            .order_by(Application.vacancy_id.desc())
        )
        if status_filter:
            stmt = stmt.where(Application.status == status_filter)

        result = await db.execute(stmt.offset(skip).limit(limit))
        return result.scalars().all()


admin_service = AdminService()
