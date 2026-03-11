from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.models.base import TimestampMixin


class InstagramAccount(TimestampMixin, Base):
    __tablename__ = "instagram_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    handle: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(500))

    # Relationships (via M2M through tables)
    locations: Mapped[list[Location]] = relationship(
        secondary="location_instagram", back_populates="instagram_accounts"
    )
    websites: Mapped[list[Website]] = relationship(
        secondary="website_instagram", back_populates="instagram_accounts"
    )
