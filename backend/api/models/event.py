from datetime import date, datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500))
    short_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    emoji: Mapped[str | None] = mapped_column(String(10))
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL")
    )
    location_name: Mapped[str | None] = mapped_column(String(255))
    sublocation: Mapped[str | None] = mapped_column(String(255))
    website_id: Mapped[int | None] = mapped_column(
        ForeignKey("websites.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )
    archived: Mapped[bool] = mapped_column(Boolean, server_default="false")
    suppressed: Mapped[bool] = mapped_column(Boolean, server_default="false")
    reviewed: Mapped[bool] = mapped_column(Boolean, server_default="false")

    # Relationships
    location: Mapped["Location"] = relationship(back_populates="events")
    website: Mapped["Website"] = relationship(back_populates="events")
    occurrences: Mapped[list["EventOccurrence"]] = relationship(
        back_populates="event"
    )
    urls: Mapped[list["EventUrl"]] = relationship(back_populates="event")
    tags: Mapped[list["EventTag"]] = relationship(back_populates="event")
    sources: Mapped[list["EventSource"]] = relationship(back_populates="event")


class EventOccurrence(Base):
    __tablename__ = "event_occurrences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )
    start_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[str | None] = mapped_column(String(20))
    end_date: Mapped[date | None] = mapped_column(Date)
    end_time: Mapped[str | None] = mapped_column(String(20))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="occurrences")


class EventUrl(Base):
    __tablename__ = "event_urls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(String(2000))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="urls")


class EventTag(Base):
    __tablename__ = "event_tags"
    __table_args__ = (UniqueConstraint("event_id", "tag_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE")
    )

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()


class EventSource(Base):
    __tablename__ = "event_sources"
    __table_args__ = (UniqueConstraint("event_id", "crawl_event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )
    crawl_event_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_events.id", ondelete="CASCADE")
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="sources")
    crawl_event: Mapped["CrawlEvent"] = relationship(back_populates="event_sources")
