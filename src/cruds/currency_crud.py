from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.cruds.base_crud import BaseCrud
from src.models.model import Currency

class CurrencyCrud(BaseCrud):
    def __init__(self):
        super().__init__(Currency)

    async def get_or_create(self, db: AsyncSession, name: str) -> Currency:
        result = await db.execute(select(Currency).where(Currency.name == name))
        currency = result.scalar_one_or_none()
        if not currency:
            currency = Currency(name=name)
            db.add(currency)
            await db.flush()
        return currency

currencycrud = CurrencyCrud()