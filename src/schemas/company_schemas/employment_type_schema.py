from pydantic import BaseModel

class EmploymentTypeBase(BaseModel):
    name: str

class EmploymentTypeCreate(EmploymentTypeBase):
    pass

class EmploymentTypeResponse(EmploymentTypeBase):
    id: int

    class Config:
        from_attributes = True