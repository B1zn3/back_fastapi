from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.core.constants import ApplicationStatus


class EmployerApplicationVacancyInfo(BaseModel):
    id: int
    title: str
    city_name: Optional[str] = None
    profession_name: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    skills: list[str] = Field(default_factory=list)


class EmployerApplicationApplicantInfo(BaseModel):
    id: Optional[int] = None
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    city_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    photo: Optional[str] = None


class EmployerApplicationResumeInfo(BaseModel):
    id: int
    profession_id: Optional[int] = None
    profession_name: Optional[str] = None
    title: str
    skills: list[str] = Field(default_factory=list)
    experience_years: float = 0
    latest_position: Optional[str] = None
    latest_company: Optional[str] = None
    educations_count: int = 0
    work_experiences_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EmployerApplicationMatchInfo(BaseModel):
    score: int
    profession_score: int
    skills_score: int
    cover_letter_score: int
    city_score: int
    experience_score: int
    freshness_score: int
    suspicion_penalty: int
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    skills_match_percent: int = 0


class EmployerApplicationSuspicionInfo(BaseModel):
    period_days: int
    period_from: datetime
    applications_count: int
    pending_count: int
    accepted_count: int
    rejected_count: int
    resume_changes_count: int
    applicant_resume_changes_count: int
    suspicion_score: int
    is_suspicious: bool
    reasons: list[str] = Field(default_factory=list)


class EmployerApplicationResponse(BaseModel):
    id: int
    vacancy_id: int
    resume_id: int
    status: ApplicationStatus
    status_label: str
    cover_letter: Optional[str] = None
    has_cover_letter: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    vacancy: EmployerApplicationVacancyInfo
    applicant: EmployerApplicationApplicantInfo
    resume: EmployerApplicationResumeInfo
    match: EmployerApplicationMatchInfo
    suspicion: EmployerApplicationSuspicionInfo


class EmployerApplicationStatsResponse(BaseModel):
    total: int
    pending: int
    accepted: int
    rejected: int
    suspicious: int
    with_cover_letter: int
    average_match_score: int


class EmployerApplicationListResponse(BaseModel):
    items: list[EmployerApplicationResponse] = Field(default_factory=list)
    total: int
    stats: EmployerApplicationStatsResponse


class EmployerApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus