import enum
from datetime import datetime

from sqlalchemy import TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column


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
