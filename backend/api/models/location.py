from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str | None] = mapped_column(String(100))
    very_short_name: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Numeric(10, 6))
    lng: Mapped[float | None] = mapped_column(Numeric(10, 6))
    emoji: Mapped[str | None] = mapped_column(String(10))
    alt_emoji: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    # Relationships
    alternate_names: Mapped[list["LocationAlternateName"]] = relationship(
        back_populates="location"
    )
    tags: Mapped[list["LocationTag"]] = relationship(back_populates="location")
    instagram_accounts: Mapped[list["InstagramAccount"]] = relationship(
        secondary="location_instagram", back_populates="locations"
    )
    events: Mapped[list["Event"]] = relationship(back_populates="location")
    website_locations: Mapped[list["WebsiteLocation"]] = relationship(
        back_populates="location"
    )


class LocationAlternateName(Base):
    __tablename__ = "location_alternate_names"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE")
    )
    alternate_name: Mapped[str] = mapped_column(String(255))
    website_id: Mapped[int | None] = mapped_column(
        ForeignKey("websites.id", ondelete="CASCADE")
    )

    # Relationships
    location: Mapped["Location"] = relationship(back_populates="alternate_names")
    website: Mapped["Website"] = relationship()


class LocationTag(Base):
    __tablename__ = "location_tags"
    __table_args__ = (UniqueConstraint("location_id", "tag_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE")
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE")
    )

    # Relationships
    location: Mapped["Location"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()


class LocationInstagram(Base):
    __tablename__ = "location_instagram"

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True
    )
    instagram_id: Mapped[int] = mapped_column(
        ForeignKey("instagram_accounts.id", ondelete="CASCADE"), primary_key=True
    )
