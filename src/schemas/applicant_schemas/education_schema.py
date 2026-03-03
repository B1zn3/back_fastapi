from pydantic import BaseModel
from datetime import date
from typing import Optional

class EducationBase(BaseModel):
    institution_name: str
    start_date: date
    end_date: Optional[date] = None

class EducationCreate(EducationBase):
    pass

class EducationUpdate(EducationBase):
    pass

class EducationResponse(EducationBase):
    id: int

    class Config:
        from_attributes = True