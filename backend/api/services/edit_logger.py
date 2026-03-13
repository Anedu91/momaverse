"""
Edit Logger Service

Logs all changes to core tables for sync and audit purposes.
Each edit is stored as an immutable log entry with a UUID for global uniqueness.

# TODO: This service mirrors the PHP EditLogger
# (src/api/edit_logger.php) to maintain feature parity during
# the PHP-to-Python migration. The PHP version uses raw PDO
# queries and session-based user context; this version uses
# async SQLAlchemy with explicit context.
#
# TODO: Investigate replacing this manual logging approach with
# SQLAlchemy ORM events (e.g., `after_insert`, `after_update`,
# `after_delete` listeners) once the migration is verified and
# stable. ORM events would reduce boilerplate in routers and
# ensure logging can't be accidentally skipped.
# Key concerns to evaluate:
#   - Performance impact of event listeners on bulk ops
#   - Ability to capture user context (user_id, ip,
#     user_agent) without thread-local state
#   - Testability: mocking/disabling listeners in tests
#   - Whether ORM events fire correctly with async sessions
"""

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import EditAction, EditSource
from api.models.edit import Edit

TRACKED_TABLES: frozenset[str] = frozenset(
    [
        "locations",
        "location_alternate_names",
        "location_tags",
        "websites",
        "website_urls",
        "website_locations",
        "website_tags",
        "events",
        "event_occurrences",
        "event_urls",
        "event_tags",
        "tags",
        "tag_rules",
    ]
)


def _serialize_value(value: Any) -> str | None:
    """Serialize a value for storage in the edits table."""
    if value is None:
        return None
    if isinstance(value, dict | list):
        return json.dumps(value, default=str)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


async def _insert_edit(
    db: AsyncSession,
    *,
    table_name: str,
    record_id: int,
    field_name: str | None,
    action: EditAction,
    old_value: Any,
    new_value: Any,
    source: EditSource,
    user_id: int | None,
    editor_ip: str | None,
    editor_user_agent: str | None,
    editor_info: str | None = None,
) -> Edit:
    """Create and flush a single edit record."""
    edit = Edit(
        edit_uuid=str(uuid.uuid4()),
        table_name=table_name,
        record_id=record_id,
        field_name=field_name,
        action=action,
        old_value=_serialize_value(old_value),
        new_value=_serialize_value(new_value),
        source=source,
        user_id=user_id,
        editor_ip=editor_ip,
        editor_user_agent=(editor_user_agent[:500] if editor_user_agent else None),
        editor_info=editor_info,
    )
    db.add(edit)
    await db.flush()
    return edit


async def log_insert(
    db: AsyncSession,
    *,
    table_name: str,
    record_id: int,
    record_data: dict[str, Any],
    source: EditSource = EditSource.local,
    user_id: int | None = None,
    editor_ip: str | None = None,
    editor_user_agent: str | None = None,
) -> Edit | None:
    """Log an INSERT operation. Returns the Edit or None if untracked."""
    if table_name not in TRACKED_TABLES:
        return None

    return await _insert_edit(
        db,
        table_name=table_name,
        record_id=record_id,
        field_name=None,
        action=EditAction.INSERT,
        old_value=None,
        new_value=record_data,
        source=source,
        user_id=user_id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )


async def log_update(
    db: AsyncSession,
    *,
    table_name: str,
    record_id: int,
    field_name: str,
    old_value: Any,
    new_value: Any,
    source: EditSource = EditSource.local,
    user_id: int | None = None,
    editor_ip: str | None = None,
    editor_user_agent: str | None = None,
) -> Edit | None:
    """Log an UPDATE for a single field. Skips if value didn't change."""
    if table_name not in TRACKED_TABLES:
        return None

    if _serialize_value(old_value) == _serialize_value(new_value):
        return None

    return await _insert_edit(
        db,
        table_name=table_name,
        record_id=record_id,
        field_name=field_name,
        action=EditAction.UPDATE,
        old_value=old_value,
        new_value=new_value,
        source=source,
        user_id=user_id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )


async def log_updates(
    db: AsyncSession,
    *,
    table_name: str,
    record_id: int,
    old_record: dict[str, Any],
    new_record: dict[str, Any],
    source: EditSource = EditSource.local,
    user_id: int | None = None,
    editor_ip: str | None = None,
    editor_user_agent: str | None = None,
) -> list[Edit]:
    """Log UPDATE operations for multiple fields by comparing old and new records."""
    edits: list[Edit] = []
    for field_name, new_value in new_record.items():
        old_value = old_record.get(field_name)
        edit = await log_update(
            db,
            table_name=table_name,
            record_id=record_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            source=source,
            user_id=user_id,
            editor_ip=editor_ip,
            editor_user_agent=editor_user_agent,
        )
        if edit is not None:
            edits.append(edit)
    return edits


async def log_delete(
    db: AsyncSession,
    *,
    table_name: str,
    record_id: int,
    record_data: dict[str, Any],
    source: EditSource = EditSource.local,
    user_id: int | None = None,
    editor_ip: str | None = None,
    editor_user_agent: str | None = None,
) -> Edit | None:
    """Log a DELETE operation with a snapshot of the record before deletion."""
    if table_name not in TRACKED_TABLES:
        return None

    return await _insert_edit(
        db,
        table_name=table_name,
        record_id=record_id,
        field_name=None,
        action=EditAction.DELETE,
        old_value=record_data,
        new_value=None,
        source=source,
        user_id=user_id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )


async def get_record_history(
    db: AsyncSession,
    *,
    table_name: str,
    record_id: int,
) -> list[Edit]:
    """Get edit history for a specific record, newest first."""
    stmt = (
        select(Edit)
        .where(Edit.table_name == table_name, Edit.record_id == record_id)
        .order_by(Edit.created_at.desc())
    )
    result = await db.scalars(stmt)
    return list(result.all())
