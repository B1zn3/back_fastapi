from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import WorkSchedule

class WorkScheduleCrud(BaseCrud):
    def __init__(self):
        super().__init__(WorkSchedule)

    async def get_by_name(self, db: AsyncSession, name: str) -> WorkSchedule | None:
        stmt = select(WorkSchedule).where(WorkSchedule.name == name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

workschedulecrud = WorkScheduleCrud()