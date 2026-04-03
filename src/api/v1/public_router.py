from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps.db_deps import get_db
from src.schemas.admin_schema import (
    CatalogItemResponse,
    CompanyPublicDetail,
    CompanyPublicListItem,
    ProfessionPublicListItem,
    VacancyPublicDetail,
)
from src.services.public_service import public_service

public_router = APIRouter(prefix="/public", tags=["Публичные данные"])


@public_router.get("/vacancies")
async def get_vacancies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    city_id: Optional[int] = Query(None),
    profession_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    employment_type_id: Optional[int] = Query(None),
    experience_id: Optional[int] = Query(None),
    work_schedule_id: Optional[int] = Query(None),
    salary_from: Optional[int] = Query(None, ge=0),
    salary_to: Optional[int] = Query(None, ge=0),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await public_service.get_vacancies(
        db=db,
        skip=skip,
        limit=limit,
        city_id=city_id,
        profession_id=profession_id,
        company_id=company_id,
        employment_type_id=employment_type_id,
        experience_id=experience_id,
        work_schedule_id=work_schedule_id,
        salary_from=salary_from,
        salary_to=salary_to,
        search=search,
    )


@public_router.get("/vacancies/{vacancy_id}", response_model=VacancyPublicDetail)
async def get_public_vacancy_detail(
    vacancy_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await public_service.get_vacancy_detail(db, vacancy_id)


@public_router.get("/catalogs/{catalog_name}", response_model=list[CatalogItemResponse])
async def get_public_catalog_items(
    catalog_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await public_service.get_catalog_items(db, catalog_name, skip, limit)


@public_router.get("/companies", response_model=list[CompanyPublicListItem], summary="Get public companies")
async def get_public_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    city_ids: Optional[str] = Query(None, description="Список id городов через запятую: 1,2,3"),
    has_vacancies_only: bool = Query(False),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await public_service.get_companies(
        db=db,
        skip=skip,
        limit=limit,
        city_ids=city_ids,
        has_vacancies_only=has_vacancies_only,
        search=search,
    )


@public_router.get("/companies/{company_id}", response_model=CompanyPublicDetail, summary="Get public company detail")
async def get_public_company_detail(
    company_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await public_service.get_company_detail(db, company_id)


@public_router.get("/professions", response_model=list[ProfessionPublicListItem], summary="Get public professions")
async def get_public_professions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await public_service.get_professions(
        db=db,
        skip=skip,
        limit=limit,
    )