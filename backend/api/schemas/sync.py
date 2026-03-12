from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from api.models.base import EditAction, EditSource, SyncSourceEnum

__all__ = ["SyncEdit", "SyncEditsRequest", "SyncStatusResponse"]


class SyncEdit(BaseModel):
    edit_uuid: Annotated[str, Field(max_length=36)]
    table_name: Annotated[str, Field(max_length=50)]
    record_id: int
    field_name: Annotated[str | None, Field(max_length=100)] = None
    action: EditAction
    old_value: str | None = None
    new_value: str | None = None
    source: EditSource


class SyncEditsRequest(BaseModel):
    edits: list[SyncEdit]


class SyncStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: SyncSourceEnum
    last_synced_edit_id: int | None = None
    last_sync_at: datetime | None = None
