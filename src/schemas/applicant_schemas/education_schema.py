from pydantic import BaseModel
from datetime import date
from typing import Optional

class EducationBase(BaseModel):
    institution_name: str
    start_date: date
    end_date: Optional[date] = None

class EducationCreate(EducationBase):
    resume_id: int

class EducationUpdate(EducationBase):
    pass

class EducationResponse(EducationBase):
    id: int
    resume_id: int
    institution_id: int
    class Config:
        from_attributes = True