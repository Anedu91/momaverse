from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common import TagResponse

__all__ = [
    "OccurrenceSchema",
    "OccurrenceResponse",
    "EventCreate",
    "EventUpdate",
    "EventResponse",
    "EventListItem",
    "EventUrlResponse",
    "EventDetailResponse",
]


class OccurrenceSchema(BaseModel):
    start_date: date
    start_time: Annotated[str | None, Field(max_length=20)] = None
    end_date: date | None = None
    end_time: Annotated[str | None, Field(max_length=20)] = None


class OccurrenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_date: date
    start_time: str | None = None
    end_date: date | None = None
    end_time: str | None = None


class EventCreate(BaseModel):
    name: Annotated[str, Field(max_length=500)]
    short_name: Annotated[str | None, Field(max_length=255)] = None
    description: str | None = None
    emoji: Annotated[str | None, Field(max_length=10)] = None
    location_id: int
    sublocation: Annotated[str | None, Field(max_length=255)] = None
    occurrences: list[OccurrenceSchema] = []
    urls: list[Annotated[str, Field(max_length=2000)]] = []
    tags: list[str] = []


class EventUpdate(BaseModel):
    name: Annotated[str | None, Field(max_length=500)] = None
    short_name: Annotated[str | None, Field(max_length=255)] = None
    description: str | None = None
    emoji: Annotated[str | None, Field(max_length=10)] = None
    location_id: int | None = None
    sublocation: Annotated[str | None, Field(max_length=255)] = None
    status: str | None = None
    reviewed: bool | None = None
    occurrences: list[OccurrenceSchema] | None = None
    urls: list[Annotated[str, Field(max_length=2000)]] | None = None
    tags: list[str] | None = None


class EventUrlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: Annotated[str, Field(max_length=2000)]


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str | None = None
    description: str | None = None
    emoji: str | None = None
    location_id: int
    sublocation: str | None = None
    status: str = "active"
    reviewed: bool = False
    created_at: datetime
    updated_at: datetime


class EventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str | None = None
    emoji: str | None = None
    location_id: int
    location_display_name: str | None = None
    status: str = "active"
    next_date: date | None = None


class EventDetailResponse(EventResponse):
    occurrences: list[OccurrenceResponse] = []
    urls: list[EventUrlResponse] = []
    tags: list[TagResponse] = []
