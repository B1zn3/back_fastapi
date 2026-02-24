from pydantic import BaseModel
from typing import Optional, List
from src.schemas.company_schemas.vacancy_schema import VacancyResponse


class CompanyBase(BaseModel):
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    logo: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None

class CompanyUpdate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    id: int
    vacancies: VacancyResponse

    class Config:
        from_attributes = True