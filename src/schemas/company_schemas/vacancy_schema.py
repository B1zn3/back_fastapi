from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from src.schemas.profession_schema import ProfessionResponse
from src.schemas.company_schemas.employment_type_schema import EmploymentTypeResponse
from src.schemas.company_schemas.work_schedule_schema import WorkScheduleResponse
from src.schemas.skill_schema import SkillResponse

class VacancyBase(BaseModel):
    title: str
    description: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    experience_required: Optional[str] = None
    is_active: bool = True
    profession_id: int
    employment_type_id: Optional[int] = None
    work_schedule_id: Optional[int] = None

class VacancyCreate(VacancyBase):
    pass

class VacancyUpdate(VacancyBase):
    pass

class VacancyResponse(VacancyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    company_id: int
    profession: Optional[ProfessionResponse] = None
    employment_type: Optional[EmploymentTypeResponse] = None
    work_schedule: Optional[WorkScheduleResponse] = None
    skills: List[SkillResponse] = []

    class Config:
        from_attributes = True