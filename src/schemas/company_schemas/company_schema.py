from typing import Optional

from pydantic import BaseModel, Field

from src.schemas.company_schemas.vacancy_schema import VacancyResponse


class CompanyCityResponse(BaseModel):
    id: int
    name: str

    full_name: Optional[str] = None

    district_id: Optional[int] = None
    district_name: Optional[str] = None

    region_id: Optional[int] = None
    region_name: Optional[str] = None

    settlement_type_id: Optional[int] = None
    settlement_type_name: Optional[str] = None

    model_config = {"from_attributes": True}


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    website: Optional[str] = None
    logo: Optional[str] = None
    founded_year: Optional[int] = Field(default=None, ge=1800, le=2100)
    employee_count: Optional[int] = Field(default=None, ge=0)
    company_type_id: Optional[int] = Field(default=None, ge=1)

    # Города офисов компании
    city_ids: Optional[list[int]] = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    logo: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None

    company_type_id: Optional[int] = None
    company_type_name: Optional[str] = None

    city_names: list[str] = Field(default_factory=list)

    city_ids: list[int] = Field(default_factory=list)
    cities: list[CompanyCityResponse] = Field(default_factory=list)

    vacancies: list[VacancyResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}