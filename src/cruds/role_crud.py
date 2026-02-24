from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import Role

class RoleCrud(BaseCrud):
    def __init__(self):
        super().__init__(Role)

    async def get_by_name(self, db: AsyncSession, name: str) -> Role | None:
        result = await db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

rolecrud = RoleCrud()