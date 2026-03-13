from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["FeedbackCreate", "FeedbackResponse"]


class FeedbackCreate(BaseModel):
    message: Annotated[str, Field(max_length=10_000)]
    page_url: Annotated[str | None, Field(max_length=500)] = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message: str
    user_agent: str | None = None
    page_url: str | None = None
    created_at: datetime
