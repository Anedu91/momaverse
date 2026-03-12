from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)

    # Relationships
    edits: Mapped[list["Edit"]] = relationship(back_populates="user")
    resolved_conflicts: Mapped[list["Conflict"]] = relationship(
        back_populates="resolved_by_user"
    )
