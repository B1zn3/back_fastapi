from fastapi import APIRouter

from src.api.v1.auth_router import auth_router
from src.api.v1.applicant_routers.applicant_router import applicant_router


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(applicant_router)