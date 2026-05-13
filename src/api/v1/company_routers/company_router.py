from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps.db_deps import get_db
from src.deps.role_checker import require_role
from src.models.model import Company, User
from src.schemas.application_schema import ApplicationResponse, ApplicationUpdate
from src.schemas.company_schemas.candidate_resume_schema import (
    CandidateResumeListItem,
    CandidateResumeListResponse,
)
from src.schemas.company_schemas.company_schema import CompanyResponse, CompanyUpdate
from src.schemas.company_schemas.employer_application_schema import (
    EmployerApplicationListResponse,
    EmployerApplicationResponse,
    EmployerApplicationStatusUpdate,
    EmployerApplicationSuspicionInfo,
)
from src.schemas.company_schemas.vacancy_schema import (
    VacancyCreate,
    VacancyResponse,
    VacancyUpdate,
)
from src.schemas.skill_schema import SkillCreate
from src.services.CompanyService.company_service import company_service


company_router = APIRouter(prefix="/companies", tags=["Компании"])


async def get_current_company(
    current_user: User = Depends(require_role("company")),
    db: AsyncSession = Depends(get_db),
) -> Company:
    company = await company_service.get_company_by_user_id_with_details(
        db,
        current_user.id,
    )

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль компании не найден",
        )

    return company


# ---------- Профиль компании ----------

@company_router.get("/me", response_model=CompanyResponse)
async def get_my_company_profile(
    company: Company = Depends(get_current_company),
):
    return await company_service.get_profile(company)


@company_router.put("/me", response_model=CompanyResponse)
async def update_my_company_profile(
    update_data: CompanyUpdate,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.update_profile(
        db,
        company,
        update_data,
    )


# ---------- Страница откликов работодателя ----------

@company_router.get(
    "/me/applications",
    response_model=EmployerApplicationListResponse,
)
async def get_company_applications_page(
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    vacancy_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    city_id: Optional[int] = Query(None),
    profession_id: Optional[int] = Query(None),
    skill_id: Optional[int] = Query(None),
    skill_ids: Optional[str] = Query(None),
    has_cover_letter: Optional[bool] = Query(None),
    suspicious_only: Optional[bool] = Query(None),
    score_from: Optional[int] = Query(None, ge=0, le=100),
    score_to: Optional[int] = Query(None, ge=0, le=100),
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None),
    period_days: int = Query(30, ge=1, le=365),
    sort_by: str = Query(
        "smart",
        description="smart | new | old | suspicious",
    ),
):
    return await company_service.get_company_applications_page(
        db=db,
        company_id=company.id,
        skip=skip,
        limit=limit,
        search=search,
        vacancy_id=vacancy_id,
        status_filter=status_filter,
        city_id=city_id,
        profession_id=profession_id,
        skill_id=skill_id,
        skill_ids=skill_ids,
        has_cover_letter=has_cover_letter,
        suspicious_only=suspicious_only,
        score_from=score_from,
        score_to=score_to,
        created_from=created_from,
        created_to=created_to,
        period_days=period_days,
        sort_by=sort_by,
    )


@company_router.get(
    "/me/applications/{application_id}",
    response_model=EmployerApplicationResponse,
)
async def get_company_application_detail_by_id(
    application_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
    period_days: int = Query(30, ge=1, le=365),
):
    return await company_service.get_company_application_detail_by_id(
        db=db,
        application_id=application_id,
        company_id=company.id,
        period_days=period_days,
    )


@company_router.get(
    "/me/applications/{application_id}/suspicion",
    response_model=EmployerApplicationSuspicionInfo,
)
async def get_company_application_suspicion(
    application_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
    period_days: int = Query(30, ge=1, le=365),
):
    return await company_service.get_company_application_suspicion_by_id(
        db=db,
        application_id=application_id,
        company_id=company.id,
        period_days=period_days,
    )


@company_router.patch(
    "/me/applications/{application_id}/status",
    response_model=EmployerApplicationResponse,
)
async def update_company_application_status_by_id(
    application_id: int,
    status_data: EmployerApplicationStatusUpdate,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
    period_days: int = Query(30, ge=1, le=365),
):
    return await company_service.update_company_application_status_by_id(
        db=db,
        application_id=application_id,
        company_id=company.id,
        status_data=status_data,
        period_days=period_days,
    )


# ---------- Вакансии компании ----------

@company_router.post(
    "/me/vacancies",
    response_model=VacancyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vacancy(
    vacancy_data: VacancyCreate,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.create_vacancy(
        db=db,
        company_id=company.id,
        vacancy_data=vacancy_data,
    )


@company_router.get("/me/vacancies", response_model=list[VacancyResponse])
async def list_my_vacancies(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.get_vacancies(
        db=db,
        company_id=company.id,
        skip=skip,
        limit=limit,
    )


@company_router.get("/me/vacancies/{vacancy_id}", response_model=VacancyResponse)
async def get_vacancy(
    vacancy_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.get_vacancy_detail(
        db=db,
        vacancy_id=vacancy_id,
        company_id=company.id,
    )


@company_router.put("/me/vacancies/{vacancy_id}", response_model=VacancyResponse)
async def update_vacancy(
    vacancy_id: int,
    vacancy_data: VacancyUpdate,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.update_vacancy(
        db=db,
        vacancy_id=vacancy_id,
        company_id=company.id,
        vacancy_data=vacancy_data,
    )


@company_router.delete(
    "/me/vacancies/{vacancy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_vacancy(
    vacancy_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    await company_service.delete_vacancy(
        db=db,
        vacancy_id=vacancy_id,
        company_id=company.id,
    )


# ---------- Навыки вакансии ----------

@company_router.post(
    "/me/vacancies/{vacancy_id}/skills",
    response_model=VacancyResponse,
)
async def add_skill_to_vacancy(
    vacancy_id: int,
    skill_data: SkillCreate,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.add_skill_to_vacancy(
        db=db,
        vacancy_id=vacancy_id,
        company_id=company.id,
        skill_name=skill_data.name,
    )


@company_router.delete(
    "/me/vacancies/{vacancy_id}/skills/{skill_id}",
    response_model=VacancyResponse,
)
async def remove_skill_from_vacancy(
    vacancy_id: int,
    skill_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.remove_skill_from_vacancy(
        db=db,
        vacancy_id=vacancy_id,
        company_id=company.id,
        skill_id=skill_id,
    )


# ---------- Старые эндпоинты откликов по конкретной вакансии ----------

@company_router.get(
    "/me/vacancies/{vacancy_id}/applications",
    response_model=list[ApplicationResponse],
)
async def get_vacancy_applications(
    vacancy_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    return await company_service.get_vacancy_applications(
        db=db,
        vacancy_id=vacancy_id,
        company_id=company.id,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
    )


@company_router.get(
    "/me/vacancies/{vacancy_id}/applications/{resume_id}",
    response_model=ApplicationResponse,
)
async def get_application_detail(
    vacancy_id: int,
    resume_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.get_application_detail(
        db=db,
        vacancy_id=vacancy_id,
        resume_id=resume_id,
        company_id=company.id,
    )


@company_router.patch(
    "/me/vacancies/{vacancy_id}/applications/{resume_id}",
    response_model=ApplicationResponse,
)
async def update_application_status(
    vacancy_id: int,
    resume_id: int,
    status_data: ApplicationUpdate,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.update_application_status(
        db=db,
        vacancy_id=vacancy_id,
        resume_id=resume_id,
        company_id=company.id,
        status_data=status_data,
    )


# ---------- Каталог резюме для компании ----------

@company_router.get("/resumes", response_model=CandidateResumeListResponse)
async def get_candidate_resumes(
    skip: int = Query(0, ge=0),
    limit: int = Query(12, ge=1, le=100),
    search: Optional[str] = Query(None),
    city_id: Optional[int] = Query(None),
    profession_id: Optional[int] = Query(None),
    skill_id: Optional[int] = Query(None),
    skill_ids: Optional[str] = Query(None),
    experience_from: Optional[float] = Query(None, ge=0),
    experience_to: Optional[float] = Query(None, ge=0),
    has_education: Optional[bool] = Query(None),
    education_institution_id: Optional[int] = Query(None),
    age_from: Optional[int] = Query(None, ge=0),
    age_to: Optional[int] = Query(None, ge=0),
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.get_candidate_resumes(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        city_id=city_id,
        profession_id=profession_id,
        skill_id=skill_id,
        skill_ids=skill_ids,
        experience_from=experience_from,
        experience_to=experience_to,
        has_education=has_education,
        education_institution_id=education_institution_id,
        age_from=age_from,
        age_to=age_to,
    )


@company_router.get("/resumes/{resume_id}", response_model=CandidateResumeListItem)
async def get_candidate_resume_detail(
    resume_id: int,
    company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.get_candidate_resume_detail(
        db=db,
        resume_id=resume_id,
    )