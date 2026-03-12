from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common import TagResponse

__all__ = [
    "LocationCreate",
    "LocationUpdate",
    "LocationResponse",
    "AlternateNameResponse",
    "LocationDetailResponse",
]


class LocationCreate(BaseModel):
    name: Annotated[str, Field(max_length=255)]
    short_name: Annotated[str | None, Field(max_length=100)] = None
    very_short_name: Annotated[str | None, Field(max_length=50)] = None
    address: Annotated[str | None, Field(max_length=500)] = None
    description: str | None = None
    lat: Annotated[float | None, Field(ge=-90, le=90)] = None
    lng: Annotated[float | None, Field(ge=-180, le=180)] = None
    emoji: Annotated[str | None, Field(max_length=10)] = None
    alt_emoji: Annotated[str | None, Field(max_length=10)] = None
    alternate_names: list[str] = []
    tags: list[str] = []


class LocationUpdate(BaseModel):
    name: Annotated[str | None, Field(max_length=255)] = None
    short_name: Annotated[str | None, Field(max_length=100)] = None
    very_short_name: Annotated[str | None, Field(max_length=50)] = None
    address: Annotated[str | None, Field(max_length=500)] = None
    description: str | None = None
    lat: Annotated[float | None, Field(ge=-90, le=90)] = None
    lng: Annotated[float | None, Field(ge=-180, le=180)] = None
    emoji: Annotated[str | None, Field(max_length=10)] = None
    alt_emoji: Annotated[str | None, Field(max_length=10)] = None
    alternate_names: list[str] | None = None
    tags: list[str] | None = None


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str | None = None
    very_short_name: str | None = None
    address: str | None = None
    description: str | None = None
    lat: float | None = None
    lng: float | None = None
    emoji: str | None = None
    alt_emoji: str | None = None
    created_at: datetime
    updated_at: datetime


class AlternateNameResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alternate_name: str
    website_id: int | None = None


class LocationDetailResponse(LocationResponse):
    alternate_names: list[AlternateNameResponse] = []
    tags: list[TagResponse] = []
