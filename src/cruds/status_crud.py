from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import Status

class StatusCrud(BaseCrud):
    def __init__(self):
        super().__init__(Status)

    async def get_or_create(self, db: AsyncSession, name: str) -> Status:
        result = await db.execute(select(Status).where(Status.name == name))
        status = result.scalar_one_or_none()
        if not status:
            status = Status(name=name)
            db.add(status)
            await db.flush()
        return status

statuscrud = StatusCrud()