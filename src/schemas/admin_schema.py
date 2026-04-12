from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class CatalogItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class CatalogItemUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class CatalogItemResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class UserAdminResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    company_id: Optional[int] = None
    applicant_id: Optional[int] = None


class UserDetailAdminResponse(UserAdminResponse):
    company_name: Optional[str] = None
    applicant_full_name: Optional[str] = None
    vacancies_count: int = 0
    resumes_count: int = 0
    applications_count: int = 0


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: str = Field(..., min_length=1, max_length=50)


class CompanyAdminListItem(BaseModel):
    id: int
    name: str
    website: Optional[str] = None
    company_type_name: Optional[str] = None
    cities: list[str] = Field(default_factory=list)
    vacancies_count: int = 0
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    is_active: bool = True


class CompanyAdminDetailResponse(CompanyAdminListItem):
    description: Optional[str] = None
    logo: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None
    vacancy_ids: list[int] = Field(default_factory=list)


class ApplicantResumeAdminItem(BaseModel):
    id: int
    profession_name: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    work_experiences_count: int = 0
    applications_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ApplicantEducationAdminItem(BaseModel):
    id: int
    institution_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ApplicantAdminListItem(BaseModel):
    id: int
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    city_name: Optional[str] = None
    resumes_count: int = 0
    educations_count: int = 0
    is_active: bool = True


class ApplicantAdminDetailResponse(ApplicantAdminListItem):
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    photo: Optional[str] = None
    resumes: list[ApplicantResumeAdminItem] = Field(default_factory=list)
    educations: list[ApplicantEducationAdminItem] = Field(default_factory=list)
    applications_count: int = 0


class VacancyModerationUpdate(BaseModel):
    status_id: int


class VacancyBulkStatusUpdate(BaseModel):
    vacancy_ids: list[int] = Field(default_factory=list)
    status_id: int


class ApplicationAdminListItem(BaseModel):
    vacancy_id: int
    resume_id: int
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    vacancy_title: Optional[str] = None
    company_name: Optional[str] = None
    applicant_name: Optional[str] = None
    resume_profession: Optional[str] = None


class ApplicationAdminDetailResponse(ApplicationAdminListItem):
    city_name: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None


class ApplicationAdminUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class AdminEntityStatusUpdate(BaseModel):
    is_active: bool


class DashboardRecentUserItem(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime


class DashboardRecentVacancyItem(BaseModel):
    id: int
    title: str
    company_name: Optional[str] = None
    status_name: Optional[str] = None
    created_at: Optional[datetime] = None


class DashboardRecentApplicationItem(BaseModel):
    vacancy_id: int
    resume_id: int
    status: str
    vacancy_title: Optional[str] = None
    company_name: Optional[str] = None
    resume_profession: Optional[str] = None
    created_at: Optional[datetime] = None


class DashboardResponse(BaseModel):
    users_total: int
    users_active: int
    companies_total: int
    applicants_total: int
    vacancies_total: int
    applications_total: int
    vacancies_by_status: dict[str, int]
    applications_by_status: dict[str, int]
    recent_users: list[DashboardRecentUserItem] = Field(default_factory=list)
    recent_vacancies: list[DashboardRecentVacancyItem] = Field(default_factory=list)
    recent_applications: list[DashboardRecentApplicationItem] = Field(default_factory=list)
