from api.schemas.auth import AuthResponse
from api.schemas.common import PaginatedResponse, TagResponse
from api.schemas.crawl import (
    CrawlContentResponse,
    CrawlJobDetailResponse,
    CrawlJobListItem,
    CrawlJobResponse,
    CrawlResultDetailResponse,
    CrawlResultResponse,
    ExtractedEventListItem,
    ExtractedEventResponse,
)
from api.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventListItem,
    EventResponse,
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
from api.schemas.source import (
    CrawlConfigCreate,
    CrawlConfigResponse,
    CrawlConfigUpdate,
    SourceCreate,
    SourceDetailResponse,
    SourceListItem,
    SourceResponse,
    SourceUpdate,
    SourceUrlCreate,
    SourceUrlResponse,
)
from api.schemas.tag_rule import TagRuleCreate, TagRuleResponse, TagRuleUpdate
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
    "EventUrlResponse",
    "OccurrenceResponse",
    "OccurrenceSchema",
    # Source
    "CrawlConfigCreate",
    "CrawlConfigResponse",
    "CrawlConfigUpdate",
    "SourceCreate",
    "SourceDetailResponse",
    "SourceListItem",
    "SourceResponse",
    "SourceUpdate",
    "SourceUrlCreate",
    "SourceUrlResponse",
    # Crawl
    "CrawlContentResponse",
    "CrawlJobDetailResponse",
    "CrawlJobListItem",
    "CrawlJobResponse",
    "CrawlResultDetailResponse",
    "CrawlResultResponse",
    "ExtractedEventListItem",
    "ExtractedEventResponse",
    # TagRule
    "TagRuleCreate",
    "TagRuleResponse",
    "TagRuleUpdate",
    # Auth
    "AuthResponse",
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
]
