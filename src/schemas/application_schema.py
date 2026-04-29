from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.core.constants import ApplicationStatus


class ApplicationCreate(BaseModel):
    vacancy_id: int = Field(..., example=1)
    resume_id: int = Field(..., example=1)
    cover_letter: Optional[str] = Field(
        default=None,
        max_length=1000,
        example="Здравствуйте! Меня заинтересовала ваша вакансия.",
    )


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus = Field(..., example="accepted")


class ApplicationVacancyInfo(BaseModel):
    id: int
    title: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    city_name: Optional[str] = None
    profession_name: Optional[str] = None


class ApplicationResumeInfo(BaseModel):
    id: int
    profession_id: Optional[int] = None
    profession_name: Optional[str] = None
    title: str


class ApplicationResponse(BaseModel):
    id: int
    vacancy_id: int
    resume_id: int
    status: ApplicationStatus
    cover_letter: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    vacancy: Optional[ApplicationVacancyInfo] = None
    resume: Optional[ApplicationResumeInfo] = None


class ApplicationStateResponse(BaseModel):
    id: Optional[int] = None
    vacancy_id: int
    applied: bool
    status: Optional[ApplicationStatus] = None
    label: str
    resume_id: Optional[int] = None
    cover_letter: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None