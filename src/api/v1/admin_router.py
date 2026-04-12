from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps.db_deps import get_db
from src.deps.role_checker import require_role
from src.models.model import Applicant, Application, Company, Resume, User, Vacancy
from src.schemas.admin_schema import (
    AdminEntityStatusUpdate,
    ApplicantAdminDetailResponse,
    ApplicantAdminListItem,
    ApplicantEducationAdminItem,
    ApplicantResumeAdminItem,
    ApplicationAdminDetailResponse,
    ApplicationAdminListItem,
    ApplicationAdminUpdate,
    CatalogItemCreate,
    CatalogItemResponse,
    CatalogItemUpdate,
    CompanyAdminDetailResponse,
    CompanyAdminListItem,
    DashboardRecentApplicationItem,
    DashboardRecentUserItem,
    DashboardRecentVacancyItem,
    DashboardResponse,
    UserAdminResponse,
    UserDetailAdminResponse,
    UserRoleUpdate,
    UserStatusUpdate,
    VacancyBulkStatusUpdate,
    VacancyModerationUpdate,
)
from src.schemas.company_schemas.vacancy_schema import VacancyResponse
from src.services.admin_service import admin_service


admin_router = APIRouter(prefix="/admin", tags=["Администрирование"])


def map_user(user: User) -> UserAdminResponse:
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


def map_user_detail(user: User) -> UserDetailAdminResponse:
    applicant_name = None
    resumes_count = 0
    applications_count = 0
    vacancies_count = 0

    if user.applicant:
        parts = [user.applicant.last_name, user.applicant.first_name, user.applicant.middle_name]
        applicant_name = " ".join(part for part in parts if part) or f"Соискатель #{user.applicant.id}"
        resumes_count = len(user.applicant.resumes or [])
        applications_count = sum(len(resume.applications or []) for resume in user.applicant.resumes or [])

    if user.company:
        vacancies_count = len(user.company.vacancies or [])

    return UserDetailAdminResponse(
        **map_user(user).model_dump(),
        company_name=user.company.name if user.company else None,
        applicant_full_name=applicant_name,
        vacancies_count=vacancies_count,
        resumes_count=resumes_count,
        applications_count=applications_count,
    )


def map_company_list(company: Company) -> CompanyAdminListItem:
    return CompanyAdminListItem(
        id=company.id,
        name=company.name,
        website=company.website,
        company_type_name=company.company_type.name if company.company_type else None,
        cities=[city.name for city in company.cities or []],
        vacancies_count=len(company.vacancies or []),
        user_id=company.user.id if company.user else None,
        user_email=company.user.email if company.user else None,
        is_active=company.user.is_active if company.user else True,
    )


def map_company_detail(company: Company) -> CompanyAdminDetailResponse:
    return CompanyAdminDetailResponse(
        **map_company_list(company).model_dump(),
        description=company.description,
        logo=company.logo,
        founded_year=company.founded_year,
        employee_count=company.employee_count,
        vacancy_ids=[vacancy.id for vacancy in company.vacancies or []],
    )


def map_applicant_resume(resume: Resume) -> ApplicantResumeAdminItem:
    return ApplicantResumeAdminItem(
        id=resume.id,
        profession_name=resume.profession.name if resume.profession else None,
        skills=[skill.name for skill in resume.skills or []],
        work_experiences_count=len(resume.work_experiences or []),
        applications_count=len(resume.applications or []),
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )


def map_applicant_list(applicant: Applicant) -> ApplicantAdminListItem:
    full_name = " ".join(
        part for part in [applicant.last_name, applicant.first_name, applicant.middle_name] if part
    ) or f"Соискатель #{applicant.id}"

    return ApplicantAdminListItem(
        id=applicant.id,
        full_name=full_name,
        email=applicant.user.email if applicant.user else None,
        phone=applicant.phone,
        city_name=applicant.city.name if applicant.city else None,
        resumes_count=len(applicant.resumes or []),
        educations_count=len(applicant.educations or []),
        is_active=applicant.user.is_active if applicant.user else True,
    )


def map_applicant_detail(applicant: Applicant) -> ApplicantAdminDetailResponse:
    return ApplicantAdminDetailResponse(
        **map_applicant_list(applicant).model_dump(),
        birth_date=applicant.birth_date,
        gender=applicant.gender,
        photo=applicant.photo,
        resumes=[map_applicant_resume(resume) for resume in applicant.resumes or []],
        educations=[
            ApplicantEducationAdminItem(
                id=education.id,
                institution_name=education.institution.name if education.institution else None,
                start_date=education.start_date,
                end_date=education.end_date,
            )
            for education in applicant.educations or []
        ],
        applications_count=sum(len(resume.applications or []) for resume in applicant.resumes or []),
    )


def map_application(application: Application) -> ApplicationAdminListItem:
    applicant = application.resume.applicant if application.resume else None
    applicant_name = " ".join(
        part for part in [getattr(applicant, "last_name", None), getattr(applicant, "first_name", None), getattr(applicant, "middle_name", None)] if part
    ) if applicant else None

    return ApplicationAdminListItem(
        vacancy_id=application.vacancy_id,
        resume_id=application.resume_id,
        status=application.status,
        created_at=getattr(application, "created_at", None),
        updated_at=getattr(application, "updated_at", None),
        vacancy_title=application.vacancy.title if application.vacancy else None,
        company_name=application.vacancy.company.name if application.vacancy and application.vacancy.company else None,
        applicant_name=applicant_name or (f"Соискатель #{applicant.id}" if applicant else None),
        resume_profession=application.resume.profession.name if application.resume and application.resume.profession else None,
    )


def map_application_detail(application: Application) -> ApplicationAdminDetailResponse:
    base = map_application(application)
    return ApplicationAdminDetailResponse(
        **base.model_dump(),
        city_name=application.vacancy.city.name if application.vacancy and application.vacancy.city else None,
        salary_min=application.vacancy.salary_min if application.vacancy else None,
        salary_max=application.vacancy.salary_max if application.vacancy else None,
    )


@admin_router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    data = await admin_service.get_dashboard(db)
    return DashboardResponse(
        users_total=data["users_total"],
        users_active=data["users_active"],
        companies_total=data["companies_total"],
        applicants_total=data["applicants_total"],
        vacancies_total=data["vacancies_total"],
        applications_total=data["applications_total"],
        vacancies_by_status=data["vacancies_by_status"],
        applications_by_status=data["applications_by_status"],
        recent_users=[
            DashboardRecentUserItem(
                id=user.id,
                email=user.email,
                role=user.role.name if user.role else "unknown",
                is_active=user.is_active,
                created_at=user.created_at,
            )
            for user in data["recent_users"]
        ],
        recent_vacancies=[
            DashboardRecentVacancyItem(
                id=vacancy.id,
                title=vacancy.title,
                company_name=vacancy.company.name if vacancy.company else None,
                status_name=vacancy.status.name if vacancy.status else None,
                created_at=vacancy.created_at,
            )
            for vacancy in data["recent_vacancies"]
        ],
        recent_applications=[
            DashboardRecentApplicationItem(
                vacancy_id=application.vacancy_id,
                resume_id=application.resume_id,
                status=application.status,
                vacancy_title=application.vacancy.title if application.vacancy else None,
                company_name=application.vacancy.company.name if application.vacancy and application.vacancy.company else None,
                resume_profession=application.resume.profession.name if application.resume and application.resume.profession else None,
                created_at=getattr(application, "created_at", None),
            )
            for application in data["recent_applications"]
        ],
    )


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
    return [map_user(user) for user in users]


@admin_router.get("/users/{user_id}", response_model=UserDetailAdminResponse)
async def get_user_detail(
    user_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await admin_service.get_user_detail(db, user_id)
    return map_user_detail(user)


@admin_router.patch("/users/{user_id}/status", response_model=UserAdminResponse)
async def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await admin_service.update_user_status(db, user_id, payload.is_active)
    return map_user(user)


@admin_router.patch("/users/{user_id}/role", response_model=UserAdminResponse)
async def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await admin_service.update_user_role(db, user_id, payload.role)
    return map_user(user)


@admin_router.get("/companies", response_model=list[CompanyAdminListItem])
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    companies = await admin_service.list_companies(db, skip, limit, search, is_active)
    return [map_company_list(company) for company in companies]


@admin_router.get("/companies/{company_id}", response_model=CompanyAdminDetailResponse)
async def get_company_detail(
    company_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    company = await admin_service.get_company_detail(db, company_id)
    return map_company_detail(company)


@admin_router.patch("/companies/{company_id}/status", response_model=CompanyAdminDetailResponse)
async def update_company_status(
    company_id: int,
    payload: AdminEntityStatusUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    company = await admin_service.update_company_status(db, company_id, payload.is_active)
    return map_company_detail(company)


@admin_router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_company(db, company_id)


@admin_router.get("/applicants", response_model=list[ApplicantAdminListItem])
async def list_applicants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    applicants = await admin_service.list_applicants(db, skip, limit, search, is_active)
    return [map_applicant_list(applicant) for applicant in applicants]


@admin_router.get("/applicants/{applicant_id}", response_model=ApplicantAdminDetailResponse)
async def get_applicant_detail(
    applicant_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    applicant = await admin_service.get_applicant_detail(db, applicant_id)
    return map_applicant_detail(applicant)


@admin_router.patch("/applicants/{applicant_id}/status", response_model=ApplicantAdminDetailResponse)
async def update_applicant_status(
    applicant_id: int,
    payload: AdminEntityStatusUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    applicant = await admin_service.update_applicant_status(db, applicant_id, payload.is_active)
    return map_applicant_detail(applicant)


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


@admin_router.post("/vacancies/bulk-status", response_model=list[VacancyResponse])
async def bulk_update_vacancy_status(
    payload: VacancyBulkStatusUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    vacancies = await admin_service.bulk_update_vacancy_status(db, payload.vacancy_ids, payload.status_id)
    return [await admin_service.get_vacancy(db, vacancy.id) for vacancy in vacancies]


@admin_router.delete("/vacancies/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vacancy(
    vacancy_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_vacancy(db, vacancy_id)


@admin_router.get("/applications", response_model=list[ApplicationAdminListItem])
async def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status_filter: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    vacancy_id: Optional[int] = Query(None),
    applicant_id: Optional[int] = Query(None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    applications = await admin_service.list_applications(
        db,
        skip,
        limit,
        status_filter=status_filter,
        company_id=company_id,
        vacancy_id=vacancy_id,
        applicant_id=applicant_id,
    )
    return [map_application(application) for application in applications]


@admin_router.get("/applications/{vacancy_id}/{resume_id}", response_model=ApplicationAdminDetailResponse)
async def get_application_detail(
    vacancy_id: int,
    resume_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    application = await admin_service.get_application_detail(db, vacancy_id, resume_id)
    return map_application_detail(application)


@admin_router.patch("/applications/{vacancy_id}/{resume_id}", response_model=ApplicationAdminDetailResponse)
async def update_application_status(
    vacancy_id: int,
    resume_id: int,
    payload: ApplicationAdminUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    application = await admin_service.update_application_status(db, vacancy_id, resume_id, payload.status)
    return map_application_detail(application)
