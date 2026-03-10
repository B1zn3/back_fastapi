from fastapi import APIRouter

from src.api.v1.auth_router import auth_router
from src.api.v1.applicant_routers.applicant_router import applicant_router
from src.api.v1.company_routers.company_router import company_router
from src.api.v1.admin_router import admin_router
from src.api.v1.public_router import public_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(applicant_router)
api_router.include_router(company_router)
api_router.include_router(admin_router)
api_router.include_router(public_router)
