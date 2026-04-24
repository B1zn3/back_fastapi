from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from src.deps.db_deps import get_db
from src.deps.role_checker import require_role
from src.deps.pagination import pagination_params
from src.services.ApplicantServices.applicant_service import applicant_service
from src.services.application_service import application_service
from src.schemas.applicant_schemas.applicant_schema import ApplicantUpdate, ApplicantResponse
from src.schemas.applicant_schemas.resume_schema import ResumeCreate, ResumeUpdate, ResumeResponse
from src.schemas.skill_schema import SkillCreate, SkillsBatchCreate
from src.schemas.applicant_schemas.work_experience_schema import (
    WorkExperienceCreate, WorkExperienceUpdate, WorkExperienceResponse
)
from src.schemas.applicant_schemas.education_schema import (
    EducationCreate, EducationUpdate, EducationResponse
)
from src.schemas.application_schema import ApplicationCreate, ApplicationResponse
from src.models.model import Applicant, User
from src.core.exceptions import BaseAppException

applicant_router = APIRouter(prefix="/applicants", tags=["Соискатели"])

async def get_current_applicant(
    current_user: User = Depends(require_role("applicant")),
    db: AsyncSession = Depends(get_db)
) -> Applicant:
    logger.info(f"Getting applicant for user {current_user.id}")
    applicant = await applicant_service.applicantcrud.get_by_user_id_with_details(db, current_user.id)
    if not applicant:
        logger.error(f"Applicant not found for user {current_user.id}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Профиль соискателя не найден")
    return applicant

# ---------- Профиль ----------
@applicant_router.get("/me", response_model=ApplicantResponse)
async def get_applicant_profile(
    applicant = Depends(get_current_applicant)
):
    return applicant

@applicant_router.put("/me", response_model=ApplicantResponse)
async def update_applicant_profile(
    update_data: ApplicantUpdate,
    current_user: User = Depends(require_role("applicant")),
    db: AsyncSession = Depends(get_db)
):
    updated = await applicant_service.update_profile(db, current_user.id, update_data)
    return updated

# ---------- Резюме ----------
@applicant_router.post("/me/resumes", response_model=ResumeResponse, status_code=201)
async def create_resume(
    data: ResumeCreate,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await applicant_service.create_resume(db, applicant.id, data)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@applicant_router.get("/me/resumes", response_model=list[ResumeResponse])
async def list_resumes(
    pagination: dict = Depends(pagination_params),
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    return await applicant_service.get_resumes(db, applicant.id, **pagination)

@applicant_router.get("/me/resumes/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await applicant_service.get_resume_detail(db, resume_id, applicant.id)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@applicant_router.put("/me/resumes/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: int,
    data: ResumeUpdate,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await applicant_service.update_resume(db, resume_id, applicant.id, data)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@applicant_router.delete("/me/resumes/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: int,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        await applicant_service.delete_resume(db, resume_id, applicant.id)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

# ---------- Навыки резюме ----------
@applicant_router.post("/me/resumes/{resume_id}/skills", response_model=ResumeResponse)
async def add_skill_to_resume(
    resume_id: int,
    skill_data: SkillCreate,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await applicant_service.add_skill_to_resume(db, resume_id, applicant.id, skill_data.name)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@applicant_router.delete("/me/resumes/{resume_id}/skills/{skill_id}", response_model=ResumeResponse)
async def remove_skill_from_resume(
    resume_id: int,
    skill_id: int,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await applicant_service.remove_skill_from_resume(db, resume_id, applicant.id, skill_id)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@applicant_router.post("/me/resumes/{resume_id}/skills/batch", response_model=ResumeResponse)
async def add_skills_batch(
    resume_id: int,
    skills_data: SkillsBatchCreate,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await applicant_service.add_skills_batch(db, resume_id, applicant.id, skills_data.skills)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

# ---------- Опыт работы ----------
@applicant_router.post("/me/resumes/{resume_id}/work-experiences", response_model=WorkExperienceResponse)
async def add_work_experience(
    resume_id: int,
    data: WorkExperienceCreate,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await applicant_service.add_work_experience(db, resume_id, applicant.id, data)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@applicant_router.put("/me/resumes/{resume_id}/work-experiences/{exp_id}", response_model=WorkExperienceResponse)
async def update_work_experience(
    resume_id: int,
    exp_id: int,
    data: WorkExperienceUpdate,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await applicant_service.update_work_experience(db, exp_id, resume_id, applicant.id, data)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@applicant_router.delete("/me/resumes/{resume_id}/work-experiences/{exp_id}", status_code=204)
async def delete_work_experience(
    resume_id: int,
    exp_id: int,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        await applicant_service.delete_work_experience(db, exp_id, resume_id, applicant.id)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

# ---------- Образование ----------
@applicant_router.post("/me/education", response_model=EducationResponse)
async def add_education(
    data: EducationCreate,
    current_user: User = Depends(require_role("applicant")),
    db: AsyncSession = Depends(get_db)
):
    try:
        edu = await applicant_service.add_education(db, current_user.id, data)
        return edu
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@applicant_router.put("/me/education/{edu_id}", response_model=EducationResponse)
async def update_education(
    edu_id: int,
    data: EducationUpdate,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await applicant_service.update_education(db, edu_id, applicant.id, data)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@applicant_router.delete("/me/education/{edu_id}", status_code=204)
async def delete_education(
    edu_id: int,
    applicant = Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db)
):
    try:
        await applicant_service.delete_education(db, edu_id, applicant.id)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

# ---------- Отклики на вакансии ----------
@applicant_router.post("/me/applications", response_model=ApplicationResponse, status_code=201)
async def apply_to_vacancy(
    application_data: ApplicationCreate,
    applicant=Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await application_service.apply_to_vacancy(db, applicant.id, application_data)
    except BaseAppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@applicant_router.get("/me/applications", response_model=list[ApplicationResponse])
async def get_my_applications(
    pagination: dict = Depends(pagination_params),
    applicant=Depends(get_current_applicant),
    db: AsyncSession = Depends(get_db),
):
    return await application_service.get_applicant_applications(
        db,
        applicant.id,
        **pagination,
    )