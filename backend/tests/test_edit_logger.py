import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.edit_logger import TRACKED_TABLES, EditLogger, _serialize_value
from api.models.base import EditSource

# ---------------------------------------------------------------------------
# _serialize_value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("hello", "hello"),
        (42, "42"),
        (3.14, "3.14"),
        (True, "True"),
    ],
)
def test_serialize_value_scalars(value, expected):
    assert _serialize_value(value) == expected


def test_serialize_value_datetime():
    dt = datetime(2026, 1, 15, 10, 30, 0)
    assert _serialize_value(dt) == "2026-01-15T10:30:00"


def test_serialize_value_dict():
    data = {"name": "Central Park", "lat": 40.785}
    result = _serialize_value(data)
    assert result is not None
    assert json.loads(result) == data


def test_serialize_value_list():
    data = ["a", "b", "c"]
    result = _serialize_value(data)
    assert result is not None
    assert json.loads(result) == data


# ---------------------------------------------------------------------------
# TRACKED_TABLES
# ---------------------------------------------------------------------------


def test_tracked_tables_contains_expected():
    expected = {
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
    assert TRACKED_TABLES == expected


def test_tracked_tables_is_frozenset():
    assert isinstance(TRACKED_TABLES, frozenset)


# ---------------------------------------------------------------------------
# EditLogger — init and context
# ---------------------------------------------------------------------------


def test_init_defaults():
    session = AsyncMock()
    logger = EditLogger(session=session)
    assert logger.source == EditSource.website
    assert logger.editor_info is None
    assert logger.user_id is None
    assert logger.editor_ip is None
    assert logger.editor_user_agent is None


def test_init_custom():
    session = AsyncMock()
    logger = EditLogger(
        session=session,
        source=EditSource.crawl,
        editor_info="crawl_run:5",
    )
    assert logger.source == EditSource.crawl
    assert logger.editor_info == "crawl_run:5"


def test_set_user_context():
    session = AsyncMock()
    logger = EditLogger(session=session)
    logger.set_user_context(user_id=1, ip="127.0.0.1", user_agent="TestAgent")
    assert logger.user_id == 1
    assert logger.editor_ip == "127.0.0.1"
    assert logger.editor_user_agent == "TestAgent"


def test_set_user_context_truncates_user_agent():
    session = AsyncMock()
    logger = EditLogger(session=session)
    long_ua = "A" * 600
    logger.set_user_context(user_agent=long_ua)
    assert logger.editor_user_agent is not None
    assert len(logger.editor_user_agent) == 500


def test_set_user_context_from_request():
    session = AsyncMock()
    logger = EditLogger(session=session)

    request = MagicMock()
    request.client.host = "192.168.1.1"
    request.headers.get.return_value = "Mozilla/5.0"

    logger.set_user_context_from_request(request, user_id=42)
    assert logger.user_id == 42
    assert logger.editor_ip == "192.168.1.1"
    assert logger.editor_user_agent == "Mozilla/5.0"


def test_set_user_context_from_request_no_client():
    session = AsyncMock()
    logger = EditLogger(session=session)

    request = MagicMock()
    request.client = None
    request.headers.get.return_value = None

    logger.set_user_context_from_request(request)
    assert logger.user_id is None
    assert logger.editor_ip is None
    assert logger.editor_user_agent is None


# ---------------------------------------------------------------------------
# EditLogger — log methods (unit tests with mocked session)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_insert_untracked_table():
    session = AsyncMock()
    logger = EditLogger(session=session)
    result = await logger.log_insert("unknown_table", 1, {"name": "test"})
    assert result is None
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_log_insert_tracked_table():
    session = AsyncMock()
    session.flush = AsyncMock()
    logger = EditLogger(session=session)

    with patch("api.edit_logger.Edit") as MockEdit:
        mock_edit = MagicMock()
        mock_edit.id = 99
        MockEdit.return_value = mock_edit

        result = await logger.log_insert("locations", 1, {"name": "Park"})

    assert result == 99
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_log_update_untracked_table():
    session = AsyncMock()
    logger = EditLogger(session=session)
    result = await logger.log_update("unknown_table", 1, "name", "old", "new")
    assert result is None


@pytest.mark.asyncio
async def test_log_update_no_change():
    session = AsyncMock()
    logger = EditLogger(session=session)
    result = await logger.log_update("locations", 1, "name", "same", "same")
    assert result is None
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_log_update_with_change():
    session = AsyncMock()
    session.flush = AsyncMock()
    logger = EditLogger(session=session)

    with patch("api.edit_logger.Edit") as MockEdit:
        mock_edit = MagicMock()
        mock_edit.id = 100
        MockEdit.return_value = mock_edit

        result = await logger.log_update("locations", 1, "name", "Old Park", "New Park")

    assert result == 100
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_log_updates_multiple_fields():
    session = AsyncMock()
    session.flush = AsyncMock()
    logger = EditLogger(session=session)

    edit_counter = iter(range(1, 10))

    with patch("api.edit_logger.Edit") as MockEdit:

        def make_edit(*args, **kwargs):
            mock = MagicMock()
            mock.id = next(edit_counter)
            return mock

        MockEdit.side_effect = make_edit

        result = await logger.log_updates(
            "locations",
            1,
            {"name": "Old", "lat": "40.0", "lng": "-74.0"},
            {"name": "New", "lat": "40.0", "lng": "-73.0"},
        )

    # name changed, lat unchanged, lng changed
    assert len(result) == 2


@pytest.mark.asyncio
async def test_log_delete_untracked_table():
    session = AsyncMock()
    logger = EditLogger(session=session)
    result = await logger.log_delete("unknown_table", 1, {"name": "test"})
    assert result is None


@pytest.mark.asyncio
async def test_log_delete_tracked_table():
    session = AsyncMock()
    session.flush = AsyncMock()
    logger = EditLogger(session=session)

    with patch("api.edit_logger.Edit") as MockEdit:
        mock_edit = MagicMock()
        mock_edit.id = 101
        MockEdit.return_value = mock_edit

        result = await logger.log_delete("locations", 1, {"name": "Park"})

    assert result == 101
    session.add.assert_called_once()
