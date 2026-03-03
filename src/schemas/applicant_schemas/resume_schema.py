from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from src.schemas.profession_schema import ProfessionResponse
from src.schemas.skill_schema import SkillResponse
from src.schemas.applicant_schemas.work_experience_schema import WorkExperienceResponse

class ResumeBase(BaseModel):
    profession_id: int

class ResumeCreate(ResumeBase):
    pass

class ResumeUpdate(ResumeBase):
    pass

class ResumeResponse(ResumeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    applicant_id: int
    profession: Optional[ProfessionResponse] = None
    skills: List[SkillResponse] = []
    work_experiences: List[WorkExperienceResponse] = []

    class Config:
        from_attributes = True