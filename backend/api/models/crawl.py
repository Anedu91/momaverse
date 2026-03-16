from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CHAR,
    TIMESTAMP,
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.models.base import CrawlResultStatus, CrawlRunStatus


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_date: Mapped[date] = mapped_column(Date, unique=True)
    status: Mapped[CrawlRunStatus] = mapped_column(
        Enum(CrawlRunStatus, name="crawl_run_status"),
        server_default="running",
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    results: Mapped[list["CrawlResult"]] = relationship(back_populates="crawl_run")


class CrawlResult(Base):
    __tablename__ = "crawl_results"
    __table_args__ = (UniqueConstraint("crawl_run_id", "filename"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crawl_run_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_runs.id", ondelete="CASCADE")
    )
    website_id: Mapped[int | None] = mapped_column(
        ForeignKey("websites.id", ondelete="SET NULL")
    )
    filename: Mapped[str] = mapped_column(String(255))
    event_count: Mapped[int] = mapped_column(Integer, server_default="0")
    status: Mapped[CrawlResultStatus] = mapped_column(
        Enum(CrawlResultStatus, name="crawl_result_status"),
        server_default="pending",
    )
    crawled_content: Mapped[str | None] = mapped_column(Text)
    extracted_content: Mapped[str | None] = mapped_column(Text)
    crawled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    extracted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    processed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    # Relationships
    crawl_run: Mapped["CrawlRun"] = relationship(back_populates="results")
    website: Mapped["Website"] = relationship(back_populates="crawl_results")
    crawl_events: Mapped[list["CrawlEvent"]] = relationship(
        back_populates="crawl_result"
    )


class CrawlEvent(Base):
    __tablename__ = "crawl_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crawl_result_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_results.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(500))
    short_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    emoji: Mapped[str | None] = mapped_column(String(10))
    location_name: Mapped[str | None] = mapped_column(String(255))
    sublocation: Mapped[str | None] = mapped_column(String(255))
    location_id: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(String(2000))
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    content_hash: Mapped[str | None] = mapped_column(CHAR(64))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    # Relationships
    crawl_result: Mapped["CrawlResult"] = relationship(back_populates="crawl_events")
    occurrences: Mapped[list["CrawlEventOccurrence"]] = relationship(
        back_populates="crawl_event"
    )
    tags: Mapped[list["CrawlEventTag"]] = relationship(back_populates="crawl_event")
    event_sources: Mapped[list["EventSource"]] = relationship(
        back_populates="crawl_event"
    )


class CrawlEventOccurrence(Base):
    __tablename__ = "crawl_event_occurrences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crawl_event_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_events.id", ondelete="CASCADE")
    )
    start_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[str | None] = mapped_column(String(20))
    end_date: Mapped[date | None] = mapped_column(Date)
    end_time: Mapped[str | None] = mapped_column(String(20))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")

    # Relationships
    crawl_event: Mapped["CrawlEvent"] = relationship(back_populates="occurrences")


class CrawlEventTag(Base):
    __tablename__ = "crawl_event_tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crawl_event_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_events.id", ondelete="CASCADE")
    )
    tag: Mapped[str] = mapped_column(String(100))

    # Relationships
    crawl_event: Mapped["CrawlEvent"] = relationship(back_populates="tags")
