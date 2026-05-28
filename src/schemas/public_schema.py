from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CityPublicCatalogItem(BaseModel):
    id: int
    name: str

    district_id: Optional[int] = None
    district_name: Optional[str] = None

    region_id: Optional[int] = None
    region_name: Optional[str] = None

    settlement_type_id: Optional[int] = None
    settlement_type_name: Optional[str] = None

    full_name: Optional[str] = None


class VacancyPublicListItem(BaseModel):
    id: int
    title: str
    description: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    created_at: datetime

    company_id: Optional[int] = None
    company_name: Optional[str] = None

    city_id: Optional[int] = None
    city_name: Optional[str] = None
    city_full_name: Optional[str] = None
    city: Optional[CityPublicCatalogItem] = None

    profession_name: Optional[str] = None


class VacancyPublicDetail(VacancyPublicListItem):
    updated_at: Optional[datetime] = None
    employment_type: Optional[str] = None
    work_schedule: Optional[str] = None
    currency: Optional[str] = None
    experience: Optional[str] = None
    skills: list[str] = Field(default_factory=list)

    company_type_name: Optional[str] = None
    company_description: Optional[str] = None
    company_website: Optional[str] = None
    company_logo: Optional[str] = None
    company_founded_year: Optional[int] = None
    company_employee_count: Optional[int] = None

    company_city_names: list[str] = Field(default_factory=list)
    company_cities: list[CityPublicCatalogItem] = Field(default_factory=list)


class ProfessionPublicListItem(BaseModel):
    id: int
    name: str


class CompanyPublicListItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    logo: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None
    vacancies_count: int = 0

    city_names: list[str] = Field(default_factory=list)
    cities: list[CityPublicCatalogItem] = Field(default_factory=list)

    first_letter: str
    company_type_name: Optional[str] = None


class CompanyPublicDetail(CompanyPublicListItem):
    pass