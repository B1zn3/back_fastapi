from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.deps.db_deps import get_db
from src.deps.role_checker import require_role
from src.services.ApplicantServices.applicant_service import applicant_service
from src.schemas.applicant_schemas.applicant_schema import ApplicantUpdate, ApplicantResponse
from src.schemas.applicant_schemas.resume_schema import ResumeCreate, ResumeUpdate, ResumeResponse
from src.schemas.skill_schema import SkillCreate
from src.schemas.applicant_schemas.work_experience_schema import WorkExperienceCreate, WorkExperienceUpdate, WorkExperienceResponse
from src.models.model import User, Applicant

applicant_router = APIRouter(prefix="/applicants", tags=["Соискатели"])

async def get_current_applicant(
    current_user: User = Depends(require_role("applicant")),
    db: AsyncSession = Depends(get_db)
) -> Applicant:
    applicant = await applicant_service.applicantcrud.get_by_user_id_with_details(db, current_user.id)
    if not applicant:
        raise HTTPException(status_code=404, detail="Профиль соискателя не найден")
    return applicant

@applicant_router.get("/me", response_model=ApplicantResponse)
async def get_applicant_profile(
    applicant: Applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    return await applicant_service.get_applicant_profile(db, applicant)

@applicant_router.put("/me", response_model=ApplicantResponse)
async def update_applicant_profile(
    update_data: ApplicantUpdate,
    applicant: Applicant = Depends(get_current_applicant),
    current_user: User = Depends(require_role("applicant")), 
    db: AsyncSession = Depends(get_db)
):
    return await applicant_service.update_applicant_profile(db, applicant, update_data, current_user.id)

@applicant_router.post("/me/resumes", response_model=ResumeResponse, status_code=201)
async def create_resume(
    resume_data: ResumeCreate,
    applicant: Applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    return await applicant_service.create_resume(db, applicant.id, resume_data)

@applicant_router.get("/me/resumes", response_model=list[ResumeResponse])
async def list_resumes(
    applicant: Applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    return await applicant_service.get_resumes(db, applicant.id)

@applicant_router.get("/me/resumes/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    applicant: Applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    return await applicant_service.get_resume_detail(db, resume_id, applicant.id)

@applicant_router.put("/me/resumes/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: int,
    resume_data: ResumeUpdate,
    applicant: Applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    return await applicant_service.update_resume(db, resume_id, applicant.id, resume_data)

@applicant_router.delete("/me/resumes/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: int,
    applicant: Applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    await applicant_service.delete_resume(db, resume_id, applicant.id)

# ===== Навыки =====
@applicant_router.post("/me/resumes/{resume_id}/skills", response_model=ResumeResponse)
async def add_skill_to_resume(
    resume_id: int,
    skill_data: SkillCreate,
    applicant: Applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    return await applicant_service.add_skill_to_resume(db, resume_id, applicant.id, skill_data.name)

@applicant_router.delete("/me/resumes/{resume_id}/skills/{skill_id}", response_model=ResumeResponse)
async def remove_skill_from_resume(
    resume_id: int,
    skill_id: int,
    applicant: Applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    return await applicant_service.remove_skill_from_resume(db, resume_id, applicant.id, skill_id)

# ===== Опыт работы =====
@applicant_router.post("/me/resumes/{resume_id}/work-experiences", response_model=WorkExperienceResponse)
async def add_work_experience(
    resume_id: int,
    exp_data: WorkExperienceCreate,
    applicant: Applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    return await applicant_service.add_work_experience(db, resume_id, applicant.id, exp_data)

@applicant_router.put("/me/resumes/{resume_id}/work-experiences/{exp_id}", response_model=WorkExperienceResponse)
async def update_work_experience(
    resume_id: int,
    exp_id: int,
    exp_data: WorkExperienceUpdate,
    applicant: Applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    return await applicant_service.update_work_experience(db, exp_id, resume_id, applicant.id, exp_data)

@applicant_router.delete("/me/resumes/{resume_id}/work-experiences/{exp_id}", status_code=204)
async def delete_work_experience(
    resume_id: int,
    exp_id: int,
    applicant: Applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    await applicant_service.delete_work_experience(db, exp_id, resume_id, applicant.id)