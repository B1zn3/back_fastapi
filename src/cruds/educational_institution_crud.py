from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import EducationalInstitution

class EducationalInstitutionCrud(BaseCrud):
    def __init__(self):
        super().__init__(EducationalInstitution)

    async def get_or_create(self, db: AsyncSession, name: str) -> EducationalInstitution:
        result = await db.execute(select(EducationalInstitution).where(EducationalInstitution.name == name))
        inst = result.scalar_one_or_none()
        if not inst:
            inst = EducationalInstitution(name=name)
            db.add(inst)
            await db.flush()
        return inst

educationalinstitutioncrud = EducationalInstitutionCrud()