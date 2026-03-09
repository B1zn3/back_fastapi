from pydantic import BaseModel, field_validator
from datetime import date
from typing import Optional


class EducationBase(BaseModel):
    institution_id: int 
    start_date: date
    end_date: Optional[date] = None

    @field_validator('end_date')
    def validate_dates(cls, v, values):
        if v and values.data.get('start_date') and v < values.data['start_date']:
            raise ValueError('Дата окончания не может быть раньше даты начала')
        return v


class EducationCreate(EducationBase):
    pass

class EducationUpdate(EducationBase):
    pass

class EducationResponse(EducationBase):
    id: int
    institution_name: str 

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "institution_id": 1,
                "start_date": "2015-09-01",
                "end_date": "2020-06-30"
            }
        }
    }