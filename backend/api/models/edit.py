from datetime import datetime

from sqlalchemy import (
    CHAR,
    TIMESTAMP,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.models.base import ConflictStatus, EditAction, EditSource, SyncSourceEnum


class Edit(Base):
    __tablename__ = "edits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edit_uuid: Mapped[str] = mapped_column(CHAR(36), unique=True)
    table_name: Mapped[str] = mapped_column(String(50))
    record_id: Mapped[int] = mapped_column(Integer)
    field_name: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[EditAction] = mapped_column(Enum(EditAction, name="edit_action"))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    source: Mapped[EditSource] = mapped_column(Enum(EditSource, name="edit_source"))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    editor_ip: Mapped[str | None] = mapped_column(String(45))
    editor_user_agent: Mapped[str | None] = mapped_column(String(500))
    editor_info: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )
    applied_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="edits")


class SyncState(Base):
    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[SyncSourceEnum] = mapped_column(
        Enum(SyncSourceEnum, name="sync_source"), unique=True
    )
    last_synced_edit_id: Mapped[int | None] = mapped_column(Integer)
    last_sync_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)


class Conflict(Base):
    __tablename__ = "conflicts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    local_edit_id: Mapped[int] = mapped_column(
        ForeignKey("edits.id", ondelete="CASCADE")
    )
    website_edit_id: Mapped[int] = mapped_column(
        ForeignKey("edits.id", ondelete="CASCADE")
    )
    table_name: Mapped[str] = mapped_column(String(50))
    record_id: Mapped[int] = mapped_column(Integer)
    field_name: Mapped[str | None] = mapped_column(String(100))
    local_value: Mapped[str | None] = mapped_column(Text)
    website_value: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ConflictStatus] = mapped_column(
        Enum(ConflictStatus, name="conflict_status"),
        server_default="pending",
    )
    resolved_value: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )

    # Relationships
    local_edit: Mapped["Edit"] = relationship(foreign_keys=[local_edit_id])
    website_edit: Mapped["Edit"] = relationship(foreign_keys=[website_edit_id])
    resolved_by_user: Mapped["User"] = relationship(
        foreign_keys=[resolved_by],
        back_populates="resolved_conflicts",
    )
