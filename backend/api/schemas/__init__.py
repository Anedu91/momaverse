from api.schemas.auth import AuthResponse
from api.schemas.common import PaginatedResponse, TagResponse
from api.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventListItem,
    EventResponse,
    EventUpdate,
    EventUrlResponse,
    OccurrenceResponse,
    OccurrenceSchema,
)
from api.schemas.location import (
    AlternateNameResponse,
    LocationCreate,
    LocationDetailResponse,
    LocationListItem,
    LocationResponse,
    LocationUpdate,
)
from api.schemas.user import UserCreate, UserLogin, UserResponse

__all__ = [
    # Common
    "PaginatedResponse",
    "TagResponse",
    # Location
    "AlternateNameResponse",
    "LocationCreate",
    "LocationDetailResponse",
    "LocationListItem",
    "LocationResponse",
    "LocationUpdate",
    # Event
    "EventCreate",
    "EventDetailResponse",
    "EventListItem",
    "EventResponse",
    "EventUpdate",
    "EventUrlResponse",
    "OccurrenceResponse",
    "OccurrenceSchema",
    # Auth
    "AuthResponse",
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
]
