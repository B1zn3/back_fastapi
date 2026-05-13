from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class CandidateResumeEducation(BaseModel):
    id: int
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CandidateResumeWorkExperience(BaseModel):
    id: int
    company_name: str
    position: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None


class CandidateResumeListItem(BaseModel):
    id: int
    applicant_id: int

    applicant_full_name: str
    applicant_first_name: Optional[str] = None
    applicant_last_name: Optional[str] = None
    applicant_middle_name: Optional[str] = None
    applicant_city_name: Optional[str] = None
    applicant_photo: Optional[str] = None
    applicant_age: Optional[int] = None
    applicant_gender: Optional[str] = None
    applicant_phone: Optional[str] = None
    applicant_birth_date: Optional[date] = None

    profession_id: Optional[int] = None
    profession_name: Optional[str] = None

    skills: list[str] = Field(default_factory=list)
    work_experiences: list[CandidateResumeWorkExperience] = Field(default_factory=list)
    educations: list[CandidateResumeEducation] = Field(default_factory=list)

    work_experiences_count: int = 0
    applications_count: int = 0

    latest_position: Optional[str] = None
    latest_company: Optional[str] = None
    experience_years: float = 0

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CandidateResumeListResponse(BaseModel):
    items: list[CandidateResumeListItem]
    total: int