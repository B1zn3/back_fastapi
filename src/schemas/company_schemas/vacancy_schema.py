from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class VacancySkillResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class VacancyCreate(BaseModel):
    employment_type_id: int = Field(..., ge=1)
    work_schedule_id: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    salary_min: int = Field(..., ge=0)
    salary_max: int = Field(..., ge=0)
    currency_id: int = Field(..., ge=1)
    experience_id: int = Field(..., ge=1)
    city_id: int = Field(..., ge=1)
    profession_id: int = Field(..., ge=1)
    status_id: Optional[int] = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_salary(self):
        if self.salary_min > self.salary_max:
            raise ValueError("salary_min не может быть больше salary_max")
        return self


class VacancyUpdate(BaseModel):
    employment_type_id: Optional[int] = Field(default=None, ge=1)
    work_schedule_id: Optional[int] = Field(default=None, ge=1)
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, min_length=1)
    salary_min: Optional[int] = Field(default=None, ge=0)
    salary_max: Optional[int] = Field(default=None, ge=0)
    currency_id: Optional[int] = Field(default=None, ge=1)
    experience_id: Optional[int] = Field(default=None, ge=1)
    city_id: Optional[int] = Field(default=None, ge=1)
    profession_id: Optional[int] = Field(default=None, ge=1)
    status_id: Optional[int] = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_salary(self):
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("salary_min не может быть больше salary_max")
        return self


class VacancyResponse(BaseModel):
    id: int
    title: str
    description: str

    employment_type_id: int
    work_schedule_id: int
    currency_id: int
    experience_id: int
    status_id: int
    company_id: int
    city_id: int
    profession_id: int

    salary_min: int
    salary_max: int

    employment_type_name: Optional[str] = None
    work_schedule_name: Optional[str] = None
    currency_name: Optional[str] = None
    currency: Optional[str] = None
    experience_name: Optional[str] = None
    status_name: Optional[str] = None
    company_name: Optional[str] = None
    city_name: Optional[str] = None
    profession_name: Optional[str] = None

    skills: list[VacancySkillResponse] = Field(default_factory=list)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}