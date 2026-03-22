import enum
from datetime import datetime, timezone

from sqlalchemy import TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import ColumnElement

# ============================================================================
# PostgreSQL Enum Types
# ============================================================================


class SourceType(str, enum.Enum):
    crawler = "crawler"
    api = "api"
    user_submission = "user_submission"
    partner_feed = "partner_feed"


class CrawlMode(str, enum.Enum):
    browser = "browser"
    json_api = "json_api"


class CrawlJobStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class CrawlResultStatus(str, enum.Enum):
    pending = "pending"
    crawled = "crawled"
    extracted = "extracted"
    processed = "processed"
    failed = "failed"


class TagRuleType(str, enum.Enum):
    rewrite = "rewrite"
    exclude = "exclude"
    remove = "remove"


class ExtractedEventStatus(str, enum.Enum):
    created = "created"
    merged = "merged"
    skipped_no_location = "skipped_no_location"
    skipped_no_occurrences = "skipped_no_occurrences"
    skipped_duplicate = "skipped_duplicate"


class EventStatus(str, enum.Enum):
    active = "active"
    archived = "archived"
    draft = "draft"
    cancelled = "cancelled"


class LocationType(str, enum.Enum):
    venue = "venue"
    area = "area"
    meeting_point = "meeting_point"


# ============================================================================
# Mixins
# ============================================================================


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )


class SoftDeleteMixin:
    """Adds soft-delete capability via deleted_at timestamp.

    A record is considered deleted when deleted_at IS NOT NULL.
    Use .active() to filter queries to non-deleted records.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP, nullable=True, default=None
    )

    @classmethod
    def active(cls) -> ColumnElement[bool]:
        """Filter clause for non-deleted records.

        Usage: select(Model).where(Model.active())
        """
        return cls.deleted_at.is_(None)

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def restore(self) -> None:
        self.deleted_at = None
