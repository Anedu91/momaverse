import enum
from datetime import datetime, timezone

from sqlalchemy import TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import ColumnElement

# ============================================================================
# PostgreSQL Enum Types (all pre-existing, create_type=False when used)
# ============================================================================


class SourceType(str, enum.Enum):
    primary = "primary"
    aggregator = "aggregator"


class CrawlMode(str, enum.Enum):
    browser = "browser"
    json_api = "json_api"


class CrawlRunStatus(str, enum.Enum):
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


class EditAction(str, enum.Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class EditSource(str, enum.Enum):
    local = "local"
    website = "website"
    crawl = "crawl"


class SyncSourceEnum(str, enum.Enum):
    local = "local"
    website = "website"


class ConflictStatus(str, enum.Enum):
    pending = "pending"
    resolved_local = "resolved_local"
    resolved_website = "resolved_website"
    resolved_merged = "resolved_merged"


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
