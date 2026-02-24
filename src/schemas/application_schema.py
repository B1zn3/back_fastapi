from pydantic import BaseModel
from typing import Optional

class ApplicationBase(BaseModel):
    status: Optional[str] = "pending"

class ApplicationCreate(ApplicationBase):
    vacancy_id: int
    resume_id: int

class ApplicationResponse(ApplicationBase):
    vacancy_id: int
    resume_id: int

    class Config:
        from_attributes = True