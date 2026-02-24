from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from src.cruds.company_cruds.company_crud import companycrud
from src.cruds.company_cruds.vacancy_crud import vacancycrud
from src.cruds.profession_crud import professioncrud
from src.cruds.company_cruds.employment_type_crud import employmenttypecrud
from src.cruds.company_cruds.work_schedule_crud import workschedulecrud
from src.cruds.skill_crud import skillcrud
from src.schemas.company_schemas.company_schema import CompanyUpdate
from src.schemas.company_schemas.vacancy_schema import VacancyCreate, VacancyUpdate
from src.schemas.skill_schema import SkillCreate
from src.models.model import Company

class CompanyService:
    def __init__(self):
        self.companycrud = companycrud
        self.vacancycrud = vacancycrud
        self.professioncrud = professioncrud
        self.employmenttypecrud = employmenttypecrud
        self.workschedulecrud = workschedulecrud
        self.skillcrud = skillcrud

    async def get_company_profile(self, db: AsyncSession, company: Company):
        await db.refresh(company, ["vacancies"])
        return company

    async def update_company_profile(self, db: AsyncSession, company: Company, update_data: CompanyUpdate):
        updated = await self.companycrud.update(db, company.id, update_data.model_dump(exclude_unset=True))
        await db.commit()
        return updated

    async def create_vacancy(self, db: AsyncSession, company_id: int, vacancy_data: VacancyCreate):
        vacancy_dict = vacancy_data.model_dump()
        vacancy_dict["company_id"] = company_id
        vacancy = await self.vacancycrud.create(db, vacancy_dict)
        await db.commit()
        await db.refresh(vacancy, ["profession", "employment_type", "work_schedule"])
        return vacancy

    async def get_company_vacancies(self, db: AsyncSession, company_id: int):
        return await self.vacancycrud.get_by_company(db, company_id)

    async def get_vacancy_detail(self, db: AsyncSession, vacancy_id: int, company_id: int):
        vacancy = await self.vacancycrud.get_with_details(db, vacancy_id)
        if not vacancy or vacancy.company_id != company_id:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        return vacancy

    async def update_vacancy(self, db: AsyncSession, vacancy_id: int, company_id: int, vacancy_data: VacancyUpdate):
        vacancy = await self.vacancycrud.get(db, vacancy_id)
        if not vacancy or vacancy.company_id != company_id:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        updated = await self.vacancycrud.update(db, vacancy_id, vacancy_data.model_dump(exclude_unset=True))
        await db.commit()
        return updated

    async def delete_vacancy(self, db: AsyncSession, vacancy_id: int, company_id: int):
        vacancy = await self.vacancycrud.get(db, vacancy_id)
        if not vacancy or vacancy.company_id != company_id:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        await self.vacancycrud.delete(db, vacancy_id)
        await db.commit()

    async def add_skill_to_vacancy(self, db: AsyncSession, vacancy_id: int, company_id: int, skill_name: str):
        vacancy = await self.vacancycrud.get_with_details(db, vacancy_id)
        if not vacancy or vacancy.company_id != company_id:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        skill = await self.skillcrud.get_or_create(db, skill_name)
        if skill not in vacancy.skills:
            vacancy.skills.append(skill)
            await db.commit()
            await db.refresh(vacancy, ["skills"])
        return vacancy

    async def remove_skill_from_vacancy(self, db: AsyncSession, vacancy_id: int, company_id: int, skill_id: int):
        vacancy = await self.vacancycrud.get_with_details(db, vacancy_id)
        if not vacancy or vacancy.company_id != company_id:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        skill = await self.skillcrud.get(db, skill_id)
        if skill and skill in vacancy.skills:
            vacancy.skills.remove(skill)
            await db.commit()
            await db.refresh(vacancy, ["skills"])
        return vacancy

company_service = CompanyService()