from pydantic import BaseModel

class ProfessionBase(BaseModel):
    name: str

class ProfessionCreate(ProfessionBase):
    pass

class ProfessionResponse(ProfessionBase):
    id: int

    class Config:
        from_attributes = True