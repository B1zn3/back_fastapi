from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FavoriteVacancyCreate(BaseModel):
    resume_id: int = Field(..., example=1)


class FavoriteVacancyResumeInfo(BaseModel):
    id: int
    profession_id: Optional[int] = None
    profession_name: Optional[str] = None
    title: str


class FavoriteVacancySkillInfo(BaseModel):
    id: int
    name: str


class FavoriteVacancyInfo(BaseModel):
    id: int
    title: str
    description: Optional[str] = None

    salary_min: Optional[int] = None
    salary_max: Optional[int] = None

    company_id: Optional[int] = None
    company_name: Optional[str] = None

    city_id: Optional[int] = None
    city_name: Optional[str] = None

    profession_id: Optional[int] = None
    profession_name: Optional[str] = None

    employment_type_id: Optional[int] = None
    employment_type_name: Optional[str] = None

    work_schedule_id: Optional[int] = None
    work_schedule_name: Optional[str] = None

    currency_id: Optional[int] = None
    currency_name: Optional[str] = None
    currency: Optional[str] = None

    experience_id: Optional[int] = None
    experience_name: Optional[str] = None

    status_id: Optional[int] = None
    status_name: Optional[str] = None

    skills: list[FavoriteVacancySkillInfo] = []

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FavoriteVacancyResponse(BaseModel):
    favorite_id: int
    vacancy_id: int
    resume_id: int
    resume: FavoriteVacancyResumeInfo
    vacancy: Optional[FavoriteVacancyInfo] = None


class FavoriteVacancyStateResponse(BaseModel):
    vacancy_id: int
    is_favorite: bool
    favorite_id: Optional[int] = None
    resume_id: Optional[int] = None
    resume: Optional[FavoriteVacancyResumeInfo] = None