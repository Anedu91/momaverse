"""SQLAdmin ModelAdmin views for all Momaverse models."""

from sqladmin import ModelView

from api.models.crawl import CrawlResult, CrawlRun
from api.models.edit import Conflict, Edit
from api.models.event import Event, EventOccurrence, EventSource
from api.models.feedback import Feedback
from api.models.grantee import Grantee
from api.models.instagram import InstagramAccount
from api.models.location import Location
from api.models.tag import Tag, TagRule
from api.models.user import User
from api.models.website import Website


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class LocationAdmin(ModelView, model=Location):
    name = "Location"
    name_plural = "Locations"
    icon = "fa-solid fa-map-marker-alt"
    column_list = ["id", "name", "address", "lat", "lng", "emoji"]
    column_searchable_list = ["name"]


class WebsiteAdmin(ModelView, model=Website):
    name = "Website"
    name_plural = "Websites"
    icon = "fa-solid fa-globe"
    column_list = [
        "id",
        "name",
        "base_url",
        "crawl_frequency",
        "disabled",
        "last_crawled_at",
    ]
    column_searchable_list = ["name", "base_url"]


class EventAdmin(ModelView, model=Event):
    name = "Event"
    name_plural = "Events"
    icon = "fa-solid fa-calendar"
    column_list = [
        "id",
        "name",
        "emoji",
        "location_name",
        "archived",
        "suppressed",
    ]
    column_searchable_list = ["name"]


class TagAdmin(ModelView, model=Tag):
    name = "Tag"
    name_plural = "Tags"
    icon = "fa-solid fa-tag"
    column_list = ["id", "name"]
    column_searchable_list = ["name"]


# ---------------------------------------------------------------------------
# Crawl models
# ---------------------------------------------------------------------------


class CrawlRunAdmin(ModelView, model=CrawlRun):
    name = "Crawl Run"
    name_plural = "Crawl Runs"
    icon = "fa-solid fa-spider"
    column_list = ["id", "run_date", "status", "started_at", "completed_at"]


class CrawlResultAdmin(ModelView, model=CrawlResult):
    name = "Crawl Result"
    name_plural = "Crawl Results"
    icon = "fa-solid fa-file-lines"
    column_list = ["id", "website_id", "filename", "event_count", "status"]
    # Exclude large text fields from forms, detail views, and exports
    form_excluded_columns = ["crawled_content", "extracted_content"]
    column_details_exclude_list = ["crawled_content", "extracted_content"]
    column_export_exclude_list = ["crawled_content", "extracted_content"]


# ---------------------------------------------------------------------------
# System models
# ---------------------------------------------------------------------------


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-users"
    can_create = False
    column_list = ["id", "email", "display_name", "is_admin", "last_login_at"]
    # Never expose password_hash in forms or detail views
    form_excluded_columns = ["password_hash"]
    column_details_exclude_list = ["password_hash"]


class EditAdmin(ModelView, model=Edit):
    name = "Edit"
    name_plural = "Edits"
    icon = "fa-solid fa-pen"
    can_create = False
    can_edit = False
    can_delete = False
    column_list = [
        "id",
        "table_name",
        "record_id",
        "action",
        "source",
        "created_at",
    ]


class ConflictAdmin(ModelView, model=Conflict):
    name = "Conflict"
    name_plural = "Conflicts"
    icon = "fa-solid fa-triangle-exclamation"
    column_list = ["id", "table_name", "record_id", "status", "created_at"]


# ---------------------------------------------------------------------------
# Additional / secondary models
# ---------------------------------------------------------------------------


class TagRuleAdmin(ModelView, model=TagRule):
    name = "Tag Rule"
    name_plural = "Tag Rules"
    icon = "fa-solid fa-gavel"
    column_list = ["id", "rule_type", "pattern", "replacement"]


class GranteeAdmin(ModelView, model=Grantee):
    name = "Grantee"
    name_plural = "Grantees"
    icon = "fa-solid fa-hand-holding-dollar"
    column_list = ["id", "name", "area", "website_id"]


class InstagramAccountAdmin(ModelView, model=InstagramAccount):
    name = "Instagram Account"
    name_plural = "Instagram Accounts"
    icon = "fa-brands fa-instagram"
    column_list = ["id", "handle", "name", "description"]
    column_searchable_list = ["handle", "name"]


class FeedbackAdmin(ModelView, model=Feedback):
    name = "Feedback"
    name_plural = "Feedback"
    icon = "fa-solid fa-comment"
    can_create = False
    can_edit = False
    can_delete = False
    column_list = ["id", "message", "page_url", "created_at"]


class EventOccurrenceAdmin(ModelView, model=EventOccurrence):
    name = "Event Occurrence"
    name_plural = "Event Occurrences"
    icon = "fa-solid fa-clock"
    column_list = ["id", "event_id", "start_date", "start_time", "end_date", "end_time"]


class EventSourceAdmin(ModelView, model=EventSource):
    name = "Event Source"
    name_plural = "Event Sources"
    icon = "fa-solid fa-link"
    column_list = ["id", "event_id", "crawl_event_id", "is_primary", "created_at"]


# All view classes in registration order
ALL_VIEWS: list[type[ModelView]] = [
    LocationAdmin,
    WebsiteAdmin,
    EventAdmin,
    TagAdmin,
    CrawlRunAdmin,
    CrawlResultAdmin,
    UserAdmin,
    EditAdmin,
    ConflictAdmin,
    TagRuleAdmin,
    GranteeAdmin,
    InstagramAccountAdmin,
    FeedbackAdmin,
    EventOccurrenceAdmin,
    EventSourceAdmin,
]
