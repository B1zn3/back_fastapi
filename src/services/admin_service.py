from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.core.hash import HashService
from src.models.model import (
    Applicant,
    Application,
    City,
    Company,
    CompanyType,
    Currency,
    Education,
    EducationalInstitution,
    EmploymentType,
    Experience,
    Profession,
    Resume,
    Role,
    Skill,
    Status,
    User,
    Vacancy,
    WorkSchedule,
    company_cities,
    resume_skills,
    vacancy_skills,
)
from src.redis.auth import session_manager


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
        "company-types": CompanyType,
    }

    def _get_catalog_model(self, catalog_name: str):
        model = self.catalog_map.get(catalog_name)
        if not model:
            raise HTTPException(status_code=404, detail="Справочник не найден")
        return model

    @staticmethod
    def _full_name(applicant: Optional[Applicant]) -> str:
        if not applicant:
            return "—"
        parts = [applicant.last_name, applicant.first_name, applicant.middle_name]
        value = " ".join(part for part in parts if part)
        return value or f"Соискатель #{applicant.id}"

    async def _scalar_count(self, db: AsyncSession, stmt: Select):
        result = await db.execute(stmt)
        value = result.scalar_one_or_none()
        return int(value or 0)

    async def _get_admin_role(self, db: AsyncSession) -> Role:
        result = await db.execute(select(Role).where(Role.name == "admin"))
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Роль admin не найдена")
        return role

    async def _count_active_admins(self, db: AsyncSession) -> int:
        return await self._scalar_count(
            db,
            select(func.count(User.id))
            .select_from(User)
            .join(Role, User.role_id == Role.id)
            .where(Role.name == "admin", User.is_active.is_(True)),
        )

    async def _catalog_usage_counts(
        self,
        db: AsyncSession,
        catalog_name: str,
        item_id: int,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}

        if catalog_name == "cities":
            counts["соискателях"] = await self._scalar_count(
                db,
                select(func.count()).select_from(Applicant).where(Applicant.city_id == item_id),
            )
            counts["вакансиях"] = await self._scalar_count(
                db,
                select(func.count()).select_from(Vacancy).where(Vacancy.city_id == item_id),
            )
            counts["компаниях"] = await self._scalar_count(
                db,
                select(func.count()).select_from(company_cities).where(company_cities.c.city_id == item_id),
            )

        elif catalog_name == "professions":
            counts["резюме"] = await self._scalar_count(
                db,
                select(func.count()).select_from(Resume).where(Resume.profession_id == item_id),
            )
            counts["вакансиях"] = await self._scalar_count(
                db,
                select(func.count()).select_from(Vacancy).where(Vacancy.profession_id == item_id),
            )

        elif catalog_name == "skills":
            counts["резюме"] = await self._scalar_count(
                db,
                select(func.count()).select_from(resume_skills).where(resume_skills.c.skill_id == item_id),
            )
            counts["вакансиях"] = await self._scalar_count(
                db,
                select(func.count()).select_from(vacancy_skills).where(vacancy_skills.c.skill_id == item_id),
            )

        elif catalog_name == "currencies":
            counts["вакансиях"] = await self._scalar_count(
                db,
                select(func.count()).select_from(Vacancy).where(Vacancy.currency_id == item_id),
            )

        elif catalog_name == "experiences":
            counts["вакансиях"] = await self._scalar_count(
                db,
                select(func.count()).select_from(Vacancy).where(Vacancy.experience_id == item_id),
            )

        elif catalog_name == "statuses":
            counts["вакансиях"] = await self._scalar_count(
                db,
                select(func.count()).select_from(Vacancy).where(Vacancy.status_id == item_id),
            )

        elif catalog_name == "work-schedules":
            counts["вакансиях"] = await self._scalar_count(
                db,
                select(func.count()).select_from(Vacancy).where(Vacancy.work_schedule_id == item_id),
            )

        elif catalog_name == "employment-types":
            counts["вакансиях"] = await self._scalar_count(
                db,
                select(func.count()).select_from(Vacancy).where(Vacancy.employment_type_id == item_id),
            )

        elif catalog_name == "educational-institutions":
            counts["образовании"] = await self._scalar_count(
                db,
                select(func.count()).select_from(Education).where(Education.institution_id == item_id),
            )

        return {key: value for key, value in counts.items() if value > 0}

    async def list_catalog_items(self, db: AsyncSession, catalog_name: str, skip: int, limit: int):
        model = self._get_catalog_model(catalog_name)
        result = await db.execute(select(model).order_by(model.id).offset(skip).limit(limit))
        return result.scalars().all()

    async def create_catalog_item(self, db: AsyncSession, catalog_name: str, name: str):
        model = self._get_catalog_model(catalog_name)
        instance = model(name=name.strip())
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

        instance.name = name.strip()

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

        usages = await self._catalog_usage_counts(db, catalog_name, item_id)
        if usages:
            usage_text = ", ".join(f"{name}: {count}" for name, count in usages.items())
            raise HTTPException(
                status_code=409,
                detail=f"Нельзя удалить элемент справочника, он используется в следующих сущностях: {usage_text}",
            )

        await db.delete(instance)
        await db.commit()

    async def get_dashboard(self, db: AsyncSession):
        users_total = await self._scalar_count(db, select(func.count()).select_from(User))
        users_active = await self._scalar_count(
            db,
            select(func.count()).select_from(User).where(User.is_active.is_(True)),
        )
        companies_total = await self._scalar_count(db, select(func.count()).select_from(Company))
        applicants_total = await self._scalar_count(db, select(func.count()).select_from(Applicant))
        vacancies_total = await self._scalar_count(db, select(func.count()).select_from(Vacancy))
        applications_total = await self._scalar_count(db, select(func.count()).select_from(Application))

        status_rows = await db.execute(
            select(Status.name, func.count(Vacancy.id))
            .select_from(Status)
            .outerjoin(Vacancy, Vacancy.status_id == Status.id)
            .group_by(Status.name)
            .order_by(Status.name)
        )
        vacancies_by_status = {name: int(count or 0) for name, count in status_rows.all()}

        application_rows = await db.execute(
            select(Application.status, func.count())
            .group_by(Application.status)
            .order_by(Application.status)
        )
        applications_by_status = {name: int(count or 0) for name, count in application_rows.all()}

        recent_users_result = await db.execute(
            select(User)
            .options(joinedload(User.role))
            .order_by(User.created_at.desc())
            .limit(5)
        )

        recent_vacancies_result = await db.execute(
            select(Vacancy)
            .options(joinedload(Vacancy.company), joinedload(Vacancy.status))
            .order_by(Vacancy.created_at.desc())
            .limit(5)
        )

        recent_applications_result = await db.execute(
            select(Application)
            .options(
                joinedload(Application.vacancy).joinedload(Vacancy.company),
                joinedload(Application.resume).joinedload(Resume.profession),
            )
            .order_by(Application.vacancy_id.desc(), Application.resume_id.desc())
            .limit(5)
        )

        return {
            "users_total": users_total,
            "users_active": users_active,
            "companies_total": companies_total,
            "applicants_total": applicants_total,
            "vacancies_total": vacancies_total,
            "applications_total": applications_total,
            "vacancies_by_status": vacancies_by_status,
            "applications_by_status": applications_by_status,
            "recent_users": recent_users_result.scalars().all(),
            "recent_vacancies": recent_vacancies_result.scalars().all(),
            "recent_applications": recent_applications_result.scalars().all(),
        }

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

    async def get_user_detail(self, db: AsyncSession, user_id: int):
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                joinedload(User.role),
                joinedload(User.company).selectinload(Company.vacancies),
                joinedload(User.applicant)
                .selectinload(Applicant.resumes)
                .selectinload(Resume.applications),
            )
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        return user

    async def update_user_status(self, db: AsyncSession, user_id: int, is_active: bool):
        user = await db.get(User, user_id, options=[joinedload(User.role)])

        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        user.is_active = is_active
        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)
        return user

    async def list_companies(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ):
        stmt = (
            select(Company)
            .options(
                joinedload(Company.company_type),
                joinedload(Company.user),
                selectinload(Company.cities),
                selectinload(Company.vacancies),
            )
            .order_by(Company.id)
        )

        if search:
            stmt = stmt.where(func.lower(Company.name).like(f"%{search.lower()}%"))

        if is_active is not None:
            stmt = stmt.join(Company.user, isouter=True).where(
                or_(User.is_active == is_active, Company.user == None)  # noqa: E711
            )

        result = await db.execute(stmt.offset(skip).limit(limit))
        return result.scalars().unique().all()

    async def get_company_detail(self, db: AsyncSession, company_id: int):
        stmt = (
            select(Company)
            .where(Company.id == company_id)
            .options(
                joinedload(Company.company_type),
                joinedload(Company.user),
                selectinload(Company.cities),
                selectinload(Company.vacancies).joinedload(Vacancy.status),
            )
        )
        result = await db.execute(stmt)
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Компания не найдена")

        return company

    async def update_company_status(self, db: AsyncSession, company_id: int, is_active: bool):
        company = await self.get_company_detail(db, company_id)

        if not company.user:
            raise HTTPException(status_code=409, detail="Компания не связана с пользователем")

        company.user.is_active = is_active
        company.user.updated_at = datetime.utcnow()

        await db.commit()
        return await self.get_company_detail(db, company_id)

    async def delete_company(self, db: AsyncSession, company_id: int):
        company = await db.get(Company, company_id)

        if not company:
            raise HTTPException(status_code=404, detail="Компания не найдена")

        await db.delete(company)
        await db.commit()

    async def list_applicants(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ):
        stmt = (
            select(Applicant)
            .options(
                selectinload(Applicant.city),
                selectinload(Applicant.user),
                selectinload(Applicant.resumes),
                selectinload(Applicant.educations),
            )
            .order_by(Applicant.id)
        )

        if search:
            search_value = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(func.coalesce(Applicant.first_name, "")).like(search_value),
                    func.lower(func.coalesce(Applicant.last_name, "")).like(search_value),
                    func.lower(func.coalesce(Applicant.phone, "")).like(search_value),
                )
            )

        if is_active is not None:
            stmt = stmt.join(Applicant.user, isouter=True).where(
                or_(User.is_active == is_active, Applicant.user == None)  # noqa: E711
            )

        result = await db.execute(stmt.offset(skip).limit(limit))
        return result.scalars().unique().all()

    async def get_applicant_detail(self, db: AsyncSession, applicant_id: int):
        stmt = (
            select(Applicant)
            .where(Applicant.id == applicant_id)
            .options(
                joinedload(Applicant.city),
                joinedload(Applicant.user),
                selectinload(Applicant.educations).joinedload(Education.institution),
                selectinload(Applicant.resumes).joinedload(Resume.profession),
                selectinload(Applicant.resumes).selectinload(Resume.skills),
                selectinload(Applicant.resumes).selectinload(Resume.work_experiences),
                selectinload(Applicant.resumes).selectinload(Resume.applications),
            )
        )
        result = await db.execute(stmt)
        applicant = result.scalar_one_or_none()

        if not applicant:
            raise HTTPException(status_code=404, detail="Соискатель не найден")

        return applicant

    async def update_applicant_status(self, db: AsyncSession, applicant_id: int, is_active: bool):
        applicant = await self.get_applicant_detail(db, applicant_id)

        if not applicant.user:
            raise HTTPException(status_code=409, detail="Соискатель не связан с пользователем")

        applicant.user.is_active = is_active
        applicant.user.updated_at = datetime.utcnow()

        await db.commit()
        return await self.get_applicant_detail(db, applicant_id)

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

    async def bulk_update_vacancy_status(self, db: AsyncSession, vacancy_ids: list[int], status_id: int):
        status_entity = await db.get(Status, status_id)
        if not status_entity:
            raise HTTPException(status_code=404, detail="Статус не найден")

        if not vacancy_ids:
            return []

        result = await db.execute(select(Vacancy).where(Vacancy.id.in_(vacancy_ids)))
        vacancies = result.scalars().all()

        for vacancy in vacancies:
            vacancy.status_id = status_id

        await db.commit()
        return vacancies

    async def delete_vacancy(self, db: AsyncSession, vacancy_id: int):
        vacancy = await db.get(Vacancy, vacancy_id)

        if not vacancy:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")

        await db.delete(vacancy)
        await db.commit()

    async def list_applications(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
        status_filter: Optional[str] = None,
        company_id: Optional[int] = None,
        vacancy_id: Optional[int] = None,
        applicant_id: Optional[int] = None,
    ):
        stmt = (
            select(Application)
            .join(Application.vacancy)
            .join(Application.resume)
            .options(
                joinedload(Application.vacancy).joinedload(Vacancy.company),
                joinedload(Application.vacancy).joinedload(Vacancy.city),
                joinedload(Application.resume).joinedload(Resume.profession),
                joinedload(Application.resume).joinedload(Resume.applicant),
            )
            .order_by(Vacancy.created_at.desc(), Application.resume_id.desc())
        )

        if status_filter:
            stmt = stmt.where(Application.status == status_filter)
        if company_id:
            stmt = stmt.where(Vacancy.company_id == company_id)
        if vacancy_id:
            stmt = stmt.where(Application.vacancy_id == vacancy_id)
        if applicant_id:
            stmt = stmt.where(Resume.applicant_id == applicant_id)

        result = await db.execute(stmt.offset(skip).limit(limit))
        return result.scalars().unique().all()

    async def get_application_detail(self, db: AsyncSession, vacancy_id: int, resume_id: int):
        stmt = (
            select(Application)
            .where(Application.vacancy_id == vacancy_id, Application.resume_id == resume_id)
            .options(
                joinedload(Application.vacancy).joinedload(Vacancy.company),
                joinedload(Application.vacancy).joinedload(Vacancy.city),
                joinedload(Application.resume).joinedload(Resume.profession),
                joinedload(Application.resume).joinedload(Resume.applicant),
            )
        )
        result = await db.execute(stmt)
        application = result.scalar_one_or_none()

        if not application:
            raise HTTPException(status_code=404, detail="Отклик не найден")

        return application

    async def update_application_status(
        self,
        db: AsyncSession,
        vacancy_id: int,
        resume_id: int,
        status_value: str,
    ):
        application = await db.get(Application, {"vacancy_id": vacancy_id, "resume_id": resume_id})

        if not application:
            raise HTTPException(status_code=404, detail="Отклик не найден")

        application.status = status_value.strip()
        await db.commit()

        return await self.get_application_detail(db, vacancy_id, resume_id)

    async def list_admins(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
        search: Optional[str] = None,
    ):
        stmt = (
            select(User)
            .join(Role, User.role_id == Role.id)
            .where(Role.name == "admin")
            .options(joinedload(User.role))
            .order_by(User.id)
        )

        if search:
            stmt = stmt.where(func.lower(User.email).like(f"%{search.lower()}%"))

        result = await db.execute(stmt.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_admin_detail(self, db: AsyncSession, admin_id: int):
        stmt = (
            select(User)
            .join(Role, User.role_id == Role.id)
            .where(User.id == admin_id, Role.name == "admin")
            .options(joinedload(User.role))
        )
        result = await db.execute(stmt)
        admin = result.scalar_one_or_none()

        if not admin:
            raise HTTPException(status_code=404, detail="Администратор не найден")

        return admin

    async def create_admin(self, db: AsyncSession, email: str, password: str):
        normalized_email = email.lower().strip()

        existing = await db.execute(select(User).where(User.email == normalized_email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")

        admin_role = await self._get_admin_role(db)

        user = User(
            email=normalized_email,
            password=HashService.get_password_hash(password),
            role_id=admin_role.id,
            is_active=True,
            company_id=None,
            applicant_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    async def update_admin(
        self,
        db: AsyncSession,
        admin_id: int,
        actor: User,
        email: Optional[str],
        new_password: Optional[str],
        is_active: Optional[bool],
        current_admin_password: str,
    ):
        if not HashService.verify_password(current_admin_password, actor.password):
            raise HTTPException(status_code=403, detail="Неверный пароль администратора")

        admin = await self.get_admin_detail(db, admin_id)

        if actor.id == admin.id and is_active is False:
            raise HTTPException(status_code=400, detail="Нельзя заблокировать самого себя")

        if is_active is False:
            active_admins_count = await self._count_active_admins(db)
            if active_admins_count <= 1 and admin.is_active:
                raise HTTPException(
                    status_code=400,
                    detail="Нельзя заблокировать последнего активного администратора",
                )

        if email:
            normalized_email = email.lower().strip()
            if normalized_email != admin.email:
                existing = await db.execute(
                    select(User).where(User.email == normalized_email, User.id != admin.id)
                )
                if existing.scalar_one_or_none():
                    raise HTTPException(status_code=409, detail="Email уже используется")
                admin.email = normalized_email

        if new_password:
            admin.password = HashService.get_password_hash(new_password)

        if is_active is not None:
            admin.is_active = is_active

        admin.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(admin)

        if new_password or is_active is False:
            await session_manager.delete_all_sessions(str(admin.id))

        return admin

    async def delete_admin(
        self,
        db: AsyncSession,
        admin_id: int,
        actor: User,
        current_admin_password: str,
    ):
        if not HashService.verify_password(current_admin_password, actor.password):
            raise HTTPException(status_code=403, detail="Неверный пароль администратора")

        admin = await self.get_admin_detail(db, admin_id)

        if actor.id == admin.id:
            raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")

        active_admins_count = await self._count_active_admins(db)
        if active_admins_count <= 1 and admin.is_active:
            raise HTTPException(
                status_code=400,
                detail="Нельзя удалить последнего активного администратора",
            )

        await session_manager.delete_all_sessions(str(admin.id))
        await db.delete(admin)
        await db.commit()


admin_service = AdminService()