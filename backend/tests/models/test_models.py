"""Test-only SQLAlchemy models that use the soft-delete mixin."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base
from api.models.base import SoftDeleteMixin, TimestampMixin


class SoftDeleteItem(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "test_soft_delete_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
