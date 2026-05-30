from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.cruds.applicant_cruds.applicant_crud import applicantcrud
from src.cruds.applicant_cruds.education_crud import educationcrud
from src.cruds.applicant_cruds.favorite_vacancy_crud import favoritevacancycrud
from src.cruds.applicant_cruds.resume_change_crud import resumechangecrud
from src.cruds.applicant_cruds.resume_crud import resumecrud
from src.cruds.applicant_cruds.work_experience_crud import workexperiencecrud
from src.cruds.city_crud import citycrud
from src.cruds.company_cruds.vacancy_crud import vacancycrud
from src.cruds.educational_institution_crud import educationalinstitutioncrud
from src.cruds.profession_crud import professioncrud
from src.cruds.skill_crud import skillcrud
from src.models.model import (
    Applicant,
    City,
    District,
    Education,
    FavoriteVacancy,
    Resume,
    Vacancy,
    WorkExperience,
)
from src.schemas.applicant_schemas.applicant_schema import ApplicantUpdate
from src.schemas.applicant_schemas.education_schema import EducationCreate, EducationUpdate
from src.schemas.applicant_schemas.resume_schema import ResumeCreate, ResumeUpdate
from src.schemas.applicant_schemas.work_experience_schema import (
    WorkExperienceCreate,
    WorkExperienceUpdate,
)
from src.core.exceptions import (
    AccessDeniedError,
    ApplicantNotFoundError,
    EducationNotFoundError,
    ResumeNotFoundError,
)
from src.utils.logger import logger
from src.services.files.file_storage_service import (
    FileStorageError,
    FileValidationError,
    file_storage_service,
)


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ApplicantService:
    def __init__(self):
        self.applicantcrud = applicantcrud
        self.resumecrud = resumecrud
        self.resumechangecrud = resumechangecrud
        self.workexperiencecrud = workexperiencecrud
        self.educationcrud = educationcrud
        self.citycrud = citycrud
        self.professioncrud = professioncrud
        self.skillcrud = skillcrud
        self.educationalinstitutioncrud = educationalinstitutioncrud
        self.favoritevacancycrud = favoritevacancycrud
        self.vacancycrud = vacancycrud

    # ---------- Вспомогательные методы ----------

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

    def _city_to_dict(self, city: City | None) -> dict | None:
        if not city:
            return None

        return {
            "id": city.id,
            "name": city.name,
            "full_name": self._format_city_full_name(city),
            "region_id": city.district.region_id if city.district else None,
            "region_name": (
                city.district.region.name
                if city.district and city.district.region
                else None
            ),
            "district_id": city.district_id,
            "district_name": city.district.name if city.district else None,
            "settlement_type_id": city.settlement_type_id,
            "settlement_type_name": (
                city.settlement_type.name
                if city.settlement_type
                else None
            ),
        }

    def _applicant_to_dict(self, applicant: Applicant) -> dict:
        return {
            "id": applicant.id,
            "photo": applicant.photo,
            "phone": applicant.phone,
            "birth_date": applicant.birth_date,
            "gender": applicant.gender,
            "first_name": applicant.first_name,
            "last_name": applicant.last_name,
            "middle_name": applicant.middle_name,
            "city": self._city_to_dict(applicant.city),
            "resumes": applicant.resumes or [],
            "educations": applicant.educations or [],
        }

    async def _get_applicant_or_raise(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Applicant:
        applicant = await self.applicantcrud.get_by_user_id_with_details(db, user_id)

        if not applicant:
            raise ApplicantNotFoundError()

        return applicant

    async def _get_applicant_with_details_for_response(
        self,
        db: AsyncSession,
        applicant_id: int,
    ) -> Applicant:
        result = await db.execute(
            select(Applicant)
            .where(Applicant.id == applicant_id)
            .options(
                joinedload(Applicant.city)
                .joinedload(City.district)
                .joinedload(District.region),
                joinedload(Applicant.city).joinedload(City.settlement_type),

                selectinload(Applicant.resumes).joinedload(Resume.profession),
                selectinload(Applicant.resumes).selectinload(Resume.skills),
                selectinload(Applicant.resumes).selectinload(Resume.work_experiences),

                selectinload(Applicant.educations).joinedload(Education.institution),
            )
        )

        applicant = result.scalar_one_or_none()

        if not applicant:
            raise ApplicantNotFoundError()

        return applicant

    async def _get_resume_or_raise(
        self,
        db: AsyncSession,
        resume_id: int,
        applicant_id: int,
    ) -> Resume:
        resume = await self.resumecrud.get_with_details(db, resume_id)

        if not resume:
            raise ResumeNotFoundError()

        if resume.applicant_id != applicant_id:
            raise AccessDeniedError("Резюме не принадлежит текущему пользователю")

        return resume

    async def _get_work_exp_or_raise(
        self,
        db: AsyncSession,
        exp_id: int,
        resume_id: int,
        applicant_id: int,
    ) -> WorkExperience:
        exp = await self.workexperiencecrud.get(db, exp_id)

        if not exp:
            raise HTTPException(status_code=404, detail="Опыт работы не найден")

        if exp.resume_id != resume_id:
            raise AccessDeniedError("Опыт работы не принадлежит данному резюме")

        await self._get_resume_or_raise(db, resume_id, applicant_id)

        return exp

    async def _record_resume_change(
        self,
        db: AsyncSession,
        resume_id: int,
        changed_at: datetime | None = None,
    ) -> None:
        await self.resumechangecrud.create_for_resume(
            db=db,
            resume_id=resume_id,
            changed_at=changed_at,
        )

    async def _touch_resume(
        self,
        db: AsyncSession,
        resume: Resume,
    ) -> None:
        now = utc_now_naive()
        resume.updated_at = now

        await self._record_resume_change(
            db=db,
            resume_id=resume.id,
            changed_at=now,
        )

    async def _touch_all_applicant_resumes(
        self,
        db: AsyncSession,
        applicant_id: int,
    ) -> None:
        result = await db.execute(
            select(Resume).where(Resume.applicant_id == applicant_id)
        )

        resumes = list(result.scalars().all())

        if not resumes:
            return

        now = utc_now_naive()

        for resume in resumes:
            resume.updated_at = now

            await self._record_resume_change(
                db=db,
                resume_id=resume.id,
                changed_at=now,
            )

    # ---------- Профиль ----------

    async def get_profile(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> dict:
        applicant = await self._get_applicant_or_raise(db, user_id)

        applicant_with_details = await self._get_applicant_with_details_for_response(
            db=db,
            applicant_id=applicant.id,
        )

        return self._applicant_to_dict(applicant_with_details)

    async def update_profile(
        self,
        db: AsyncSession,
        user_id: int,
        update_data: ApplicantUpdate,
    ) -> dict:
        applicant = await self._get_applicant_or_raise(db, user_id)

        try:
            update_payload = update_data.model_dump(exclude_unset=True)

            if "phone" in update_payload:
                raw_phone = update_payload.get("phone")

                if raw_phone:
                    normalized_phone = (
                        str(raw_phone)
                        .strip()
                        .replace(" ", "")
                        .replace("-", "")
                        .replace("(", "")
                        .replace(")", "")
                    )

                    if normalized_phone != applicant.phone:
                        existing_phone = await db.execute(
                            select(Applicant.id).where(
                                Applicant.phone == normalized_phone,
                                Applicant.id != applicant.id,
                            )
                        )

                        if existing_phone.scalar_one_or_none():
                            raise HTTPException(
                                status_code=409,
                                detail="Телефон уже используется другим аккаунтом.",
                            )

                    update_payload["phone"] = normalized_phone
                else:
                    update_payload["phone"] = None

            city_was_changed = False

            if "city_id" in update_payload:
                city_id = update_payload.pop("city_id")
                city_was_changed = True

                if city_id is None:
                    applicant.city_id = None
                else:
                    city_result = await db.execute(
                        select(City.id).where(City.id == city_id)
                    )
                    existing_city_id = city_result.scalar_one_or_none()

                    if not existing_city_id:
                        raise HTTPException(
                            status_code=400,
                            detail="Город не найден.",
                        )

                    applicant.city_id = city_id

            for field, value in update_payload.items():
                setattr(applicant, field, value)

            profile_was_changed = bool(update_payload) or city_was_changed

            if profile_was_changed:
                await self._touch_all_applicant_resumes(db, applicant.id)

            await db.commit()

            updated_applicant = await self._get_applicant_with_details_for_response(
                db=db,
                applicant_id=applicant.id,
            )

            return self._applicant_to_dict(updated_applicant)

        except HTTPException:
            await db.rollback()
            raise

        except IntegrityError as e:
            await db.rollback()

            error_text = str(e.orig).lower()

            if "applicants_phone_key" in error_text or "key (phone)" in error_text:
                raise HTTPException(
                    status_code=409,
                    detail="Телефон уже используется другим аккаунтом.",
                )

            logger.error(f"DB integrity error in update_profile: {e}")

            raise HTTPException(
                status_code=400,
                detail="Некорректные данные профиля.",
            )

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in update_profile: {e}")

            raise HTTPException(
                status_code=500,
                detail="Ошибка базы данных.",
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error in update_profile: {e}", exc_info=True)

            raise HTTPException(
                status_code=500,
                detail="Внутренняя ошибка сервера.",
            )

    # ---------- Резюме ----------

    async def create_resume(
        self,
        db: AsyncSession,
        applicant_id: int,
        data: ResumeCreate,
    ) -> Resume:
        try:
            now = utc_now_naive()

            resume_dict = data.model_dump()
            resume_dict["applicant_id"] = applicant_id
            resume_dict["created_at"] = now
            resume_dict["updated_at"] = now

            resume = await self.resumecrud.create(db, resume_dict)

            await db.commit()
            await db.refresh(resume, ["profession", "skills", "work_experiences"])

            return resume

        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="Invalid profession_id or duplicate")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in create_resume: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error")

    async def get_resumes(
        self,
        db: AsyncSession,
        applicant_id: int,
        skip: int = 0,
        limit: int = 10,
    ) -> list[Resume]:
        return await self.resumecrud.get_by_applicant_with_details_paginated(
            db,
            applicant_id,
            skip,
            limit,
        )

    async def get_resume_detail(
        self,
        db: AsyncSession,
        resume_id: int,
        applicant_id: int,
    ) -> Resume:
        return await self._get_resume_or_raise(db, resume_id, applicant_id)

    async def get_resume_changes(
        self,
        db: AsyncSession,
        resume_id: int,
        applicant_id: int,
        skip: int = 0,
        limit: int = 20,
    ):
        await self._get_resume_or_raise(db, resume_id, applicant_id)

        return await self.resumechangecrud.get_by_resume(
            db=db,
            resume_id=resume_id,
            skip=skip,
            limit=limit,
        )

    async def update_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        applicant_id: int,
        data: ResumeUpdate,
    ) -> Resume:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)

        try:
            update_data = data.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                setattr(resume, field, value)

            if update_data:
                await self._touch_resume(db, resume)

            await db.commit()
            await db.refresh(resume, ["profession", "skills", "work_experiences"])

            return resume

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in update_resume: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error")

    async def delete_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        applicant_id: int,
    ) -> None:
        await self._get_resume_or_raise(db, resume_id, applicant_id)

        try:
            await self.resumecrud.delete(db, resume_id)
            await db.commit()

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in delete_resume: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error")

    # ---------- Навыки резюме ----------

    async def add_skill_to_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        applicant_id: int,
        skill_name: str,
    ) -> Resume:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)

        try:
            skill = await self.skillcrud.get_or_create(db, skill_name)
            existing_ids = {item.id for item in resume.skills}

            if skill.id not in existing_ids:
                resume.skills.append(skill)
                await self._touch_resume(db, resume)

                await db.commit()
                await db.refresh(resume, ["skills", "profession", "work_experiences"])

            return resume

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in add_skill_to_resume: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error")

    async def remove_skill_from_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        applicant_id: int,
        skill_id: int,
    ) -> Resume:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)

        try:
            skill = await self.skillcrud.get(db, skill_id)

            if skill and any(item.id == skill.id for item in resume.skills):
                resume.skills.remove(skill)
                await self._touch_resume(db, resume)

                await db.commit()
                await db.refresh(resume, ["skills", "profession", "work_experiences"])

            return resume

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in remove_skill_from_resume: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error")

    async def add_skills_batch(
        self,
        db: AsyncSession,
        resume_id: int,
        applicant_id: int,
        skill_names: list[str],
    ) -> Resume:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)

        try:
            skills_map = await self.skillcrud.get_or_create_many(db, skill_names)

            existing_ids = {skill.id for skill in resume.skills}
            to_add = [
                skill
                for skill in skills_map.values()
                if skill.id not in existing_ids
            ]

            if to_add:
                resume.skills.extend(to_add)
                await self._touch_resume(db, resume)

                await db.commit()
                await db.refresh(resume, ["skills", "profession", "work_experiences"])

            return resume

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in add_skills_batch: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error")

    # ---------- Опыт работы ----------

    async def add_work_experience(
        self,
        db: AsyncSession,
        resume_id: int,
        applicant_id: int,
        data: WorkExperienceCreate,
    ) -> WorkExperience:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)

        try:
            exp_dict = data.model_dump()
            exp_dict["resume_id"] = resume_id

            exp = await self.workexperiencecrud.create(db, exp_dict)

            await self._touch_resume(db, resume)

            await db.commit()
            await db.refresh(exp)

            return exp

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in add_work_experience: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error")

    async def update_work_experience(
        self,
        db: AsyncSession,
        exp_id: int,
        resume_id: int,
        applicant_id: int,
        data: WorkExperienceUpdate,
    ) -> WorkExperience:
        await self._get_work_exp_or_raise(db, exp_id, resume_id, applicant_id)
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)

        try:
            update_data = data.model_dump(exclude_unset=True)

            updated = await self.workexperiencecrud.update(
                db,
                update_data,
                exp_id,
            )

            if update_data:
                await self._touch_resume(db, resume)

            await db.commit()
            await db.refresh(updated)

            return updated

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in update_work_experience: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error")

    async def delete_work_experience(
        self,
        db: AsyncSession,
        exp_id: int,
        resume_id: int,
        applicant_id: int,
    ) -> None:
        await self._get_work_exp_or_raise(db, exp_id, resume_id, applicant_id)
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)

        try:
            await self.workexperiencecrud.delete(db, exp_id)
            await self._touch_resume(db, resume)

            await db.commit()

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in delete_work_experience: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error")

    # ---------- Образование ----------

    async def add_education(
        self,
        db: AsyncSession,
        user_id: int,
        data: EducationCreate,
    ) -> Education:
        applicant = await self._get_applicant_or_raise(db, user_id)

        try:
            institution = await self.educationalinstitutioncrud.get(db, data.institution_id)

            if not institution:
                raise HTTPException(status_code=400, detail="Учебное заведение не найдено")

            edu_dict = data.model_dump()
            edu_dict["applicant_id"] = applicant.id
            edu_dict["institution_id"] = institution.id

            edu = await self.educationcrud.create(db, edu_dict)

            await self._touch_all_applicant_resumes(db, applicant.id)

            await db.commit()
            await db.refresh(edu, ["institution"])

            return edu

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"IntegrityError in add_education: {e}")
            raise HTTPException(
                status_code=400,
                detail="Некорректные данные образования",
            )

        except HTTPException:
            await db.rollback()
            raise

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in add_education: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Внутренняя ошибка",
            )

    async def update_education(
        self,
        db: AsyncSession,
        edu_id: int,
        applicant_id: int,
        data: EducationUpdate,
    ) -> Education:
        edu = await self.educationcrud.get_with_institution(db, edu_id)

        if not edu or edu.applicant_id != applicant_id:
            raise EducationNotFoundError()

        try:
            was_changed = False

            if data.institution_id is not None:
                institution = await self.educationalinstitutioncrud.get(db, data.institution_id)

                if not institution:
                    raise HTTPException(status_code=400, detail="Учебное заведение не найдено")

                if edu.institution_id != institution.id:
                    edu.institution_id = institution.id
                    was_changed = True

            update_data = data.model_dump(
                exclude={"institution_id"},
                exclude_unset=True,
            )

            for field, value in update_data.items():
                if getattr(edu, field) != value:
                    setattr(edu, field, value)
                    was_changed = True

            if was_changed:
                await self._touch_all_applicant_resumes(db, applicant_id)

            await db.commit()
            await db.refresh(edu, ["institution"])

            return edu

        except HTTPException:
            await db.rollback()
            raise

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in update_education: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Внутренняя ошибка")

    async def delete_education(
        self,
        db: AsyncSession,
        edu_id: int,
        applicant_id: int,
    ) -> None:
        edu = await self.educationcrud.get(db, edu_id)

        if not edu or edu.applicant_id != applicant_id:
            raise EducationNotFoundError()

        try:
            await self.educationcrud.delete(db, edu_id)
            await self._touch_all_applicant_resumes(db, applicant_id)

            await db.commit()

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in delete_education: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error")

    # ---------- Избранные вакансии ----------

    async def _get_vacancy_for_favorite_or_raise(
        self,
        db: AsyncSession,
        vacancy_id: int,
    ) -> Vacancy:
        vacancy = await self.vacancycrud.get(db, vacancy_id)

        if not vacancy:
            raise HTTPException(
                status_code=404,
                detail="Вакансия не найдена",
            )

        return vacancy

    async def _get_favorite_pair_for_response(
        self,
        db: AsyncSession,
        resume_id: int,
        vacancy_id: int,
    ) -> tuple[FavoriteVacancy, Resume] | None:
        """
        Возвращает FavoriteVacancy + Resume со всеми связями,
        которые нужны для сериализации ответа.

        Это нужно, чтобы в async SQLAlchemy не было lazy loading ошибки:
        greenlet_spawn has not been called.
        """

        result = await db.execute(
            select(FavoriteVacancy, Resume)
            .join(FavoriteVacancy.resumes)
            .where(
                Resume.id == resume_id,
                FavoriteVacancy.vacancy_id == vacancy_id,
            )
            .options(
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.company),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.profession),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.employment_type),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.work_schedule),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.currency),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.experience),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.status),

                joinedload(FavoriteVacancy.vacancy)
                .joinedload(Vacancy.city)
                .joinedload(City.district)
                .joinedload(District.region),

                joinedload(FavoriteVacancy.vacancy)
                .joinedload(Vacancy.city)
                .joinedload(City.settlement_type),

                joinedload(FavoriteVacancy.vacancy).selectinload(Vacancy.skills),

                joinedload(Resume.profession),
            )
        )

        return result.unique().one_or_none()

    async def _get_first_favorite_pair_for_response(
        self,
        db: AsyncSession,
        applicant_id: int,
        vacancy_id: int,
    ) -> tuple[FavoriteVacancy, Resume] | None:
        """
        Возвращает первую пару FavoriteVacancy + Resume для applicant_id и vacancy_id.
        Используется, когда фронт проверяет состояние избранного без конкретного resume_id.
        """

        result = await db.execute(
            select(FavoriteVacancy, Resume)
            .join(FavoriteVacancy.resumes)
            .where(
                Resume.applicant_id == applicant_id,
                FavoriteVacancy.vacancy_id == vacancy_id,
            )
            .options(
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.company),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.profession),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.employment_type),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.work_schedule),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.currency),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.experience),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.status),

                joinedload(FavoriteVacancy.vacancy)
                .joinedload(Vacancy.city)
                .joinedload(City.district)
                .joinedload(District.region),

                joinedload(FavoriteVacancy.vacancy)
                .joinedload(Vacancy.city)
                .joinedload(City.settlement_type),

                joinedload(FavoriteVacancy.vacancy).selectinload(Vacancy.skills),

                joinedload(Resume.profession),
            )
            .limit(1)
        )

        return result.unique().one_or_none()

    async def _get_favorite_pairs_for_response(
        self,
        db: AsyncSession,
        applicant_id: int,
        skip: int = 0,
        limit: int = 10,
        resume_id: int | None = None,
    ) -> list[tuple[FavoriteVacancy, Resume]]:
        """
        Возвращает список избранных вакансий со всеми связями для сериализации.
        Используется вместо favoritevacancycrud.get_by_applicant(...),
        если тот CRUD не делает eager loading всех связей.
        """

        query = (
            select(FavoriteVacancy, Resume)
            .join(FavoriteVacancy.resumes)
            .where(Resume.applicant_id == applicant_id)
            .options(
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.company),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.profession),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.employment_type),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.work_schedule),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.currency),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.experience),
                joinedload(FavoriteVacancy.vacancy).joinedload(Vacancy.status),

                joinedload(FavoriteVacancy.vacancy)
                .joinedload(Vacancy.city)
                .joinedload(City.district)
                .joinedload(District.region),

                joinedload(FavoriteVacancy.vacancy)
                .joinedload(Vacancy.city)
                .joinedload(City.settlement_type),

                joinedload(FavoriteVacancy.vacancy).selectinload(Vacancy.skills),

                joinedload(Resume.profession),
            )
            .offset(skip)
            .limit(limit)
        )

        if resume_id is not None:
            query = query.where(Resume.id == resume_id)

        result = await db.execute(query)

        return list(result.unique().all())

    def _serialize_favorite_resume(
        self,
        resume: Resume,
    ) -> dict:
        profession_name = resume.profession.name if resume.profession else None

        return {
            "id": resume.id,
            "profession_id": resume.profession_id,
            "profession_name": profession_name,
            "title": profession_name or f"Резюме #{resume.id}",
        }

    def _serialize_favorite_vacancy_info(
        self,
        vacancy: Vacancy | None,
    ) -> dict | None:
        if not vacancy:
            return None

        city_full_name = None

        if vacancy.city:
            settlement_type = (
                vacancy.city.settlement_type.name
                if vacancy.city.settlement_type
                else ""
            )
            district = vacancy.city.district.name if vacancy.city.district else ""
            region = (
                vacancy.city.district.region.name
                if vacancy.city.district and vacancy.city.district.region
                else ""
            )

            city_title = f"{settlement_type} {vacancy.city.name}".strip()
            city_full_name = ", ".join(
                part for part in [city_title, district, region] if part
            )

        return {
            "id": vacancy.id,
            "title": vacancy.title,
            "description": vacancy.description,
            "salary_min": vacancy.salary_min,
            "salary_max": vacancy.salary_max,
            "company_id": vacancy.company_id,
            "company_name": vacancy.company.name if vacancy.company else None,
            "city_id": vacancy.city_id,
            "city_name": vacancy.city.name if vacancy.city else None,
            "city_full_name": city_full_name,
            "city": self._city_to_dict(vacancy.city) if vacancy.city else None,
            "profession_id": vacancy.profession_id,
            "profession_name": vacancy.profession.name if vacancy.profession else None,
            "employment_type_id": vacancy.employment_type_id,
            "employment_type_name": (
                vacancy.employment_type.name if vacancy.employment_type else None
            ),
            "work_schedule_id": vacancy.work_schedule_id,
            "work_schedule_name": (
                vacancy.work_schedule.name if vacancy.work_schedule else None
            ),
            "currency_id": vacancy.currency_id,
            "currency_name": vacancy.currency.name if vacancy.currency else None,
            "currency": vacancy.currency.name if vacancy.currency else None,
            "experience_id": vacancy.experience_id,
            "experience_name": vacancy.experience.name if vacancy.experience else None,
            "status_id": vacancy.status_id,
            "status_name": vacancy.status.name if vacancy.status else None,
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

    def _serialize_favorite_response(
        self,
        favorite: FavoriteVacancy,
        resume: Resume,
    ) -> dict:
        return {
            "favorite_id": favorite.id,
            "vacancy_id": favorite.vacancy_id,
            "resume_id": resume.id,
            "resume": self._serialize_favorite_resume(resume),
            "vacancy": self._serialize_favorite_vacancy_info(favorite.vacancy),
        }

    async def add_favorite_vacancy(
        self,
        db: AsyncSession,
        applicant_id: int,
        vacancy_id: int,
        resume_id: int,
    ) -> dict:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)
        await self._get_vacancy_for_favorite_or_raise(db, vacancy_id)

        try:
            favorite = await self.favoritevacancycrud.get_by_vacancy_id(
                db=db,
                vacancy_id=vacancy_id,
            )

            if not favorite:
                favorite = await self.favoritevacancycrud.create(
                    db=db,
                    vacancy_id=vacancy_id,
                )

            await self.favoritevacancycrud.link_resume(
                db=db,
                resume_id=resume.id,
                favorite_vacancy_id=favorite.id,
            )

            await db.commit()

            pair = await self._get_favorite_pair_for_response(
                db=db,
                resume_id=resume.id,
                vacancy_id=vacancy_id,
            )

            if not pair:
                raise HTTPException(
                    status_code=500,
                    detail="Не удалось получить избранную вакансию",
                )

            favorite, resume = pair

            return self._serialize_favorite_response(favorite, resume)

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error in add_favorite_vacancy: {e}", exc_info=True)

            raise HTTPException(
                status_code=400,
                detail="Не удалось добавить вакансию в избранное",
            )

        except HTTPException:
            await db.rollback()
            raise

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in add_favorite_vacancy: {e}", exc_info=True)

            raise HTTPException(
                status_code=500,
                detail="Ошибка базы данных",
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in add_favorite_vacancy: {e}", exc_info=True)

            raise HTTPException(
                status_code=500,
                detail="Внутренняя ошибка сервера",
            )

    async def remove_favorite_vacancy(
        self,
        db: AsyncSession,
        applicant_id: int,
        vacancy_id: int,
        resume_id: int,
    ) -> None:
        resume = await self._get_resume_or_raise(db, resume_id, applicant_id)

        try:
            pair = await self._get_favorite_pair_for_response(
                db=db,
                resume_id=resume.id,
                vacancy_id=vacancy_id,
            )

            if not pair:
                await db.commit()
                return

            favorite, _ = pair

            await self.favoritevacancycrud.unlink_resume(
                db=db,
                resume_id=resume.id,
                favorite_vacancy_id=favorite.id,
            )

            links_count = await self.favoritevacancycrud.count_links(
                db=db,
                favorite_vacancy_id=favorite.id,
            )

            if links_count == 0:
                await self.favoritevacancycrud.delete_favorite_record(
                    db=db,
                    favorite_vacancy_id=favorite.id,
                )

            await db.commit()

        except HTTPException:
            await db.rollback()
            raise

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in remove_favorite_vacancy: {e}", exc_info=True)

            raise HTTPException(
                status_code=500,
                detail="Ошибка базы данных",
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in remove_favorite_vacancy: {e}", exc_info=True)

            raise HTTPException(
                status_code=500,
                detail="Внутренняя ошибка сервера",
            )

    async def get_favorite_vacancies(
        self,
        db: AsyncSession,
        applicant_id: int,
        skip: int = 0,
        limit: int = 10,
        resume_id: int | None = None,
    ) -> list[dict]:
        if resume_id is not None:
            await self._get_resume_or_raise(db, resume_id, applicant_id)

        favorites = await self._get_favorite_pairs_for_response(
            db=db,
            applicant_id=applicant_id,
            skip=skip,
            limit=limit,
            resume_id=resume_id,
        )

        return [
            self._serialize_favorite_response(favorite, resume)
            for favorite, resume in favorites
        ]

    async def get_favorite_vacancy_state(
        self,
        db: AsyncSession,
        applicant_id: int,
        vacancy_id: int,
        resume_id: int | None = None,
    ) -> dict:
        await self._get_vacancy_for_favorite_or_raise(db, vacancy_id)

        if resume_id is not None:
            resume = await self._get_resume_or_raise(db, resume_id, applicant_id)

            pair = await self._get_favorite_pair_for_response(
                db=db,
                resume_id=resume.id,
                vacancy_id=vacancy_id,
            )
        else:
            pair = await self._get_first_favorite_pair_for_response(
                db=db,
                applicant_id=applicant_id,
                vacancy_id=vacancy_id,
            )

        if not pair:
            return {
                "vacancy_id": vacancy_id,
                "is_favorite": False,
                "favorite_id": None,
                "resume_id": None,
                "resume": None,
            }

        favorite, resume = pair

        return {
            "vacancy_id": vacancy_id,
            "is_favorite": True,
            "favorite_id": favorite.id,
            "resume_id": resume.id,
            "resume": self._serialize_favorite_resume(resume),
        }

    async def upload_photo(
        self,
        db: AsyncSession,
        user_id: int,
        file: UploadFile,
    ) -> dict:
        applicant = await self._get_applicant_or_raise(
            db=db,
            user_id=user_id,
        )

        old_photo_url = applicant.photo
        uploaded = None

        try:
            uploaded = await file_storage_service.upload_applicant_photo(
                applicant_id=applicant.id,
                file=file,
            )

            applicant.photo = uploaded.file_url

            await self._touch_all_applicant_resumes(
                db=db,
                applicant_id=applicant.id,
            )

            await db.commit()

            if old_photo_url and old_photo_url != uploaded.file_url:
                await file_storage_service.delete_file(old_photo_url)

            return await self.get_profile(
                db=db,
                user_id=user_id,
            )

        except (FileValidationError, FileStorageError) as e:
            await db.rollback()

            if uploaded:
                await file_storage_service.delete_file(uploaded.object_key)

            raise HTTPException(
                status_code=400,
                detail=str(e),
            )

        except HTTPException:
            await db.rollback()

            if uploaded:
                await file_storage_service.delete_file(uploaded.object_key)

            raise

        except Exception as e:
            await db.rollback()

            if uploaded:
                await file_storage_service.delete_file(uploaded.object_key)

            logger.error(f"Unexpected error in upload_photo: {e}", exc_info=True)

            raise HTTPException(
                status_code=500,
                detail="Внутренняя ошибка сервера",
            )

    async def delete_photo(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> dict:
        applicant = await self._get_applicant_or_raise(
            db=db,
            user_id=user_id,
        )

        old_photo_url = applicant.photo

        try:
            applicant.photo = None

            await self._touch_all_applicant_resumes(
                db=db,
                applicant_id=applicant.id,
            )

            await db.commit()

            if old_photo_url:
                await file_storage_service.delete_file(old_photo_url)

            return await self.get_profile(
                db=db,
                user_id=user_id,
            )

        except HTTPException:
            await db.rollback()
            raise

        except Exception as e:
            await db.rollback()

            logger.error(f"Unexpected error in delete_photo: {e}", exc_info=True)

            raise HTTPException(
                status_code=500,
                detail="Внутренняя ошибка сервера",
            )

applicant_service = ApplicantService()