from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cruds.base_crud import BaseCrud
from src.models.model import ResumeChange


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ResumeChangeCrud(BaseCrud):
    def __init__(self):
        super().__init__(ResumeChange)

    async def create_for_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        changed_at: datetime | None = None,
    ) -> ResumeChange:
        item = ResumeChange(
            resume_id=resume_id,
            changed_at=changed_at or utc_now_naive(),
        )

        db.add(item)
        await db.flush()

        return item

    async def get_by_resume(
        self,
        db: AsyncSession,
        resume_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ResumeChange]:
        stmt = (
            select(ResumeChange)
            .where(ResumeChange.resume_id == resume_id)
            .order_by(ResumeChange.changed_at.desc(), ResumeChange.id.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())


resumechangecrud = ResumeChangeCrud()