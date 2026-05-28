from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import Select, String, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.core.hash import HashService
from src.models.model import (
    Applicant,
    Application,
    Chat,
    City,
    Company,
    CompanyType,
    Currency,
    District,
    Education,
    EducationalInstitution,
    EmploymentType,
    Experience,
    FavoriteVacancy,
    Message,
    MessageAttachment,
    Profession,
    Region,
    Resume,
    ResumeChange,
    Role,
    SettlementType,
    Skill,
    Status,
    User,
    Vacancy,
    WorkExperience,
    WorkSchedule,
    company_cities,
    resume_favorite_vacancies,
    resume_skills,
    vacancy_skills,
)
from src.redis.auth import session_manager


class AdminService:
    catalog_map: dict[str, Any] = {
    "regions": Region,
    "districts": District,
    "settlement-types": SettlementType,
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
    def _ensure_root_admin(actor: User):
        if actor.id != 1:
            raise HTTPException(
                status_code=403,
                detail="Создавать, редактировать и удалять администраторов может только главный администратор",
            )

    @staticmethod
    def _period_start(period: str) -> Optional[datetime]:
        now = datetime.utcnow()

        if period == "7d":
            return now - timedelta(days=7)
        if period == "30d":
            return now - timedelta(days=30)
        if period == "90d":
            return now - timedelta(days=90)
        if period in {"365d", "year"}:
            return now - timedelta(days=365)

        return None

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
    async def _delete_chats_by_application_ids(
        self,
        db: AsyncSession,
        application_ids: list[int],
    ) -> None:
        if not application_ids:
            return

        chat_ids_result = await db.execute(
            select(Chat.id).where(Chat.application_id.in_(application_ids))
        )
        chat_ids = list(chat_ids_result.scalars().all())

        if not chat_ids:
            return

        message_ids_result = await db.execute(
            select(Message.id).where(Message.chat_id.in_(chat_ids))
        )
        message_ids = list(message_ids_result.scalars().all())

        if message_ids:
            await db.execute(
                delete(MessageAttachment).where(
                    MessageAttachment.message_id.in_(message_ids)
                )
            )
            await db.execute(
                delete(Message).where(Message.id.in_(message_ids))
            )

        await db.execute(
            delete(Chat).where(Chat.id.in_(chat_ids))
        )


    async def _delete_applications_by_ids(
        self,
        db: AsyncSession,
        application_ids: list[int],
    ) -> None:
        if not application_ids:
            return

        await self._delete_chats_by_application_ids(db, application_ids)

        await db.execute(
            delete(Application).where(Application.id.in_(application_ids))
        )


    async def _delete_vacancies_by_ids(
        self,
        db: AsyncSession,
        vacancy_ids: list[int],
    ) -> None:
        if not vacancy_ids:
            return

        application_ids_result = await db.execute(
            select(Application.id).where(Application.vacancy_id.in_(vacancy_ids))
        )
        application_ids = list(application_ids_result.scalars().all())

        await self._delete_applications_by_ids(db, application_ids)

        favorite_ids_result = await db.execute(
            select(FavoriteVacancy.id).where(FavoriteVacancy.vacancy_id.in_(vacancy_ids))
        )
        favorite_ids = list(favorite_ids_result.scalars().all())

        if favorite_ids:
            await db.execute(
                delete(resume_favorite_vacancies).where(
                    resume_favorite_vacancies.c.favorite_vacancy_id.in_(favorite_ids)
                )
            )
            await db.execute(
                delete(FavoriteVacancy).where(FavoriteVacancy.id.in_(favorite_ids))
            )

        await db.execute(
            delete(vacancy_skills).where(vacancy_skills.c.vacancy_id.in_(vacancy_ids))
        )

        await db.execute(
            delete(Vacancy).where(Vacancy.id.in_(vacancy_ids))
        )


    async def _delete_resumes_by_ids(
        self,
        db: AsyncSession,
        resume_ids: list[int],
    ) -> None:
        if not resume_ids:
            return

        application_ids_result = await db.execute(
            select(Application.id).where(Application.resume_id.in_(resume_ids))
        )
        application_ids = list(application_ids_result.scalars().all())

        await self._delete_applications_by_ids(db, application_ids)

        await db.execute(
            delete(resume_favorite_vacancies).where(
                resume_favorite_vacancies.c.resume_id.in_(resume_ids)
            )
        )

        await db.execute(
            delete(resume_skills).where(resume_skills.c.resume_id.in_(resume_ids))
        )

        await db.execute(
            delete(ResumeChange).where(ResumeChange.resume_id.in_(resume_ids))
        )

        await db.execute(
            delete(WorkExperience).where(WorkExperience.resume_id.in_(resume_ids))
        )

        await db.execute(
            delete(Resume).where(Resume.id.in_(resume_ids))
        )


    async def _delete_cities_by_ids(
        self,
        db: AsyncSession,
        city_ids: list[int],
    ) -> None:
        if not city_ids:
            return

        vacancy_ids_result = await db.execute(
            select(Vacancy.id).where(Vacancy.city_id.in_(city_ids))
        )
        vacancy_ids = list(vacancy_ids_result.scalars().all())

        await self._delete_vacancies_by_ids(db, vacancy_ids)

        await db.execute(
            delete(company_cities).where(company_cities.c.city_id.in_(city_ids))
        )

        await db.execute(
            update(Applicant)
            .where(Applicant.city_id.in_(city_ids))
            .values(city_id=None)
        )

        await db.execute(
            delete(City).where(City.id.in_(city_ids))
        )


    async def _force_delete_catalog_item(
        self,
        db: AsyncSession,
        catalog_name: str,
        item_id: int,
    ) -> None:
        model = self._get_catalog_model(catalog_name)
        instance = await db.get(model, item_id)

        if not instance:
            raise HTTPException(status_code=404, detail="Элемент справочника не найден")

        if catalog_name == "regions":
            district_ids_result = await db.execute(
                select(District.id).where(District.region_id == item_id)
            )
            district_ids = list(district_ids_result.scalars().all())

            if district_ids:
                city_ids_result = await db.execute(
                    select(City.id).where(City.district_id.in_(district_ids))
                )
                city_ids = list(city_ids_result.scalars().all())

                await self._delete_cities_by_ids(db, city_ids)

                await db.execute(
                    delete(District).where(District.id.in_(district_ids))
                )

            await db.execute(
                delete(Region).where(Region.id == item_id)
            )
            return

        if catalog_name == "districts":
            city_ids_result = await db.execute(
                select(City.id).where(City.district_id == item_id)
            )
            city_ids = list(city_ids_result.scalars().all())

            await self._delete_cities_by_ids(db, city_ids)

            await db.execute(
                delete(District).where(District.id == item_id)
            )
            return

        if catalog_name == "settlement-types":
            city_ids_result = await db.execute(
                select(City.id).where(City.settlement_type_id == item_id)
            )
            city_ids = list(city_ids_result.scalars().all())

            await self._delete_cities_by_ids(db, city_ids)

            await db.execute(
                delete(SettlementType).where(SettlementType.id == item_id)
            )
            return

        if catalog_name == "cities":
            await self._delete_cities_by_ids(db, [item_id])
            return

        if catalog_name == "professions":
            vacancy_ids_result = await db.execute(
                select(Vacancy.id).where(Vacancy.profession_id == item_id)
            )
            vacancy_ids = list(vacancy_ids_result.scalars().all())

            resume_ids_result = await db.execute(
                select(Resume.id).where(Resume.profession_id == item_id)
            )
            resume_ids = list(resume_ids_result.scalars().all())

            await self._delete_vacancies_by_ids(db, vacancy_ids)
            await self._delete_resumes_by_ids(db, resume_ids)

            await db.execute(
                delete(Profession).where(Profession.id == item_id)
            )
            return

        if catalog_name == "skills":
            await db.execute(
                delete(vacancy_skills).where(vacancy_skills.c.skill_id == item_id)
            )
            await db.execute(
                delete(resume_skills).where(resume_skills.c.skill_id == item_id)
            )
            await db.execute(
                delete(Skill).where(Skill.id == item_id)
            )
            return

        if catalog_name == "work-schedules":
            vacancy_ids_result = await db.execute(
                select(Vacancy.id).where(Vacancy.work_schedule_id == item_id)
            )
            vacancy_ids = list(vacancy_ids_result.scalars().all())

            await self._delete_vacancies_by_ids(db, vacancy_ids)

            await db.execute(
                delete(WorkSchedule).where(WorkSchedule.id == item_id)
            )
            return

        if catalog_name == "employment-types":
            vacancy_ids_result = await db.execute(
                select(Vacancy.id).where(Vacancy.employment_type_id == item_id)
            )
            vacancy_ids = list(vacancy_ids_result.scalars().all())

            await self._delete_vacancies_by_ids(db, vacancy_ids)

            await db.execute(
                delete(EmploymentType).where(EmploymentType.id == item_id)
            )
            return

        if catalog_name == "currencies":
            vacancy_ids_result = await db.execute(
                select(Vacancy.id).where(Vacancy.currency_id == item_id)
            )
            vacancy_ids = list(vacancy_ids_result.scalars().all())

            await self._delete_vacancies_by_ids(db, vacancy_ids)

            await db.execute(
                delete(Currency).where(Currency.id == item_id)
            )
            return

        if catalog_name == "experiences":
            vacancy_ids_result = await db.execute(
                select(Vacancy.id).where(Vacancy.experience_id == item_id)
            )
            vacancy_ids = list(vacancy_ids_result.scalars().all())

            await self._delete_vacancies_by_ids(db, vacancy_ids)

            await db.execute(
                delete(Experience).where(Experience.id == item_id)
            )
            return

        if catalog_name == "statuses":
            vacancy_ids_result = await db.execute(
                select(Vacancy.id).where(Vacancy.status_id == item_id)
            )
            vacancy_ids = list(vacancy_ids_result.scalars().all())

            await self._delete_vacancies_by_ids(db, vacancy_ids)

            await db.execute(
                delete(Status).where(Status.id == item_id)
            )
            return

        if catalog_name == "educational-institutions":
            await db.execute(
                delete(Education).where(Education.institution_id == item_id)
            )

            await db.execute(
                delete(EducationalInstitution).where(EducationalInstitution.id == item_id)
            )
            return

        if catalog_name == "company-types":
            await db.execute(
                update(Company)
                .where(Company.company_type_id == item_id)
                .values(company_type_id=None)
            )

            await db.execute(
                delete(CompanyType).where(CompanyType.id == item_id)
            )
            return

        await db.delete(instance)

    async def _catalog_usage_counts(
        self,
        db: AsyncSession,
        catalog_name: str,
        item_id: int,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}

        if catalog_name == "regions":
            district_ids_result = await db.execute(
                select(District.id).where(District.region_id == item_id)
            )
            district_ids = list(district_ids_result.scalars().all())

            counts["районы"] = len(district_ids)

            if district_ids:
                city_ids_result = await db.execute(
                    select(City.id).where(City.district_id.in_(district_ids))
                )
                city_ids = list(city_ids_result.scalars().all())

                counts["города"] = len(city_ids)

                if city_ids:
                    counts["вакансии"] = await self._scalar_count(
                        db,
                        select(func.count())
                        .select_from(Vacancy)
                        .where(Vacancy.city_id.in_(city_ids)),
                    )
                    counts["соискатели"] = await self._scalar_count(
                        db,
                        select(func.count())
                        .select_from(Applicant)
                        .where(Applicant.city_id.in_(city_ids)),
                    )
                    counts["компании"] = await self._scalar_count(
                        db,
                        select(func.count(func.distinct(company_cities.c.company_id)))
                        .select_from(company_cities)
                        .where(company_cities.c.city_id.in_(city_ids)),
                    )

        elif catalog_name == "districts":
            city_ids_result = await db.execute(
                select(City.id).where(City.district_id == item_id)
            )
            city_ids = list(city_ids_result.scalars().all())

            counts["города"] = len(city_ids)

            if city_ids:
                counts["вакансии"] = await self._scalar_count(
                    db,
                    select(func.count())
                    .select_from(Vacancy)
                    .where(Vacancy.city_id.in_(city_ids)),
                )
                counts["соискатели"] = await self._scalar_count(
                    db,
                    select(func.count())
                    .select_from(Applicant)
                    .where(Applicant.city_id.in_(city_ids)),
                )
                counts["компании"] = await self._scalar_count(
                    db,
                    select(func.count(func.distinct(company_cities.c.company_id)))
                    .select_from(company_cities)
                    .where(company_cities.c.city_id.in_(city_ids)),
                )

        elif catalog_name == "settlement-types":
            city_ids_result = await db.execute(
                select(City.id).where(City.settlement_type_id == item_id)
            )
            city_ids = list(city_ids_result.scalars().all())

            counts["города"] = len(city_ids)

            if city_ids:
                counts["вакансии"] = await self._scalar_count(
                    db,
                    select(func.count())
                    .select_from(Vacancy)
                    .where(Vacancy.city_id.in_(city_ids)),
                )
                counts["соискатели"] = await self._scalar_count(
                    db,
                    select(func.count())
                    .select_from(Applicant)
                    .where(Applicant.city_id.in_(city_ids)),
                )
                counts["компании"] = await self._scalar_count(
                    db,
                    select(func.count(func.distinct(company_cities.c.company_id)))
                    .select_from(company_cities)
                    .where(company_cities.c.city_id.in_(city_ids)),
                )

        elif catalog_name == "cities":
            counts["вакансии"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(Vacancy)
                .where(Vacancy.city_id == item_id),
            )
            counts["соискатели"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(Applicant)
                .where(Applicant.city_id == item_id),
            )
            counts["компании"] = await self._scalar_count(
                db,
                select(func.count(func.distinct(company_cities.c.company_id)))
                .select_from(company_cities)
                .where(company_cities.c.city_id == item_id),
            )

        elif catalog_name == "professions":
            counts["вакансии"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(Vacancy)
                .where(Vacancy.profession_id == item_id),
            )
            counts["резюме"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(Resume)
                .where(Resume.profession_id == item_id),
            )

        elif catalog_name == "skills":
            counts["вакансии"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(vacancy_skills)
                .where(vacancy_skills.c.skill_id == item_id),
            )
            counts["резюме"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(resume_skills)
                .where(resume_skills.c.skill_id == item_id),
            )

        elif catalog_name == "work-schedules":
            counts["вакансии"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(Vacancy)
                .where(Vacancy.work_schedule_id == item_id),
            )

        elif catalog_name == "employment-types":
            counts["вакансии"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(Vacancy)
                .where(Vacancy.employment_type_id == item_id),
            )

        elif catalog_name == "currencies":
            counts["вакансии"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(Vacancy)
                .where(Vacancy.currency_id == item_id),
            )

        elif catalog_name == "experiences":
            counts["вакансии"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(Vacancy)
                .where(Vacancy.experience_id == item_id),
            )

        elif catalog_name == "statuses":
            counts["вакансии"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(Vacancy)
                .where(Vacancy.status_id == item_id),
            )

        elif catalog_name == "educational-institutions":
            counts["образование"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(Education)
                .where(Education.institution_id == item_id),
            )

        elif catalog_name == "company-types":
            counts["компании"] = await self._scalar_count(
                db,
                select(func.count())
                .select_from(Company)
                .where(Company.company_type_id == item_id),
            )

        return {key: value for key, value in counts.items() if value > 0}

    async def list_catalog_items(
        self,
        db: AsyncSession,
        catalog_name: str,
        skip: int,
        limit: int,
        search: Optional[str] = None,
    ):
        model = self._get_catalog_model(catalog_name)

        if catalog_name == "districts":
            stmt = select(District).options(joinedload(District.region)).order_by(District.id)
        elif catalog_name == "cities":
            stmt = (
                select(City)
                .options(
                    joinedload(City.district).joinedload(District.region),
                    joinedload(City.settlement_type),
                )
                .order_by(City.id)
            )
        else:
            stmt = select(model).order_by(model.id)

        if search:
            value = f"%{search.lower()}%"

            if catalog_name == "districts":
                stmt = stmt.join(District.region).where(
                    or_(
                        func.lower(District.name).like(value),
                        func.lower(Region.name).like(value),
                        func.cast(District.id, String).like(value),
                    )
                )
            elif catalog_name == "cities":
                stmt = (
                    stmt.join(City.district)
                    .join(District.region)
                    .join(City.settlement_type)
                    .where(
                        or_(
                            func.lower(City.name).like(value),
                            func.lower(District.name).like(value),
                            func.lower(Region.name).like(value),
                            func.lower(SettlementType.name).like(value),
                            func.cast(City.id, String).like(value),
                        )
                    )
                )
            else:
                stmt = stmt.where(
                    or_(
                        func.lower(model.name).like(value),
                        func.cast(model.id, String).like(value),
                    )
                )

        result = await db.execute(stmt.offset(skip).limit(limit))
        return result.scalars().unique().all()

    async def _get_default_settlement_type(self, db: AsyncSession) -> SettlementType:
        result = await db.execute(select(SettlementType).where(SettlementType.name == "г."))
        settlement_type = result.scalar_one_or_none()

        if settlement_type:
            return settlement_type

        settlement_type = SettlementType(name="г.")
        db.add(settlement_type)
        await db.flush()
        return settlement_type

    async def create_catalog_item(
        self,
        db: AsyncSession,
        catalog_name: str,
        name: str,
        region_id: Optional[int] = None,
        district_id: Optional[int] = None,
        settlement_type_id: Optional[int] = None,
    ):
        model = self._get_catalog_model(catalog_name)
        normalized_name = name.strip()

        if catalog_name == "districts":
            if not region_id:
                raise HTTPException(status_code=422, detail="Выберите область")
            if not await db.get(Region, region_id):
                raise HTTPException(status_code=404, detail="Область не найдена")
            instance = District(name=normalized_name, region_id=region_id)

        elif catalog_name == "cities":
            if not district_id:
                raise HTTPException(status_code=422, detail="Выберите район")
            if not await db.get(District, district_id):
                raise HTTPException(status_code=404, detail="Район не найден")

            if settlement_type_id:
                settlement_type = await db.get(SettlementType, settlement_type_id)
                if not settlement_type:
                    raise HTTPException(status_code=404, detail="Тип населённого пункта не найден")
            else:
                settlement_type = await self._get_default_settlement_type(db)

            instance = City(
                name=normalized_name,
                district_id=district_id,
                settlement_type_id=settlement_type.id,
            )

        else:
            instance = model(name=normalized_name)

        db.add(instance)

        try:
            await db.flush()
            instance_id = instance.id
            await db.commit()
            return await self.get_catalog_item(db, catalog_name, instance_id)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Элемент с такими данными уже существует")

    async def get_catalog_item(self, db: AsyncSession, catalog_name: str, item_id: int):
        model = self._get_catalog_model(catalog_name)

        if catalog_name == "districts":
            stmt = select(District).where(District.id == item_id).options(joinedload(District.region))
        elif catalog_name == "cities":
            stmt = (
                select(City)
                .where(City.id == item_id)
                .options(
                    joinedload(City.district).joinedload(District.region),
                    joinedload(City.settlement_type),
                )
            )
        else:
            stmt = select(model).where(model.id == item_id)

        result = await db.execute(stmt)
        instance = result.scalar_one_or_none()

        if not instance:
            raise HTTPException(status_code=404, detail="Элемент справочника не найден")

        return instance

    async def update_catalog_item(
        self,
        db: AsyncSession,
        catalog_name: str,
        item_id: int,
        name: str,
        region_id: Optional[int] = None,
        district_id: Optional[int] = None,
        settlement_type_id: Optional[int] = None,
    ):
        model = self._get_catalog_model(catalog_name)
        instance = await db.get(model, item_id)

        if not instance:
            raise HTTPException(status_code=404, detail="Элемент справочника не найден")

        instance.name = name.strip()

        if catalog_name == "districts":
            if not region_id:
                raise HTTPException(status_code=422, detail="Выберите область")
            if not await db.get(Region, region_id):
                raise HTTPException(status_code=404, detail="Область не найдена")
            instance.region_id = region_id

        elif catalog_name == "cities":
            if not district_id:
                raise HTTPException(status_code=422, detail="Выберите район")
            if not await db.get(District, district_id):
                raise HTTPException(status_code=404, detail="Район не найден")
            instance.district_id = district_id

            if settlement_type_id:
                if not await db.get(SettlementType, settlement_type_id):
                    raise HTTPException(status_code=404, detail="Тип населённого пункта не найден")
                instance.settlement_type_id = settlement_type_id

        try:
            await db.commit()
            return await self.get_catalog_item(db, catalog_name, item_id)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Элемент с такими данными уже существует")

    async def delete_catalog_item(
        self,
        db: AsyncSession,
        catalog_name: str,
        item_id: int,
        force: bool = False,
    ):
        model = self._get_catalog_model(catalog_name)
        instance = await db.get(model, item_id)

        if not instance:
            raise HTTPException(status_code=404, detail="Элемент справочника не найден")

        usages = await self._catalog_usage_counts(db, catalog_name, item_id)

        if usages and not force:
            usage_text = ", ".join(f"{name}: {count}" for name, count in usages.items())

            raise HTTPException(
                status_code=409,
                detail={
                    "requires_confirmation": True,
                    "catalog_name": catalog_name,
                    "item_id": item_id,
                    "item_name": instance.name,
                    "usages": usages,
                    "message": (
                        f"Элемент «{instance.name}» используется: {usage_text}. "
                        "При подтверждении связанные данные будут удалены или отвязаны."
                    ),
                },
            )

        try:
            if force:
                await self._force_delete_catalog_item(
                    db=db,
                    catalog_name=catalog_name,
                    item_id=item_id,
                )
            else:
                await db.delete(instance)

            await db.commit()
        except Exception:
            await db.rollback()
            raise

    async def get_dashboard(self, db: AsyncSession, period: str = "30d"):
        users_total = await self._scalar_count(db, select(func.count()).select_from(User))
        users_active = await self._scalar_count(
            db,
            select(func.count()).select_from(User).where(User.is_active.is_(True)),
        )
        users_blocked = await self._scalar_count(
            db,
            select(func.count()).select_from(User).where(User.is_active.is_(False)),
        )
        companies_total = await self._scalar_count(db, select(func.count()).select_from(Company))
        applicants_total = await self._scalar_count(db, select(func.count()).select_from(Applicant))
        vacancies_total = await self._scalar_count(db, select(func.count()).select_from(Vacancy))
        applications_total = await self._scalar_count(db, select(func.count()).select_from(Application))
        admins_total = await self._scalar_count(
            db,
            select(func.count(User.id)).select_from(User).join(Role, User.role_id == Role.id).where(Role.name == "admin"),
        )

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

        role_rows = await db.execute(
            select(Role.name, func.count(User.id))
            .select_from(Role)
            .outerjoin(User, User.role_id == Role.id)
            .group_by(Role.name)
            .order_by(Role.name)
        )
        users_by_role = {name: int(count or 0) for name, count in role_rows.all()}

        start = self._period_start(period)
        registrations_stmt = (
            select(User)
            .options(joinedload(User.role))
            .order_by(User.created_at)
        )

        if start:
            registrations_stmt = registrations_stmt.where(User.created_at >= start)

        registrations_result = await db.execute(registrations_stmt)
        registration_users = registrations_result.scalars().all()

        registration_map: dict[str, dict[str, Any]] = {}

        for user in registration_users:
            key = user.created_at.date().isoformat()
            if key not in registration_map:
                registration_map[key] = {
                    "label": user.created_at.strftime("%d.%m"),
                    "date": key,
                    "users": 0,
                    "applicants": 0,
                    "companies": 0,
                    "admins": 0,
                }

            registration_map[key]["users"] += 1

            role_name = user.role.name if user.role else ""
            if role_name == "applicant":
                registration_map[key]["applicants"] += 1
            elif role_name == "company":
                registration_map[key]["companies"] += 1
            elif role_name == "admin":
                registration_map[key]["admins"] += 1

        registrations = list(registration_map.values())

        city_rows = await db.execute(
            select(City, func.count(Applicant.id))
            .select_from(City)
            .options(
                joinedload(City.district).joinedload(District.region),
                joinedload(City.settlement_type),
            )
            .outerjoin(Applicant, Applicant.city_id == City.id)
            .group_by(City.id)
            .order_by(func.count(Applicant.id).desc())
            .limit(8)
        )
        top_cities = [
            {"key": str(city.id), "label": city.full_name, "value": int(count or 0)}
            for city, count in city_rows.unique().all()
            if int(count or 0) > 0
        ]

        profession_rows = await db.execute(
            select(Profession.name, func.count(Vacancy.id))
            .select_from(Profession)
            .outerjoin(Vacancy, Vacancy.profession_id == Profession.id)
            .group_by(Profession.name)
            .order_by(func.count(Vacancy.id).desc())
            .limit(8)
        )
        top_professions = [
            {"key": name, "label": name, "value": int(count or 0)}
            for name, count in profession_rows.all()
            if int(count or 0) > 0
        ]

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
            .order_by(Application.created_at.desc())
            .limit(5)
        )

        return {
            "users_total": users_total,
            "users_active": users_active,
            "users_blocked": users_blocked,
            "companies_total": companies_total,
            "applicants_total": applicants_total,
            "vacancies_total": vacancies_total,
            "applications_total": applications_total,
            "admins_total": admins_total,
            "vacancies_by_status": vacancies_by_status,
            "applications_by_status": applications_by_status,
            "users_by_role": users_by_role,
            "registrations": registrations,
            "top_cities": top_cities,
            "top_professions": top_professions,
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
            search_value = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(User.email).like(search_value),
                    func.cast(User.id, String).like(search_value),
                )
            )

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

        if user.id == 1 and is_active is False:
            raise HTTPException(status_code=400, detail="Главного администратора нельзя заблокировать")

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
        city: Optional[str] = None,
        company_type: Optional[str] = None,
    ):
        stmt = (
            select(Company)
            .options(
                joinedload(Company.company_type),
                joinedload(Company.user),
                selectinload(Company.cities).joinedload(City.district).joinedload(District.region),
                selectinload(Company.cities).joinedload(City.settlement_type),
                selectinload(Company.vacancies),
            )
            .order_by(Company.id)
        )

        if search:
            search_value = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Company.name).like(search_value),
                    func.lower(func.coalesce(Company.website, "")).like(search_value),
                    func.cast(Company.id, String).like(search_value),
                )
            )

        if city:
            stmt = stmt.join(Company.cities).where(func.lower(City.name) == city.lower())

        if company_type:
            stmt = stmt.join(Company.company_type).where(func.lower(CompanyType.name) == company_type.lower())

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
                selectinload(Company.cities).joinedload(City.district).joinedload(District.region),
                selectinload(Company.cities).joinedload(City.settlement_type),
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
        city: Optional[str] = None,
        has_resumes: Optional[bool] = None,
    ):
        stmt = (
            select(Applicant)
            .options(
                selectinload(Applicant.city).joinedload(City.district).joinedload(District.region),
                selectinload(Applicant.city).joinedload(City.settlement_type),
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
                    func.lower(func.coalesce(Applicant.middle_name, "")).like(search_value),
                    func.lower(func.coalesce(Applicant.phone, "")).like(search_value),
                    func.cast(Applicant.id, String).like(search_value),
                )
            )

        if city:
            stmt = stmt.join(Applicant.city).where(func.lower(City.name) == city.lower())

        if has_resumes is not None:
            resumes_count = (
                select(func.count(Resume.id))
                .where(Resume.applicant_id == Applicant.id)
                .correlate(Applicant)
                .scalar_subquery()
            )
            stmt = stmt.where(resumes_count > 0 if has_resumes else resumes_count == 0)

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
                joinedload(Applicant.city).joinedload(City.district).joinedload(District.region),
                joinedload(Applicant.city).joinedload(City.settlement_type),
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
                joinedload(Vacancy.city).joinedload(City.district).joinedload(District.region),
                joinedload(Vacancy.city).joinedload(City.settlement_type),
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
            value = f"%{search.lower()}%"
            stmt = stmt.join(Vacancy.company).where(
                or_(
                    func.lower(Vacancy.title).like(value),
                    func.lower(Vacancy.description).like(value),
                    func.lower(Company.name).like(value),
                    func.cast(Vacancy.id, String).like(value),
                )
            )

        if status_id:
            stmt = stmt.where(Vacancy.status_id == status_id)
        if city_id:
            stmt = stmt.where(Vacancy.city_id == city_id)
        if profession_id:
            stmt = stmt.where(Vacancy.profession_id == profession_id)
        if company_id:
            stmt = stmt.where(Vacancy.company_id == company_id)

        result = await db.execute(stmt.offset(skip).limit(limit))
        return result.scalars().unique().all()

    async def get_vacancy(self, db: AsyncSession, vacancy_id: int):
        stmt = (
            select(Vacancy)
            .where(Vacancy.id == vacancy_id)
            .options(
                joinedload(Vacancy.company),
                joinedload(Vacancy.city).joinedload(City.district).joinedload(District.region),
                joinedload(Vacancy.city).joinedload(City.settlement_type),
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
        vacancy.updated_at = datetime.utcnow()
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
            vacancy.updated_at = datetime.utcnow()

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
                joinedload(Application.vacancy).joinedload(Vacancy.city).joinedload(City.district).joinedload(District.region),
                joinedload(Vacancy.city).joinedload(City.settlement_type),
                joinedload(Application.resume).joinedload(Resume.profession),
                joinedload(Application.resume).joinedload(Resume.applicant),
            )
            .order_by(Application.created_at.desc())
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
                joinedload(Application.vacancy).joinedload(Vacancy.city).joinedload(City.district).joinedload(District.region),
                joinedload(Vacancy.city).joinedload(City.settlement_type),
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
        stmt = select(Application).where(
            Application.vacancy_id == vacancy_id,
            Application.resume_id == resume_id,
        )
        result = await db.execute(stmt)
        application = result.scalar_one_or_none()

        if not application:
            raise HTTPException(status_code=404, detail="Отклик не найден")

        application.status = status_value.strip()
        application.updated_at = datetime.utcnow()
        await db.commit()

        return await self.get_application_detail(db, vacancy_id, resume_id)

    async def list_admins(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ):
        stmt = (
            select(User)
            .join(Role, User.role_id == Role.id)
            .where(Role.name == "admin")
            .options(joinedload(User.role))
            .order_by(User.id)
        )

        if search:
            value = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(User.email).like(value),
                    func.cast(User.id, String).like(value),
                )
            )

        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

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

    async def create_admin(self, db: AsyncSession, email: str, password: str, actor: User):
        self._ensure_root_admin(actor)

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
        self._ensure_root_admin(actor)

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
        self._ensure_root_admin(actor)

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