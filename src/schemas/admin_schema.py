from datetime import datetime
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


class UserStatusUpdate(BaseModel):
    is_active: bool


class VacancyModerationUpdate(BaseModel):
    status_id: int


class VacancyPublicListItem(BaseModel):
    id: int
    title: str
    description: str
    salary_min: int
    salary_max: int
    created_at: datetime
    company_name: str
    city_name: str
    profession_name: str


class VacancyPublicDetail(VacancyPublicListItem):
    updated_at: datetime
    employment_type: str
    work_schedule: str
    currency: str
    experience: str
    skills: list[str] = []
    company_description: Optional[str] = None
    company_website: Optional[str] = None
    company_logo: Optional[str] = None
    company_founded_year: Optional[int] = None
    company_employee_count: Optional[int] = None

class CompanyPublicListItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    logo: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None
    vacancies_count: int = 0
    city_names: list[str] = []

class ProfessionPublicListItem(BaseModel):
    id: int
    name: str

class CompanyPublicDetail(CompanyPublicListItem):
    pass

class VacancyPublicDetail(BaseModel):
    id: int
    title: str
    description: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    company_name: Optional[str] = None
    city_name: Optional[str] = None
    profession_name: Optional[str] = None
    employment_type: Optional[str] = None
    work_schedule: Optional[str] = None
    currency: Optional[str] = None
    experience: Optional[str] = None

    skills: list[str] = []

    company_description: Optional[str] = None
    company_website: Optional[str] = None
    company_logo: Optional[str] = None
    company_founded_year: Optional[int] = None
    company_employee_count: Optional[int] = None
    company_cities: list[str] = []