from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.company_cruds.vacancy_crud import vacancycrud
from src.redis.redis_client import RedisClient
from typing import Optional, List

class VacancyPublicService:
    def __init__(self, redis_client: RedisClient):
        self.vacancycrud = vacancycrud
        self.redis = redis_client

    async def get_vacancies_list(self, db: AsyncSession, skip: int = 0, limit: int = 20, filters: dict = None):
        query = select(self.vacancycrud.model).where(self.vacancycrud.model.is_active == True)
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_vacancy_detail(self, db: AsyncSession, vacancy_id: int):
        vacancy = await self.vacancycrud.get_with_details(db, vacancy_id)
        if not vacancy or not vacancy.is_active:
            return None
        view_key = f"vacancy:views:{vacancy_id}"
        await self.redis.increment_counter(view_key)
        views = await self.redis.get_counter(view_key)
        return vacancy, views

    async def get_vacancy_views(self, vacancy_id: int) -> int:
        return await self.redis.get_counter(f"vacancy:views:{vacancy_id}")