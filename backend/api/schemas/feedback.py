from typing import Annotated

from pydantic import BaseModel, Field

__all__ = ["FeedbackCreate"]


class FeedbackCreate(BaseModel):
    message: Annotated[str, Field(max_length=10_000)]
    page_url: Annotated[str | None, Field(max_length=500)] = None
