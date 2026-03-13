from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from api.models.base import EditAction, EditSource

__all__ = ["EditHistoryEntry", "EditResponse"]


class EditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edit_uuid: str
    table_name: str
    record_id: int
    field_name: Annotated[str | None, Field(max_length=100)] = None
    action: EditAction
    old_value: str | None = None
    new_value: str | None = None
    source: EditSource
    user_id: int | None = None
    created_at: datetime
    applied_at: datetime | None = None


# TODO: Remove EditHistoryEntry — user_name/user_email are not populated from
# the Edit model. This schema will be replaced when edit history is redesigned.
class EditHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edit_uuid: str
    field_name: Annotated[str | None, Field(max_length=100)] = None
    action: EditAction
    old_value: str | None = None
    new_value: str | None = None
    source: EditSource
    editor_info: str | None = None
    created_at: datetime
    user_name: str | None = None
    user_email: str | None = None
