from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import Experience

class ExperienceCrud(BaseCrud):
    def __init__(self):
        super().__init__(Experience)

    async def get_or_create(self, db: AsyncSession, name: str) -> Experience:
        result = await db.execute(select(Experience).where(Experience.name == name))
        exp = result.scalar_one_or_none()
        if not exp:
            exp = Experience(name=name)
            db.add(exp)
            await db.flush()
        return exp

experiencecrud = ExperienceCrud()