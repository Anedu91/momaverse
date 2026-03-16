from __future__ import annotations

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base
from api.models.base import CreatedAtMixin, TagRuleType


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class TagRule(CreatedAtMixin, Base):
    __tablename__ = "tag_rules"
    __table_args__ = (UniqueConstraint("rule_type", "pattern"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_type: Mapped[TagRuleType] = mapped_column(
        Enum(TagRuleType, name="tag_rule_type")
    )
    pattern: Mapped[str] = mapped_column(String(100))
    replacement: Mapped[str | None] = mapped_column(String(100))
