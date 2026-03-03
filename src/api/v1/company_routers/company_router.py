from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.deps.pagination import pagination_params
from src.deps.db_deps import get_db
from src.deps.role_checker import require_role
from src.models.model import User
from src.services.CompanyService.company_service import company_service
from src.schemas.company_schemas.company_schema import CompanyUpdate, CompanyResponse
from src.schemas.company_schemas.vacancy_schema import (
    VacancyCreate, VacancyUpdate, VacancyResponse
)
from src.schemas.skill_schema import SkillCreate
from src.schemas.application_schema import ApplicationUpdate, ApplicationResponse
from src.models.model import Company

company_router = APIRouter(prefix="/companies", tags=["Компании"])


async def get_current_company(
    current_user: User = Depends(require_role("company")),
    db: AsyncSession = Depends(get_db)
) -> Company:
    """Возвращает профиль компании текущего пользователя с предзагруженными вакансиями."""
    company = await company_service.companycrud.get_by_user_id_with_details(db, current_user.id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль компании не найден"
        )
    return company


# ---------- Профиль ----------
@company_router.get("/me", response_model=CompanyResponse)
async def get_my_company_profile(
    company: Company = Depends(get_current_company)
):
    """Получить профиль текущей компании."""
    return await company_service.get_profile(company)

@company_router.put("/me", response_model=CompanyResponse)
async def update_my_company_profile(
    update_data: CompanyUpdate,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    """Обновить профиль компании."""
    return await company_service.update_profile(db, company, update_data)

# ---------- Вакансии ----------
@company_router.post("/me/vacancies", response_model=VacancyResponse, status_code=201)
async def create_vacancy(
    vacancy_data: VacancyCreate,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    """Создать новую вакансию."""
    return await company_service.create_vacancy(db, company.id, vacancy_data)

@company_router.get("/me/vacancies", response_model=list[VacancyResponse])
async def list_my_vacancies(
    pagination: dict = Depends(pagination_params),
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    """Список вакансий компании с пагинацией."""
    return await company_service.get_vacancies(
        db, company.id, skip=pagination["skip"], limit=pagination["limit"]
    )

@company_router.get("/me/vacancies/{vacancy_id}", response_model=VacancyResponse)
async def get_vacancy(
    vacancy_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    """Детальная информация о вакансии."""
    return await company_service.get_vacancy_detail(db, vacancy_id, company.id)

@company_router.put("/me/vacancies/{vacancy_id}", response_model=VacancyResponse)
async def update_vacancy(
    vacancy_id: int,
    vacancy_data: VacancyUpdate,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    """Обновить вакансию."""
    return await company_service.update_vacancy(db, vacancy_id, company.id, vacancy_data)

@company_router.delete("/me/vacancies/{vacancy_id}", status_code=204)
async def delete_vacancy(
    vacancy_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    """Удалить вакансию."""
    await company_service.delete_vacancy(db, vacancy_id, company.id)

# ---------- Навыки вакансии ----------
@company_router.post("/me/vacancies/{vacancy_id}/skills", response_model=VacancyResponse)
async def add_skill_to_vacancy(
    vacancy_id: int,
    skill_data: SkillCreate,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    """Добавить навык к вакансии."""
    return await company_service.add_skill_to_vacancy(
        db, vacancy_id, company.id, skill_data.name
    )

@company_router.delete("/me/vacancies/{vacancy_id}/skills/{skill_id}", response_model=VacancyResponse)
async def remove_skill_from_vacancy(
    vacancy_id: int,
    skill_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    """Удалить навык из вакансии."""
    return await company_service.remove_skill_from_vacancy(
        db, vacancy_id, company.id, skill_id
    )

# ---------- Отклики на вакансии ----------
@company_router.get("/me/vacancies/{vacancy_id}/applications", response_model=list[ApplicationResponse])
async def get_vacancy_applications(
    vacancy_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Сколько пропустить"),
    limit: int = Query(10, ge=1, le=100, description="Сколько вернуть"),
    status: Optional[str] = Query(None, description="Фильтр по статусу отклика")
):
    """Получить все отклики на вакансию (с пагинацией и фильтром)."""
    return await company_service.get_vacancy_applications(
        db, vacancy_id, company.id, skip=skip, limit=limit, status=status
    )

@company_router.patch("/me/vacancies/{vacancy_id}/applications/{resume_id}", response_model=ApplicationResponse)
async def update_application_status(
    vacancy_id: int,
    resume_id: int,
    status_data: ApplicationUpdate,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    """Изменить статус отклика."""
    return await company_service.update_application_status(
        db, vacancy_id, resume_id, company.id, status_data
    )