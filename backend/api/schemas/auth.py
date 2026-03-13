from pydantic import BaseModel

from api.schemas.user import UserResponse

__all__ = ["AuthResponse"]


class AuthResponse(BaseModel):
    token: str
    user: UserResponse
