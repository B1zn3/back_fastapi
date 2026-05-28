from datetime import date
from typing import Optional, List

from pydantic import BaseModel, Field

from src.schemas.city_schema import CityResponse
from src.schemas.applicant_schemas.resume_schema import ResumeResponse
from src.schemas.applicant_schemas.education_schema import EducationResponse


class ApplicantBase(BaseModel):
    photo: Optional[str] = Field(None, example="https://storage.example.com/photos/user1.jpg")
    phone: Optional[str] = Field(None, example="+375295608177", pattern=r"^(\+375|8)[0-9]{9}$")
    birth_date: Optional[date] = Field(None, example="1990-05-15")
    gender: Optional[str] = Field(None, example="м")
    first_name: Optional[str] = Field(None, example="Иван", min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, example="Петров", min_length=2, max_length=50)
    middle_name: Optional[str] = Field(None, example="Сергеевич", min_length=2, max_length=50)


class ApplicantUpdate(ApplicantBase):
    city_id: Optional[int] = Field(default=None, ge=1)


class ApplicantResponse(ApplicantBase):
    id: int
    city: Optional[CityResponse] = None
    resumes: List[ResumeResponse] = Field(default_factory=list)
    educations: List[EducationResponse] = Field(default_factory=list)

    model_config = {
        "from_attributes": False,
    }