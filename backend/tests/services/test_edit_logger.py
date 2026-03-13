"""Tests for the edit logger service."""

import json
from datetime import datetime

import pytest
from api.models.base import EditAction, EditSource
from api.services.edit_logger import (
    TRACKED_TABLES,
    _serialize_value,
    get_record_history,
    log_delete,
    log_insert,
    log_update,
    log_updates,
)

# ---------------------------------------------------------------
# _serialize_value
# ---------------------------------------------------------------


class TestSerializeValue:
    def test_none_returns_none(self):
        assert _serialize_value(None) is None

    def test_string_returns_string(self):
        assert _serialize_value("hello") == "hello"

    def test_int_returns_string(self):
        assert _serialize_value(42) == "42"

    def test_dict_returns_json(self):
        result = _serialize_value({"a": 1})
        assert result is not None
        assert json.loads(result) == {"a": 1}

    def test_list_returns_json(self):
        result = _serialize_value([1, 2, 3])
        assert result is not None
        assert json.loads(result) == [1, 2, 3]

    def test_datetime_returns_isoformat(self):
        dt = datetime(2026, 1, 15, 10, 30, 0)
        assert _serialize_value(dt) == dt.isoformat()

    def test_bool_returns_string(self):
        assert _serialize_value(True) == "True"


# ---------------------------------------------------------------
# log_insert
# ---------------------------------------------------------------


class TestLogInsert:
    @pytest.mark.asyncio
    async def test_creates_edit_record(self, db_session):
        record_data = {"name": "Test", "lat": 40.0}
        edit = await log_insert(
            db_session,
            table_name="locations",
            record_id=1,
            record_data=record_data,
        )

        assert edit is not None
        assert edit.table_name == "locations"
        assert edit.record_id == 1
        assert edit.action == EditAction.INSERT
        assert edit.old_value is None
        assert edit.new_value is not None
        assert edit.field_name is None
        assert edit.source == EditSource.local

    @pytest.mark.asyncio
    async def test_stores_user_context(self, db_session):
        edit = await log_insert(
            db_session,
            table_name="tags",
            record_id=5,
            record_data={"name": "music"},
            user_id=1,
            editor_ip="127.0.0.1",
            editor_user_agent="TestAgent/1.0",
        )

        assert edit is not None
        assert edit.user_id == 1
        assert edit.editor_ip == "127.0.0.1"
        assert edit.editor_user_agent == "TestAgent/1.0"

    @pytest.mark.asyncio
    async def test_untracked_table_returns_none(self, db_session):
        edit = await log_insert(
            db_session,
            table_name="users",
            record_id=1,
            record_data={"email": "x@y.com"},
        )
        assert edit is None

    @pytest.mark.asyncio
    async def test_edit_uuid_is_set(self, db_session):
        edit = await log_insert(
            db_session,
            table_name="locations",
            record_id=99,
            record_data={"name": "Place"},
        )
        assert edit is not None
        assert len(edit.edit_uuid) == 36


# ---------------------------------------------------------------
# log_update
# ---------------------------------------------------------------


class TestLogUpdate:
    @pytest.mark.asyncio
    async def test_creates_edit_for_changed_field(self, db_session):
        edit = await log_update(
            db_session,
            table_name="events",
            record_id=10,
            field_name="name",
            old_value="Old Name",
            new_value="New Name",
        )

        assert edit is not None
        assert edit.action == EditAction.UPDATE
        assert edit.field_name == "name"
        assert edit.old_value == "Old Name"
        assert edit.new_value == "New Name"

    @pytest.mark.asyncio
    async def test_skips_unchanged_value(self, db_session):
        edit = await log_update(
            db_session,
            table_name="events",
            record_id=10,
            field_name="name",
            old_value="Same",
            new_value="Same",
        )
        assert edit is None

    @pytest.mark.asyncio
    async def test_skips_unchanged_none(self, db_session):
        edit = await log_update(
            db_session,
            table_name="events",
            record_id=10,
            field_name="description",
            old_value=None,
            new_value=None,
        )
        assert edit is None

    @pytest.mark.asyncio
    async def test_untracked_table_returns_none(self, db_session):
        edit = await log_update(
            db_session,
            table_name="untracked_table",
            record_id=1,
            field_name="col",
            old_value="a",
            new_value="b",
        )
        assert edit is None


# ---------------------------------------------------------------
# log_updates (batch)
# ---------------------------------------------------------------


class TestLogUpdates:
    @pytest.mark.asyncio
    async def test_logs_only_changed_fields(self, db_session):
        old = {"name": "Old", "lat": 40.0, "lng": -74.0}
        new = {"name": "New", "lat": 40.0, "lng": -75.0}

        edits = await log_updates(
            db_session,
            table_name="locations",
            record_id=1,
            old_record=old,
            new_record=new,
        )

        assert len(edits) == 2
        field_names = {e.field_name for e in edits}
        assert field_names == {"name", "lng"}

    @pytest.mark.asyncio
    async def test_returns_empty_when_nothing_changed(self, db_session):
        data = {"name": "Same", "lat": 40.0}
        edits = await log_updates(
            db_session,
            table_name="locations",
            record_id=1,
            old_record=data,
            new_record=data,
        )
        assert edits == []


# ---------------------------------------------------------------
# log_delete
# ---------------------------------------------------------------


class TestLogDelete:
    @pytest.mark.asyncio
    async def test_creates_delete_edit(self, db_session):
        record_data = {"name": "Deleted Location", "lat": 0}
        edit = await log_delete(
            db_session,
            table_name="locations",
            record_id=77,
            record_data=record_data,
        )

        assert edit is not None
        assert edit.action == EditAction.DELETE
        assert edit.new_value is None
        assert edit.old_value is not None
        assert edit.record_id == 77

    @pytest.mark.asyncio
    async def test_untracked_table_returns_none(self, db_session):
        edit = await log_delete(
            db_session,
            table_name="sessions",
            record_id=1,
            record_data={"id": 1},
        )
        assert edit is None


# ---------------------------------------------------------------
# get_record_history
# ---------------------------------------------------------------


class TestGetRecordHistory:
    @pytest.mark.asyncio
    async def test_returns_edits_for_record(self, db_session):
        # Insert then update
        await log_insert(
            db_session,
            table_name="tags",
            record_id=200,
            record_data={"name": "original"},
        )
        await log_update(
            db_session,
            table_name="tags",
            record_id=200,
            field_name="name",
            old_value="original",
            new_value="renamed",
        )

        history = await get_record_history(
            db_session,
            table_name="tags",
            record_id=200,
        )

        assert len(history) == 2
        actions = {e.action for e in history}
        assert actions == {EditAction.INSERT, EditAction.UPDATE}

    @pytest.mark.asyncio
    async def test_empty_for_nonexistent_record(self, db_session):
        history = await get_record_history(
            db_session,
            table_name="tags",
            record_id=99999,
        )
        assert history == []


# ---------------------------------------------------------------
# TRACKED_TABLES sanity check
# ---------------------------------------------------------------


def test_tracked_tables_contains_expected():
    assert "locations" in TRACKED_TABLES
    assert "tags" in TRACKED_TABLES
    assert "events" in TRACKED_TABLES
    assert "users" not in TRACKED_TABLES
