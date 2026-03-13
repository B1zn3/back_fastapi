from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.router import api_router
from src.redis.client import redis_client
from src.core.config import settings
from src.models.seed import seed_all
from src.redis.auth import session_manager
from src.utils.logger import logger



@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.connect()
    await session_manager.initialize()
    await seed_all()
    logger.info("Application started")
    yield
    await redis_client.close()
    logger.info("Application stopped")


app = FastAPI(lifespan=lifespan, title="JobFinder")

app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    origin = request.headers.get("origin", "-")
    logger.info(f"HTTP {request.method} {request.url.path} origin={origin}")
    response = await call_next(request)
    logger.info(f"HTTP {request.method} {request.url.path} -> {response.status_code}")
    return response

