from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.models.base import LocationType, TimestampMixin


class Location(TimestampMixin, Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str | None] = mapped_column(String(100))
    very_short_name: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Numeric(10, 6, asdecimal=False))
    lng: Mapped[float | None] = mapped_column(Numeric(10, 6, asdecimal=False))
    emoji: Mapped[str | None] = mapped_column(String(10))
    alt_emoji: Mapped[str | None] = mapped_column(String(10))
    website_url: Mapped[str | None] = mapped_column(String(500))
    type: Mapped[LocationType] = mapped_column(
        Enum(LocationType, name="location_type"),
        server_default="venue",
    )

    # Relationships
    alternate_names: Mapped[list["LocationAlternateName"]] = relationship(
        back_populates="location"
    )
    tags: Mapped[list["Tag"]] = relationship(secondary="location_tags", viewonly=True)
    events: Mapped[list["Event"]] = relationship(back_populates="location")


class LocationAlternateName(Base):
    __tablename__ = "location_alternate_names"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE")
    )
    alternate_name: Mapped[str] = mapped_column(String(255))

    # Relationships
    location: Mapped["Location"] = relationship(back_populates="alternate_names")


class LocationTag(Base):
    __tablename__ = "location_tags"

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
