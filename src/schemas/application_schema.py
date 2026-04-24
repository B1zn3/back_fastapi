from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from src.core.constants import ApplicationStatus


class ApplicationBase(BaseModel):
    status: ApplicationStatus = Field(ApplicationStatus.PENDING, example="pending")


class ApplicationCreate(BaseModel):
    vacancy_id: int = Field(..., example=1)
    resume_id: Optional[int] = Field(None, example=1)


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus = Field(..., example="accepted")


class ApplicationResponse(ApplicationBase):
    vacancy_id: int
    resume_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "vacancy_id": 1,
                "resume_id": 1,
                "status": "pending",
                "created_at": None,
                "updated_at": None
            }
        }
    }