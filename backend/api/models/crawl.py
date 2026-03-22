from datetime import datetime
from typing import Any

from sqlalchemy import (
    TIMESTAMP,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.models.base import CrawlJobStatus, CrawlResultStatus, ExtractedEventStatus


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[CrawlJobStatus] = mapped_column(
        Enum(CrawlJobStatus, name="crawl_job_status"),
        server_default="running",
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)

    # Relationships
    results: Mapped[list["CrawlResult"]] = relationship(back_populates="crawl_job")


class CrawlResult(Base):
    __tablename__ = "crawl_results"
    __table_args__ = (UniqueConstraint("crawl_job_id", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crawl_job_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_jobs.id", ondelete="CASCADE")
    )
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    status: Mapped[CrawlResultStatus] = mapped_column(
        Enum(CrawlResultStatus, name="crawl_result_status"),
        server_default="pending",
    )
    crawled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    extracted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    processed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    # Relationships
    crawl_job: Mapped["CrawlJob"] = relationship(back_populates="results")
    source: Mapped["Source"] = relationship(back_populates="crawl_results")
    extracted_events: Mapped[list["ExtractedEvent"]] = relationship(
        back_populates="crawl_result"
    )
    content: Mapped["CrawlContent | None"] = relationship(
        back_populates="crawl_result", uselist=False
    )


class CrawlContent(Base):
    __tablename__ = "crawl_contents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crawl_result_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_results.id", ondelete="CASCADE"), unique=True
    )
    crawled_content: Mapped[str | None] = mapped_column(Text)
    extracted_content: Mapped[str | None] = mapped_column(Text)

    # Relationships
    crawl_result: Mapped["CrawlResult"] = relationship(back_populates="content")


class ExtractedEvent(Base):
    __tablename__ = "extracted_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crawl_result_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_results.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(500))
    short_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    emoji: Mapped[str | None] = mapped_column(String(10))
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL")
    )
    location_name: Mapped[str | None] = mapped_column(String(255))
    sublocation: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(2000))
    occurrences: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    # Relationships
    crawl_result: Mapped["CrawlResult"] = relationship(
        back_populates="extracted_events"
    )
    location: Mapped["Location"] = relationship()
    event_sources: Mapped[list["EventSource"]] = relationship(
        back_populates="extracted_event"
    )
    logs: Mapped[list["ExtractedEventLog"]] = relationship(
        back_populates="extracted_event"
    )


class ExtractedEventLog(Base):
    __tablename__ = "extracted_event_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    extracted_event_id: Mapped[int] = mapped_column(
        ForeignKey("extracted_events.id", ondelete="CASCADE")
    )
    status: Mapped[ExtractedEventStatus] = mapped_column(
        Enum(ExtractedEventStatus, name="extracted_event_status")
    )
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL")
    )
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    # Relationships
    extracted_event: Mapped["ExtractedEvent"] = relationship(back_populates="logs")
    event: Mapped["Event | None"] = relationship()
