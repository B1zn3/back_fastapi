from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps.db_deps import get_db
from src.schemas.admin_schema import CatalogItemResponse, VacancyPublicDetail, VacancyPublicListItem
from src.services.public_service import public_service

public_router = APIRouter(prefix="/public", tags=["Публичные вакансии"])


@public_router.get("/vacancies", response_model=list[VacancyPublicListItem])
async def get_public_vacancies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    city_id: Optional[int] = Query(None),
    profession_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await public_service.get_vacancies(
        db,
        skip=skip,
        limit=limit,
        city_id=city_id,
        profession_id=profession_id,
        company_id=company_id,
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
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await public_service.get_catalog_items(db, catalog_name, skip, limit)