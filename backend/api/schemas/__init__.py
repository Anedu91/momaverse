from api.schemas.auth import AuthResponse
from api.schemas.common import PaginatedResponse, TagResponse
from api.schemas.edit import EditResponse
from api.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
    EventUrlResponse,
    OccurrenceResponse,
    OccurrenceSchema,
)
from api.schemas.feedback import FeedbackCreate, FeedbackResponse
from api.schemas.location import (
    AlternateNameResponse,
    LocationCreate,
    LocationDetailResponse,
    LocationResponse,
    LocationUpdate,
)
from api.schemas.sync import SyncEdit, SyncEditsRequest, SyncStatusResponse
from api.schemas.user import UserCreate, UserLogin, UserResponse
from api.schemas.website import (
    WebsiteCreate,
    WebsiteDetailResponse,
    WebsiteResponse,
    WebsiteUpdate,
    WebsiteUrlResponse,
)

__all__ = [
    # Common
    "PaginatedResponse",
    "TagResponse",
    # Location
    "AlternateNameResponse",
    "LocationCreate",
    "LocationDetailResponse",
    "LocationResponse",
    "LocationUpdate",
    # Event
    "EventCreate",
    "EventDetailResponse",
    "EventResponse",
    "EventUpdate",
    "EventUrlResponse",
    "OccurrenceResponse",
    "OccurrenceSchema",
    # Website
    "WebsiteCreate",
    "WebsiteDetailResponse",
    "WebsiteResponse",
    "WebsiteUpdate",
    "WebsiteUrlResponse",
    # Auth
    "AuthResponse",
    # Feedback
    "FeedbackCreate",
    "FeedbackResponse",
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
    # Edit
    "EditResponse",
    # Sync
    "SyncEdit",
    "SyncEditsRequest",
    "SyncStatusResponse",
]
