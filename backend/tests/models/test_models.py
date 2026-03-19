"""Test-only SQLAlchemy models that use the soft-delete and versioning mixins."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base
from api.models.base import (
    CreatedAtMixin,
    SoftDeleteMixin,
    TimestampMixin,
    VersionedMixin,
)


class SoftDeleteItem(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "test_soft_delete_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class VersionedItem(VersionedMixin, CreatedAtMixin, Base):
    __tablename__ = "test_versioned_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
