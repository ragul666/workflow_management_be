import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    tenant_id: uuid.UUID
    roles: List[str] = []
    permissions: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserRoleAssign(BaseModel):
    user_id: uuid.UUID
    role_name: str
