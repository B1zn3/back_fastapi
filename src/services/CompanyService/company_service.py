# src/services/company_service.py
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException, status
import logging

from src.cruds.company_cruds.company_crud import companycrud
from src.cruds.company_cruds.vacancy_crud import vacancycrud
from src.cruds.profession_crud import professioncrud
from src.cruds.city_crud import citycrud
from src.cruds.currency_crud import currencycrud
from src.cruds.experience_crud import experiencecrud
from src.cruds.company_cruds.employment_type_crud import employmenttypecrud
from src.cruds.company_cruds.work_schedule_crud import workschedulecrud
from src.cruds.skill_crud import skillcrud
from src.cruds.application_crud import applicationcrud
from src.schemas.company_schemas.company_schema import CompanyUpdate
from src.schemas.company_schemas.vacancy_schema import VacancyCreate, VacancyUpdate
from src.schemas.application_schema import ApplicationUpdate
from src.models.model import Company, Vacancy, Application

logger = logging.getLogger(__name__)

class CompanyService:
    def __init__(self):
        self.companycrud = companycrud
        self.vacancycrud = vacancycrud
        self.professioncrud = professioncrud
        self.citycrud = citycrud
        self.currencycrud = currencycrud
        self.experiencecrud = experiencecrud
        self.employmenttypecrud = employmenttypecrud
        self.workschedulecrud = workschedulecrud
        self.skillcrud = skillcrud
        self.applicationcrud = applicationcrud

    # ---------- Вспомогательные методы ----------
    async def _get_vacancy_or_404(self, db: AsyncSession, vacancy_id: int, company_id: int) -> Vacancy:
        """Возвращает вакансию, если она принадлежит компании, иначе 404."""
        vacancy = await self.vacancycrud.get(db, vacancy_id)
        if not vacancy or vacancy.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вакансия не найдена"
            )
        return vacancy

    async def _get_application_or_404(
        self, db: AsyncSession, vacancy_id: int, resume_id: int, company_id: int
    ) -> Application:
        """Возвращает отклик, если вакансия принадлежит компании, иначе 404."""
        # Сначала проверим вакансию
        await self._get_vacancy_or_404(db, vacancy_id, company_id)
        application = await self.applicationcrud.get_by_vacancy_and_resume(db, vacancy_id, resume_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Отклик не найден"
            )
        return application

    async def _validate_foreign_keys(self, db: AsyncSession, data: dict):
        """Проверяет существование связанных сущностей."""
        checks = {
            "profession_id": self.professioncrud.get,
            "city_id": self.citycrud.get,
            "currency_id": self.currencycrud.get,
            "experience_id": self.experiencecrud.get,
            "employment_type_id": self.employmenttypecrud.get,
            "work_schedule_id": self.workschedulecrud.get,
        }
        for field, crud_method in checks.items():
            value = data.get(field)
            if value and not await crud_method(db, value):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field} с id {value} не существует"
                )

    # ---------- Профиль компании ----------
    async def get_profile(self, company: Company) -> Company:
        """Возвращает профиль компании (можно расширить статистикой)."""
        return company

    async def update_profile(
        self, db: AsyncSession, company: Company, update_data: CompanyUpdate
    ) -> Company:
        """Обновляет профиль компании."""
        try:
            update_dict = update_data.model_dump(exclude_unset=True)
            # Здесь можно добавить дополнительную валидацию (например, уникальность названия)
            updated = await self.companycrud.update(db, update_dict, company.id)
            await db.commit()
            await db.refresh(updated)
            return updated
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error in update_profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Название компании уже используется или некорректные данные"
            )
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in update_profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных"
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error in update_profile: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Внутренняя ошибка сервера"
            )

    # ---------- Вакансии ----------
    async def create_vacancy(
        self, db: AsyncSession, company_id: int, vacancy_data: VacancyCreate
    ) -> Vacancy:
        try:
            vacancy_dict = vacancy_data.model_dump()
            
            # Добавляем служебные поля
            vacancy_dict["company_id"] = company_id
            vacancy_dict["created_at"] = datetime.utcnow()
            vacancy_dict["updated_at"] = datetime.utcnow()
            
            if "status_id" not in vacancy_dict or not vacancy_dict["status_id"]:
                vacancy_dict["status_id"] = 1
            
            vacancy = await self.vacancycrud.create(db, vacancy_dict)
            await db.commit()
            
            # ВАЖНО: возвращаем с загруженными связями
            return await self.vacancycrud.get(db, vacancy.id)
            
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка целостности данных: {str(e)}"
            )

    async def get_vacancies(
        self, db: AsyncSession, company_id: int, skip: int = 0, limit: int = 10
    ) -> List[Vacancy]:
        """Возвращает список вакансий компании с пагинацией."""
        try:
            return await self.vacancycrud.get_by_company_with_details(
                db, company_id, skip=skip, limit=limit
            )
        except SQLAlchemyError as e:
            logger.error(f"DB error in get_vacancies: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных"
            )

    async def get_vacancy_detail(
        self, db: AsyncSession, vacancy_id: int, company_id: int
    ) -> Vacancy:
        """Возвращает детальную информацию о вакансии."""
        try:
            vacancy = await self.vacancycrud.get_with_details(db, vacancy_id)
            if not vacancy or vacancy.company_id != company_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Вакансия не найдена"
                )
            return vacancy
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"DB error in get_vacancy_detail: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных"
            )

    async def update_vacancy(
        self,
        db: AsyncSession,
        vacancy_id: int,
        company_id: int,
        vacancy_data: VacancyUpdate
    ) -> Vacancy:
        """Обновляет вакансию."""
        try:
            # Проверяем, что вакансия существует и принадлежит компании
            vacancy = await self._get_vacancy_or_404(db, vacancy_id, company_id)
            
            # Получаем только те поля, которые прислал клиент
            update_dict = vacancy_data.model_dump(exclude_unset=True)
            
            if update_dict:
                # Применяем изменения
                for key, value in update_dict.items():
                    setattr(vacancy, key, value)
                
                # Обновляем дату
                vacancy.updated_at = datetime.utcnow()
                
                await db.commit()
                await db.refresh(vacancy)
            
            # Возвращаем с деталями
            return await self.vacancycrud.get_with_details(db, vacancy_id)
            
        except HTTPException:
            raise
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error in update_vacancy: {e}")
            
            # Человекочитаемая ошибка
            error_msg = str(e)
            if "profession_id" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Профессия с ID {update_dict.get('profession_id')} не существует"
                )
            elif "city_id" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Город с ID {update_dict.get('city_id')} не существует"
                )
            elif "currency_id" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Валюта с ID {update_dict.get('currency_id')} не существует"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ошибка целостности данных. Проверьте ID справочников."
                )
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in update_vacancy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных"
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error in update_vacancy: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Внутренняя ошибка сервера"
            )

    async def delete_vacancy(self, db: AsyncSession, vacancy_id: int, company_id: int):
        """Удаляет вакансию."""
        try:
            await self._get_vacancy_or_404(db, vacancy_id, company_id)
            await self.vacancycrud.delete(db, vacancy_id)
            await db.commit()
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in delete_vacancy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных"
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error in delete_vacancy: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Внутренняя ошибка сервера"
            )

    # ---------- Навыки вакансии ----------
    async def add_skill_to_vacancy(
        self, db: AsyncSession, vacancy_id: int, company_id: int, skill_name: str
    ) -> Vacancy:
        """Добавляет навык к вакансии."""
        try:
            vacancy = await self._get_vacancy_or_404(db, vacancy_id, company_id)
            skill = await self.skillcrud.get_or_create(db, skill_name)
            if skill not in vacancy.skills:
                vacancy.skills.append(skill)
                await db.commit()
                await db.refresh(vacancy, ["skills"])
            return vacancy
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in add_skill_to_vacancy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных"
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error in add_skill_to_vacancy: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Внутренняя ошибка сервера"
            )

    async def remove_skill_from_vacancy(
        self, db: AsyncSession, vacancy_id: int, company_id: int, skill_id: int
    ) -> Vacancy:
        """Удаляет навык из вакансии."""
        try:
            vacancy = await self._get_vacancy_or_404(db, vacancy_id, company_id)
            skill = await self.skillcrud.get(db, skill_id)
            if skill and skill in vacancy.skills:
                vacancy.skills.remove(skill)
                await db.commit()
                await db.refresh(vacancy, ["skills"])
            return vacancy
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in remove_skill_from_vacancy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных"
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error in remove_skill_from_vacancy: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Внутренняя ошибка сервера"
            )

    # ---------- Отклики на вакансии ----------
    async def get_vacancy_applications(
        self,
        db: AsyncSession,
        vacancy_id: int,
        company_id: int,
        skip: int = 0,
        limit: int = 10,
        status: Optional[str] = None
    ) -> List[Application]:
        """Возвращает отклики на вакансию с фильтрацией и пагинацией."""
        try:
            # Проверяем принадлежность вакансии
            await self._get_vacancy_or_404(db, vacancy_id, company_id)
            return await self.applicationcrud.get_by_vacancy_with_details(
                db, vacancy_id, skip=skip, limit=limit, status=status
            )
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"DB error in get_vacancy_applications: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных"
            )
        except Exception as e:
            logger.error(f"Unexpected error in get_vacancy_applications: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Внутренняя ошибка сервера"
            )

    async def update_application_status(
        self,
        db: AsyncSession,
        vacancy_id: int,
        resume_id: int,
        company_id: int,
        status_data: ApplicationUpdate
    ) -> Application:
        """Обновляет статус отклика."""
        try:
            application = await self._get_application_or_404(db, vacancy_id, resume_id, company_id)
            application.status = status_data.status
            await db.commit()
            return application
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in update_application_status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных"
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error in update_application_status: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Внутренняя ошибка сервера"
            )

# Создаём единственный экземпляр сервиса
company_service = CompanyService()