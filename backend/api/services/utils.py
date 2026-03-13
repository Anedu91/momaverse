from typing import Any

from fastapi import Request
from sqlalchemy import inspect as sa_inspect


def snapshot_record(record: Any) -> dict[str, object]:
    """Extract loggable scalar fields from a SQLAlchemy model instance."""
    return {
        c.key: getattr(record, c.key) for c in sa_inspect(record).mapper.column_attrs
    }


def extract_editor_context(request: Request) -> tuple[str | None, str | None]:
    """Extract editor IP and user-agent from the request."""
    editor_ip = request.client.host if request.client else None
    raw_ua = request.headers.get("user-agent")
    editor_user_agent = raw_ua[:500] if raw_ua else None
    return editor_ip, editor_user_agent
