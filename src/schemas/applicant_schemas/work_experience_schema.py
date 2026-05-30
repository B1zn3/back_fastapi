from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional

class WorkExperienceBase(BaseModel):
    company_name: str = Field(..., example="Яндекс", min_length=2, max_length=200)
    position: str = Field(..., example="Senior Python Developer", min_length=2, max_length=200)
    start_date: date = Field(..., example="2020-07-01")
    end_date: Optional[date] = Field(None, example="2023-12-31")
    description: Optional[str] = Field(None, example="Разработка микросервисов на FastAPI", max_length=2000)

    @field_validator('end_date')
    def validate_dates(cls, v, values):
        if v and values.data.get('start_date') and v < values.data['start_date']:
            raise ValueError('Дата окончания не может быть раньше даты начала')
        return v

class WorkExperienceCreate(WorkExperienceBase):
    pass

class WorkExperienceUpdate(WorkExperienceBase):
    pass

class WorkExperienceResponse(WorkExperienceBase):
    id: int
    resume_id: int

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "resume_id": 1,
                "company_name": "Яндекс",
                "position": "Senior Python Developer",
                "start_date": "2020-07-01",
                "end_date": "2023-12-31",
                "description": "Разработка микросервисов на FastAPI"
            }
        }
    }