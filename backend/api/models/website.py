from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.models.base import CrawlMode, SourceType, TimestampMixin


class Website(TimestampMixin, Base):
    __tablename__ = "websites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    base_url: Mapped[str | None] = mapped_column(String(500))
    crawl_frequency: Mapped[int | None] = mapped_column(Integer)
    selector: Mapped[str | None] = mapped_column(String(500))
    num_clicks: Mapped[int | None] = mapped_column(Integer)
    js_code: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[str | None] = mapped_column(String(255))
    max_pages: Mapped[int | None] = mapped_column(Integer, server_default="30")
    max_batches: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    disabled: Mapped[bool] = mapped_column(Boolean, server_default="false")
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type"),
        server_default="primary",
    )
    crawl_after: Mapped[date | None] = mapped_column(Date)
    force_crawl: Mapped[bool] = mapped_column(Boolean, server_default="false")
    last_crawled_at: Mapped[datetime | None] = mapped_column()
    delay_before_return_html: Mapped[int | None] = mapped_column(Integer)
    content_filter_threshold: Mapped[float | None] = mapped_column(
        Numeric(3, 2, asdecimal=False)
    )
    scan_full_page: Mapped[bool | None] = mapped_column(Boolean)
    remove_overlay_elements: Mapped[bool | None] = mapped_column(Boolean)
    javascript_enabled: Mapped[bool | None] = mapped_column(Boolean)
    text_mode: Mapped[bool | None] = mapped_column(Boolean)
    light_mode: Mapped[bool | None] = mapped_column(Boolean)
    use_stealth: Mapped[bool | None] = mapped_column(Boolean)
    scroll_delay: Mapped[float | None] = mapped_column(Numeric(3, 2, asdecimal=False))
    crawl_timeout: Mapped[int | None] = mapped_column(Integer)
    crawl_frequency_locked: Mapped[bool] = mapped_column(
        Boolean, server_default="false"
    )
    process_images: Mapped[bool | None] = mapped_column(Boolean)
    crawl_mode: Mapped[CrawlMode] = mapped_column(
        Enum(CrawlMode, name="crawl_mode"),
        server_default="browser",
    )
    json_api_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Relationships
    urls: Mapped[list["WebsiteUrl"]] = relationship(back_populates="website")
    locations: Mapped[list["Location"]] = relationship(
        secondary="website_locations", viewonly=True
    )
    tags: Mapped[list["Tag"]] = relationship(secondary="website_tags", viewonly=True)
    instagram_accounts: Mapped[list["InstagramAccount"]] = relationship(
        secondary="website_instagram", back_populates="websites"
    )
    events: Mapped[list["Event"]] = relationship(back_populates="website")
    crawl_results: Mapped[list["CrawlResult"]] = relationship(back_populates="website")
    grantees: Mapped[list["Grantee"]] = relationship(back_populates="website")


class WebsiteUrl(Base):
    __tablename__ = "website_urls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    website_id: Mapped[int] = mapped_column(
        ForeignKey("websites.id", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(String(2000))
    js_code: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")

    # Relationships
    website: Mapped["Website"] = relationship(back_populates="urls")


class WebsiteLocation(Base):
    __tablename__ = "website_locations"
    __table_args__ = (UniqueConstraint("website_id", "location_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    website_id: Mapped[int] = mapped_column(
        ForeignKey("websites.id", ondelete="CASCADE")
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE")
    )

    # Relationships
    website: Mapped["Website"] = relationship(viewonly=True)
    location: Mapped["Location"] = relationship(viewonly=True)


class WebsiteTag(Base):
    __tablename__ = "website_tags"
    __table_args__ = (UniqueConstraint("website_id", "tag_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    website_id: Mapped[int] = mapped_column(
        ForeignKey("websites.id", ondelete="CASCADE")
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"))


class WebsiteInstagram(Base):
    __tablename__ = "website_instagram"

    website_id: Mapped[int] = mapped_column(
        ForeignKey("websites.id", ondelete="CASCADE"), primary_key=True
    )
    instagram_id: Mapped[int] = mapped_column(
        ForeignKey("instagram_accounts.id", ondelete="CASCADE"), primary_key=True
    )
