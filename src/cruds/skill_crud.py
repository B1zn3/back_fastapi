from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import Skill

class SkillCrud(BaseCrud):
    def __init__(self):
        super().__init__(Skill)

    async def get_or_create(self, db: AsyncSession, name: str) -> Skill:
        result = await db.execute(select(Skill).where(Skill.name == name))
        skill = result.scalar_one_or_none()
        if not skill:
            skill = Skill(name=name)
            db.add(skill)
            await db.flush()
        return skill
    
    async def get_or_create_many(self, db: AsyncSession, names: List[str]) -> Dict[str, Skill]:
        """Получает или создаёт несколько навыков за один раз."""
        unique_names = list(set(names))  # убираем дубликаты
        # Ищем существующие
        stmt = select(Skill).where(Skill.name.in_(unique_names))
        result = await db.execute(stmt)
        existing = {s.name: s for s in result.scalars().all()}
        # Создаём недостающие
        to_create = [name for name in unique_names if name not in existing]
        if to_create:
            new_skills = [Skill(name=name) for name in to_create]
            db.add_all(new_skills)
            await db.flush()
            for skill in new_skills:
                existing[skill.name] = skill

        return existing

skillcrud = SkillCrud()