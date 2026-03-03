from pydantic import BaseModel
from datetime import date
from typing import Optional, List
from src.schemas.applicant_schemas.education_schema import EducationResponse
from src.schemas.city_schema import CityResponse
from src.schemas.applicant_schemas.resume_schema import ResumeResponse

class ApplicantBase(BaseModel):
    photo: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None

class ApplicantUpdate(ApplicantBase):
    city_name: Optional[str] = None

class ApplicantResponse(ApplicantBase):
    id: int
    city: Optional[CityResponse] = None
    resumes: List[ResumeResponse] = []
    educations: List[EducationResponse] = []

    class Config:
        from_attributes = True