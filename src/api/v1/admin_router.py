from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps.db_deps import get_db
from src.deps.role_checker import require_role
from src.models.model import Applicant, Application, Company, Resume, User, Vacancy
from src.schemas.admin_schema import (
    AdminCreateRequest,
    AdminDeleteRequest,
    AdminDetailResponse,
    AdminEntityStatusUpdate,
    AdminListItemResponse,
    AdminUpdateRequest,
    ApplicantAdminDetailResponse,
    ApplicantAdminListItem,
    ApplicantEducationAdminItem,
    ApplicantResumeAdminItem,
    ApplicantWorkExperienceAdminItem,
    ApplicationAdminDetailResponse,
    ApplicationAdminListItem,
    ApplicationAdminUpdate,
    CatalogItemCreate,
    CatalogItemResponse,
    CatalogItemUpdate,
    CompanyAdminDetailResponse,
    CompanyAdminListItem,
    DashboardMetricItem,
    DashboardRecentApplicationItem,
    DashboardRecentUserItem,
    DashboardRecentVacancyItem,
    DashboardRegistrationPoint,
    DashboardResponse,
    UserAdminResponse,
    UserDetailAdminResponse,
    UserStatusUpdate,
    VacancyAdminDetailResponse,
    VacancyAdminListItem,
    VacancyBulkStatusUpdate,
    VacancyModerationUpdate,
    VacancySkillAdminItem,
)
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


def map_admin_detail(admin: User) -> AdminDetailResponse:
    return AdminDetailResponse(
        id=admin.id,
        email=admin.email,
        role=admin.role.name if admin.role else "admin",
        is_active=admin.is_active,
        created_at=admin.created_at,
        updated_at=admin.updated_at,
        password_set=bool(admin.password),
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
        created_at=getattr(company, "created_at", None),
        updated_at=getattr(company, "updated_at", None),
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
        profession_id=resume.profession_id,
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
        created_at=getattr(applicant, "created_at", None),
        updated_at=getattr(applicant, "updated_at", None),
    )


def map_applicant_detail(applicant: Applicant) -> ApplicantAdminDetailResponse:
    work_experiences: list[ApplicantWorkExperienceAdminItem] = []

    for resume in applicant.resumes or []:
        for work in resume.work_experiences or []:
            work_experiences.append(
                ApplicantWorkExperienceAdminItem(
                    id=work.id,
                    resume_id=resume.id,
                    resume_profession=resume.profession.name if resume.profession else None,
                    company_name=work.company_name,
                    position=work.position,
                    start_date=work.start_date,
                    end_date=work.end_date,
                    description=work.description,
                )
            )

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
        work_experiences=work_experiences,
        applications_count=sum(len(resume.applications or []) for resume in applicant.resumes or []),
    )


def map_vacancy(vacancy: Vacancy) -> VacancyAdminDetailResponse:
    return VacancyAdminDetailResponse(
        id=vacancy.id,
        title=vacancy.title,
        description=vacancy.description,

        company_id=vacancy.company_id,
        city_id=vacancy.city_id,
        profession_id=vacancy.profession_id,
        status_id=vacancy.status_id,

        company_name=vacancy.company.name if vacancy.company else None,
        city_name=vacancy.city.name if vacancy.city else None,
        profession_name=vacancy.profession.name if vacancy.profession else None,
        status_name=vacancy.status.name if vacancy.status else None,

        salary_min=vacancy.salary_min,
        salary_max=vacancy.salary_max,
        currency=vacancy.currency.name if vacancy.currency else None,

        employment_type_name=vacancy.employment_type.name if vacancy.employment_type else None,
        work_schedule_name=vacancy.work_schedule.name if vacancy.work_schedule else None,
        experience_name=vacancy.experience.name if vacancy.experience else None,

        created_at=vacancy.created_at,
        updated_at=vacancy.updated_at,

        skills=[
            VacancySkillAdminItem(id=skill.id, name=skill.name)
            for skill in vacancy.skills or []
        ],
    )


def map_application(application: Application) -> ApplicationAdminListItem:
    applicant = application.resume.applicant if application.resume else None
    applicant_name = (
        " ".join(
            part
            for part in [
                getattr(applicant, "last_name", None),
                getattr(applicant, "first_name", None),
                getattr(applicant, "middle_name", None),
            ]
            if part
        )
        if applicant
        else None
    )

    return ApplicationAdminListItem(
        vacancy_id=application.vacancy_id,
        resume_id=application.resume_id,
        status=application.status,
        created_at=getattr(application, "created_at", None),
        updated_at=getattr(application, "updated_at", None),
        vacancy_title=application.vacancy.title if application.vacancy else None,
        company_name=application.vacancy.company.name if application.vacancy and application.vacancy.company else None,
        applicant_name=applicant_name or (f"Соискатель #{applicant.id}" if applicant else None),
        applicant_id=applicant.id if applicant else None,
        resume_profession=application.resume.profession.name if application.resume and application.resume.profession else None,
    )


def map_application_detail(application: Application) -> ApplicationAdminDetailResponse:
    base = map_application(application)

    return ApplicationAdminDetailResponse(
        **base.model_dump(),
        city_name=application.vacancy.city.name if application.vacancy and application.vacancy.city else None,
        salary_min=application.vacancy.salary_min if application.vacancy else None,
        salary_max=application.vacancy.salary_max if application.vacancy else None,
        cover_letter=application.cover_letter,
    )


@admin_router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    period: str = Query("30d"),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    data = await admin_service.get_dashboard(db, period)

    return DashboardResponse(
        users_total=data["users_total"],
        users_active=data["users_active"],
        users_blocked=data["users_blocked"],
        companies_total=data["companies_total"],
        applicants_total=data["applicants_total"],
        vacancies_total=data["vacancies_total"],
        applications_total=data["applications_total"],
        admins_total=data["admins_total"],
        vacancies_by_status=data["vacancies_by_status"],
        applications_by_status=data["applications_by_status"],
        users_by_role=data["users_by_role"],
        registrations=[
            DashboardRegistrationPoint(
                label=item["label"],
                date=item["date"],
                users=item["users"],
                applicants=item["applicants"],
                companies=item["companies"],
                admins=item["admins"],
            )
            for item in data["registrations"]
        ],
        top_cities=[
            DashboardMetricItem(key=item["key"], label=item["label"], value=item["value"])
            for item in data["top_cities"]
        ],
        top_professions=[
            DashboardMetricItem(key=item["key"], label=item["label"], value=item["value"])
            for item in data["top_professions"]
        ],
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
                company_name=application.vacancy.company.name
                if application.vacancy and application.vacancy.company
                else None,
                resume_profession=application.resume.profession.name
                if application.resume and application.resume.profession
                else None,
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
    search: Optional[str] = Query(None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_catalog_items(db, catalog_name, skip, limit, search)


@admin_router.get("/admins", response_model=list[AdminListItemResponse])
async def list_admins(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    admins = await admin_service.list_admins(db, skip, limit, search, is_active)

    return [
        AdminListItemResponse(
            id=item.id,
            email=item.email,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in admins
    ]


@admin_router.get("/admins/{admin_id}", response_model=AdminDetailResponse)
async def get_admin_detail(
    admin_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    admin = await admin_service.get_admin_detail(db, admin_id)
    return map_admin_detail(admin)


@admin_router.post("/admins", response_model=AdminDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    payload: AdminCreateRequest,
    current_admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    admin = await admin_service.create_admin(db, payload.email, payload.password, actor=current_admin)
    return map_admin_detail(admin)


@admin_router.patch("/admins/{admin_id}", response_model=AdminDetailResponse)
async def update_admin(
    admin_id: int,
    payload: AdminUpdateRequest,
    current_admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    admin = await admin_service.update_admin(
        db=db,
        admin_id=admin_id,
        actor=current_admin,
        email=payload.email,
        new_password=payload.new_password,
        is_active=payload.is_active,
        current_admin_password=payload.current_admin_password,
    )

    return map_admin_detail(admin)


@admin_router.delete("/admins/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin(
    admin_id: int,
    payload: AdminDeleteRequest,
    current_admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_admin(
        db=db,
        admin_id=admin_id,
        actor=current_admin,
        current_admin_password=payload.current_admin_password,
    )


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
    current_admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    if user_id == 1 and payload.is_active is False:
        raise HTTPException(status_code=400, detail="Главного администратора нельзя заблокировать")

    if current_admin.id == user_id and payload.is_active is False:
        raise HTTPException(status_code=400, detail="Нельзя заблокировать самого себя")

    user = await admin_service.update_user_status(db, user_id, payload.is_active)
    return map_user(user)


@admin_router.get("/companies", response_model=list[CompanyAdminListItem])
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    city: Optional[str] = Query(None),
    company_type: Optional[str] = Query(None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    companies = await admin_service.list_companies(db, skip, limit, search, is_active, city, company_type)
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
    city: Optional[str] = Query(None),
    has_resumes: Optional[bool] = Query(None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    applicants = await admin_service.list_applicants(db, skip, limit, search, is_active, city, has_resumes)
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


@admin_router.get("/vacancies", response_model=list[VacancyAdminListItem])
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
    vacancies = await admin_service.list_vacancies(
        db,
        skip,
        limit,
        search=search,
        status_id=status_id,
        city_id=city_id,
        profession_id=profession_id,
        company_id=company_id,
    )

    return [map_vacancy(vacancy) for vacancy in vacancies]


@admin_router.get("/vacancies/{vacancy_id}", response_model=VacancyAdminDetailResponse)
async def get_vacancy(
    vacancy_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    vacancy = await admin_service.get_vacancy(db, vacancy_id)
    return map_vacancy(vacancy)


@admin_router.patch("/vacancies/{vacancy_id}/status", response_model=VacancyAdminDetailResponse)
async def update_vacancy_status(
    vacancy_id: int,
    payload: VacancyModerationUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    vacancy = await admin_service.update_vacancy_status(db, vacancy_id, payload.status_id)
    return map_vacancy(vacancy)


@admin_router.post("/vacancies/bulk-status", response_model=list[VacancyAdminDetailResponse])
async def bulk_update_vacancy_status(
    payload: VacancyBulkStatusUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    vacancies = await admin_service.bulk_update_vacancy_status(db, payload.vacancy_ids, payload.status_id)
    return [map_vacancy(await admin_service.get_vacancy(db, vacancy.id)) for vacancy in vacancies]


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