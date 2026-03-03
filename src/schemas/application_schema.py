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

class ApplicationUpdate(BaseModel):
    status: Optional[str]

    class Config:
        from_attributes = True