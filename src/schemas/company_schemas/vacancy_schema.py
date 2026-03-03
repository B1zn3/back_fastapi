from pydantic import BaseModel, ConfigDict
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
    currency: int
    experience_required: int
    is_active: bool = True
    profession_id: int
    employment_type_id: Optional[int] = None
    work_schedule_id: Optional[int] = None


class VacancyCreate(BaseModel):
    title: str
    description: str
    profession_id: int  # важно: profession_id, а не profession
    city_id: int        # важно: city_id, а не city
    employment_type_id: int  # важно: employment_type_id, а не employment_type
    work_schedule_id: int    # важно: work_schedule_id, а не work_schedule
    salary_min: int
    salary_max: int
    currency_id: int
    experience_id: int

class VacancyUpdate(VacancyCreate):
    pass

class VacancyResponse(BaseModel):
    id: int
    title: str
    description: str
    profession_id: int
    city_id: int
    employment_type_id: int
    work_schedule_id: int
    salary_min: int
    salary_max: int
    currency_id: int  # вместо currency: str
    experience_id: int
    status_id: int
    company_id: int
    created_at: datetime
    updated_at: datetime
    

    class Config:
        from_attributes = True