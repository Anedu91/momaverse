from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common import TagResponse
from api.schemas.location import LocationResponse

__all__ = [
    "WebsiteCreate",
    "WebsiteUpdate",
    "WebsiteResponse",
    "WebsiteUrlResponse",
    "WebsiteDetailResponse",
]


class WebsiteCreate(BaseModel):
    name: Annotated[str, Field(max_length=255)]
    description: str | None = None
    base_url: Annotated[str | None, Field(max_length=500)] = None
    max_pages: int = 30
    urls: list[str] = []
    location_ids: list[int] = []
    tags: list[str] = []


class WebsiteUpdate(BaseModel):
    name: Annotated[str | None, Field(max_length=255)] = None
    description: str | None = None
    base_url: Annotated[str | None, Field(max_length=500)] = None
    max_pages: int | None = None
    disabled: bool | None = None
    urls: list[str] | None = None
    location_ids: list[int] | None = None
    tags: list[str] | None = None


class WebsiteUrlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    sort_order: int = 0


class WebsiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    base_url: str | None = None
    max_pages: int | None = None
    disabled: bool = False
    created_at: datetime
    updated_at: datetime


class WebsiteDetailResponse(WebsiteResponse):
    urls: list[WebsiteUrlResponse] = []
    locations: list[LocationResponse] = []
    tags: list[TagResponse] = []
