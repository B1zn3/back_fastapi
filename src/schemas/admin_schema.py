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
