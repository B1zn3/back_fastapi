from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int
    changed_at: datetime