from datetime import date, datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.models.base import EventStatus, TimestampMixin


class Event(TimestampMixin, Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500))
    short_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    emoji: Mapped[str | None] = mapped_column(String(10))
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT")
    )
    sublocation: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status"),
        server_default="active",
    )
    reviewed: Mapped[bool] = mapped_column(Boolean, server_default="false")

    # Relationships
    location: Mapped["Location"] = relationship(back_populates="events")
    occurrences: Mapped[list["EventOccurrence"]] = relationship(back_populates="event")
    urls: Mapped[list["EventUrl"]] = relationship(back_populates="event")
    tags: Mapped[list["Tag"]] = relationship(secondary="event_tags", viewonly=True)
    sources: Mapped[list["EventSource"]] = relationship(back_populates="event")


class EventOccurrence(Base):
    __tablename__ = "event_occurrences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    start_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[str | None] = mapped_column(String(20))
    end_date: Mapped[date | None] = mapped_column(Date)
    end_time: Mapped[str | None] = mapped_column(String(20))

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="occurrences")


class EventUrl(Base):
    __tablename__ = "event_urls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(2000))

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="urls")


class EventTag(Base):
    __tablename__ = "event_tags"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )


class EventSource(Base):
    __tablename__ = "event_sources"
    __table_args__ = (UniqueConstraint("event_id", "extracted_event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    extracted_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("extracted_events.id", ondelete="CASCADE")
    )
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    trust_score: Mapped[float | None] = mapped_column(Numeric(2, 1, asdecimal=False))
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="sources")
    extracted_event: Mapped["ExtractedEvent"] = relationship(
        back_populates="event_sources"
    )
