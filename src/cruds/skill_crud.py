from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import Skill

class SkillCrud(BaseCrud):
    def __init__(self):
        super().__init__(Skill)

    async def get_by_name(self, db: AsyncSession, name: str) -> Skill | None:
        stmt = select(Skill).where(Skill.name == name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, db: AsyncSession, name: str) -> Skill:
        skill = await self.get_by_name(db, name)
        if not skill:
            skill = await self.create(db, {"name": name})
            await db.flush()
        return skill

skillcrud = SkillCrud()