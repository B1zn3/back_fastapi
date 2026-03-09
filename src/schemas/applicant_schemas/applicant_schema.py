from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List
from src.schemas.city_schema import CityResponse
from src.schemas.applicant_schemas.resume_schema import ResumeResponse
from src.schemas.applicant_schemas.education_schema import EducationResponse

class ApplicantBase(BaseModel):
    photo: Optional[str] = Field(None, example="https://storage.example.com/photos/user1.jpg")
    phone: Optional[str] = Field(None, example="+375295608177", pattern=r'^(\+375|8)[0-9]{9}$')
    birth_date: Optional[date] = Field(None, example="1990-05-15")
    gender: Optional[str] = Field(None, example="м")
    first_name: Optional[str] = Field(None, example="Иван", min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, example="Петров", min_length=2, max_length=50)
    middle_name: Optional[str] = Field(None, example="Сергеевич", min_length=2, max_length=50)

class ApplicantUpdate(ApplicantBase):
    city_name: Optional[str] = Field(None, example="Москва", min_length=2, max_length=100)

class ApplicantResponse(ApplicantBase):
    id: int
    city: Optional[CityResponse] = None
    resumes: List[ResumeResponse] = []
    educations: List[EducationResponse] = []

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "photo": "https://storage.example.com/photos/user1.jpg",
                "phone": "+79991234567",
                "birth_date": "1990-05-15",
                "gender": "м",
                "first_name": "Иван",
                "last_name": "Петров",
                "middle_name": "Сергеевич",
                "city": {"id": 1, "name": "Москва"},
                "resumes": [
                    {
                        "id": 1,
                        "profession_id": 1,
                        "created_at": "2024-01-15T10:30:00",
                        "updated_at": "2024-02-20T14:25:00",
                        "applicant_id": 1,
                        "profession": {"id": 1, "name": "Python разработчик"},
                        "skills": [{"id": 1, "name": "FastAPI"}],
                        "work_experiences": []
                    }
                ],
                "educations": [
                    {
                        "id": 1,
                        "institution_name": "МГУ",
                        "start_date": "2015-09-01",
                        "end_date": "2020-06-30"
                    }
                ]
            }
        }
    }