import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.base import EditAction, EditSource, SyncSourceEnum
from api.models.edit import Edit, SyncState

TRACKED_TABLES: frozenset[str] = frozenset(
    {
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
    }
)


def _serialize_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


class EditLogger:
    def __init__(
        self,
        session: AsyncSession,
        source: EditSource = EditSource.website,
        editor_info: str | None = None,
    ) -> None:
        self.session = session
        self.source = source
        self.editor_info = editor_info
        self.user_id: int | None = None
        self.editor_ip: str | None = None
        self.editor_user_agent: str | None = None

    def set_user_context(
        self,
        user_id: int | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.user_id = user_id
        self.editor_ip = ip
        self.editor_user_agent = user_agent[:500] if user_agent else None

    def set_user_context_from_request(
        self,
        request: Request,
        user_id: int | None = None,
    ) -> None:
        self.user_id = user_id
        self.editor_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        self.editor_user_agent = user_agent[:500] if user_agent else None

    async def _insert_edit(
        self,
        table_name: str,
        record_id: int,
        field_name: str | None,
        action: EditAction,
        old_value: Any,
        new_value: Any,
    ) -> int:
        edit = Edit(
            edit_uuid=str(uuid.uuid4()),
            table_name=table_name,
            record_id=record_id,
            field_name=field_name,
            action=action,
            old_value=_serialize_value(old_value),
            new_value=_serialize_value(new_value),
            source=self.source,
            user_id=self.user_id,
            editor_ip=self.editor_ip,
            editor_user_agent=self.editor_user_agent,
            editor_info=self.editor_info,
            applied_at=datetime.now(timezone.utc),
        )
        self.session.add(edit)
        await self.session.flush()
        return edit.id

    async def log_insert(
        self,
        table_name: str,
        record_id: int,
        record_data: dict[str, Any],
    ) -> int | None:
        if table_name not in TRACKED_TABLES:
            return None
        return await self._insert_edit(
            table_name,
            record_id,
            None,
            EditAction.INSERT,
            None,
            record_data,
        )

    async def log_update(
        self,
        table_name: str,
        record_id: int,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> int | None:
        if table_name not in TRACKED_TABLES:
            return None
        if _serialize_value(old_value) == _serialize_value(new_value):
            return None
        return await self._insert_edit(
            table_name,
            record_id,
            field_name,
            EditAction.UPDATE,
            old_value,
            new_value,
        )

    async def log_updates(
        self,
        table_name: str,
        record_id: int,
        old_record: dict[str, Any],
        new_record: dict[str, Any],
    ) -> list[int]:
        edit_ids: list[int] = []
        for field_name, new_value in new_record.items():
            old_value = old_record.get(field_name)
            edit_id = await self.log_update(
                table_name,
                record_id,
                field_name,
                old_value,
                new_value,
            )
            if edit_id is not None:
                edit_ids.append(edit_id)
        return edit_ids

    async def log_delete(
        self,
        table_name: str,
        record_id: int,
        record_data: dict[str, Any],
    ) -> int | None:
        if table_name not in TRACKED_TABLES:
            return None
        return await self._insert_edit(
            table_name,
            record_id,
            None,
            EditAction.DELETE,
            record_data,
            None,
        )

    async def get_record_history(
        self,
        table_name: str,
        record_id: int,
    ) -> list[Edit]:
        stmt = (
            select(Edit)
            .options(selectinload(Edit.user))
            .where(Edit.table_name == table_name, Edit.record_id == record_id)
            .order_by(Edit.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_edits_since(
        self,
        since_id: int = 0,
        source: EditSource | None = None,
        limit: int = 1000,
    ) -> list[Edit]:
        stmt = select(Edit).where(Edit.id > since_id)
        if source is not None:
            stmt = stmt.where(Edit.source == source)
        stmt = stmt.order_by(Edit.id.asc()).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def update_last_synced_edit_id(
        self,
        source: SyncSourceEnum,
        edit_id: int,
    ) -> None:
        stmt = (
            pg_insert(SyncState)
            .values(
                source=source,
                last_synced_edit_id=edit_id,
                last_sync_at=func.now(),
            )
            .on_conflict_do_update(
                index_elements=["source"],
                set_={
                    "last_synced_edit_id": edit_id,
                    "last_sync_at": func.now(),
                },
            )
        )
        await self.session.execute(stmt)
