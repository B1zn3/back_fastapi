from pydantic import BaseModel, EmailStr
from typing import Optional

from src.schemas.profile_schema import ProfileResponse

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str 
    is_active: bool
    profile: ProfileResponse

    class Config:
        from_attributes = True