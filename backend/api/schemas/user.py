from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field

__all__ = ["UserCreate", "UserLogin", "UserResponse"]


class UserCreate(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8)]
    display_name: Annotated[str | None, Field(max_length=100)] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str | None = None
    is_admin: bool = False
    created_at: datetime
