from datetime import datetime

from pydantic import BaseModel, ConfigDict

from api.models.base import EditAction, EditSource

__all__ = ["EditResponse"]


class EditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edit_uuid: str
    table_name: str
    record_id: int
    field_name: str | None = None
    action: EditAction
    old_value: str | None = None
    new_value: str | None = None
    source: EditSource
    user_id: int | None = None
    created_at: datetime
    applied_at: datetime | None = None


