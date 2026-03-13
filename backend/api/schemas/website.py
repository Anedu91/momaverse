from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common import TagResponse
from api.schemas.location import LocationResponse

__all__ = [
    "WebsiteCreate",
    "WebsiteUpdate",
    "WebsiteResponse",
    "WebsiteListItem",
    "WebsiteUrlResponse",
    "WebsiteDetailResponse",
]


class WebsiteCreate(BaseModel):
    """Note: ``tags`` and ``location_ids`` are accepted here for convenience but
    the ORM relationships are ``viewonly=True``.  The service layer must
    manually create the join-table rows (``WebsiteTag`` / ``WebsiteLocation``)
    when processing these fields."""

    name: Annotated[str, Field(max_length=255)]
    description: str | None = None
    base_url: Annotated[str | None, Field(max_length=500)] = None
    max_pages: int = 30
    urls: list[Annotated[str, Field(max_length=2000)]] = []
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
    url: Annotated[str, Field(max_length=2000)]
    sort_order: int = 0


# Fields like crawl_frequency, selector, num_clicks, js_code, keywords,
# max_batches, notes, source_type, etc. are intentionally excluded from
# public schemas — they are admin/crawler internals and will be exposed
# through a separate admin schema if needed.
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


class WebsiteListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    base_url: str | None = None
    disabled: bool = False
    event_count: int = 0


class WebsiteDetailResponse(WebsiteResponse):
    urls: list[WebsiteUrlResponse] = []
    locations: list[LocationResponse] = []
    tags: list[TagResponse] = []
