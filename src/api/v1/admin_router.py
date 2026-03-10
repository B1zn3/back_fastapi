from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps.db_deps import get_db
from src.deps.role_checker import require_role
from src.models.model import User
from src.schemas.admin_schema import (
    CatalogItemCreate,
    CatalogItemResponse,
    CatalogItemUpdate,
    UserAdminResponse,
    UserStatusUpdate,
    VacancyModerationUpdate,
)
from src.schemas.applicant_schemas.applicant_schema import ApplicantResponse
from src.schemas.application_schema import ApplicationResponse
from src.schemas.company_schemas.company_schema import CompanyResponse
from src.schemas.company_schemas.vacancy_schema import VacancyResponse
from src.services.admin_service import admin_service


admin_router = APIRouter(prefix="/admin", tags=["Администрирование"])


@admin_router.get("/catalogs/{catalog_name}", response_model=list[CatalogItemResponse])
async def list_catalog_items(
    catalog_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_catalog_items(db, catalog_name, skip, limit)


@admin_router.post("/catalogs/{catalog_name}", response_model=CatalogItemResponse, status_code=status.HTTP_201_CREATED)
async def create_catalog_item(
    catalog_name: str,
    payload: CatalogItemCreate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.create_catalog_item(db, catalog_name, payload.name)


@admin_router.put("/catalogs/{catalog_name}/{item_id}", response_model=CatalogItemResponse)
async def update_catalog_item(
    catalog_name: str,
    item_id: int,
    payload: CatalogItemUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.update_catalog_item(db, catalog_name, item_id, payload.name)


@admin_router.delete("/catalogs/{catalog_name}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalog_item(
    catalog_name: str,
    item_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_catalog_item(db, catalog_name, item_id)


@admin_router.get("/users", response_model=list[UserAdminResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    users = await admin_service.list_users(db, skip, limit, role=role, is_active=is_active, search=search)
    return [
        UserAdminResponse(
            id=user.id,
            email=user.email,
            role=user.role.name if user.role else "unknown",
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            company_id=user.company_id,
            applicant_id=user.applicant_id,
        )
        for user in users
    ]


@admin_router.patch("/users/{user_id}/status", response_model=UserAdminResponse)
async def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await admin_service.update_user_status(db, user_id, payload.is_active)
    return UserAdminResponse(
        id=user.id,
        email=user.email,
        role=user.role.name if user.role else "unknown",
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        company_id=user.company_id,
        applicant_id=user.applicant_id,
    )


@admin_router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_companies(db, skip, limit, search)


@admin_router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_company(db, company_id)


@admin_router.get("/applicants", response_model=list[ApplicantResponse])
async def list_applicants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_applicants(db, skip, limit)


@admin_router.delete("/applicants/{applicant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_applicant(
    applicant_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_applicant(db, applicant_id)


@admin_router.get("/vacancies", response_model=list[VacancyResponse])
async def list_vacancies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    status_id: Optional[int] = Query(None),
    city_id: Optional[int] = Query(None),
    profession_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_vacancies(
        db,
        skip,
        limit,
        search=search,
        status_id=status_id,
        city_id=city_id,
        profession_id=profession_id,
        company_id=company_id,
    )


@admin_router.get("/vacancies/{vacancy_id}", response_model=VacancyResponse)
async def get_vacancy(
    vacancy_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_vacancy(db, vacancy_id)


@admin_router.patch("/vacancies/{vacancy_id}/status", response_model=VacancyResponse)
async def update_vacancy_status(
    vacancy_id: int,
    payload: VacancyModerationUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.update_vacancy_status(db, vacancy_id, payload.status_id)


@admin_router.delete("/vacancies/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vacancy(
    vacancy_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_vacancy(db, vacancy_id)


@admin_router.get("/applications", response_model=list[ApplicationResponse])
async def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status_filter: Optional[str] = Query(None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_applications(db, skip, limit, status_filter)
