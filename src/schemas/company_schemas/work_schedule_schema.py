from pydantic import BaseModel

class WorkScheduleBase(BaseModel):
    name: str

class WorkScheduleCreate(WorkScheduleBase):
    pass

class WorkScheduleResponse(WorkScheduleBase):
    id: int

    class Config:
        from_attributes = True