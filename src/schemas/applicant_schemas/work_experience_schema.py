from pydantic import BaseModel
from datetime import date
from typing import Optional

class WorkExperienceBase(BaseModel):
    company_name: str
    position: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None

class WorkExperienceCreate(WorkExperienceBase):
    resume_id: int

class WorkExperienceUpdate(WorkExperienceBase):
    pass

class WorkExperienceResponse(WorkExperienceBase):
    id: int
    resume_id: int

    class Config:
        from_attributes = True