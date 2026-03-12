import pytest
from pydantic import ValidationError

from api.schemas.sync import SyncEdit, SyncEditsRequest, SyncStatusResponse


# ---------------------------------------------------------------------------
# SyncEdit
# ---------------------------------------------------------------------------


def test_edit_valid():
    edit = SyncEdit(
        edit_uuid="uuid-1234",
        table_name="events",
        record_id=1,
        action="INSERT",
        source="local",
    )
    assert edit.table_name == "events"


def test_edit_table_name_max_length():
    with pytest.raises(ValidationError):
        SyncEdit(
            edit_uuid="uuid-1234",
            table_name="x" * 51,
            record_id=1,
            action="INSERT",
            source="local",
        )


# ---------------------------------------------------------------------------
# SyncEditsRequest
# ---------------------------------------------------------------------------


def test_request_with_edits():
    req = SyncEditsRequest(
        edits=[
            SyncEdit(
                edit_uuid="uuid-1",
                table_name="events",
                record_id=1,
                action="INSERT",
                source="local",
            )
        ]
    )
    assert len(req.edits) == 1


def test_request_empty_edits():
    req = SyncEditsRequest(edits=[])
    assert req.edits == []


# ---------------------------------------------------------------------------
# SyncStatusResponse
# ---------------------------------------------------------------------------


def test_status_response():
    resp = SyncStatusResponse(source="local")
    assert resp.last_synced_edit_id is None
