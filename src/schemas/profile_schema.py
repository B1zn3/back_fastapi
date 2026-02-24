from pydantic import BaseModel
from typing import Optional

class ProfileBase(BaseModel):
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    company_id: Optional[int] = None
    applicant_id: Optional[int] = None

    class Config:
        from_attributes = True