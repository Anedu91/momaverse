from api.database import Base
from api.models.base import CreatedAtMixin

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message: Mapped[str] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    page_url: Mapped[str | None] = mapped_column(String(500))
