from unittest.mock import AsyncMock, MagicMock

import pytest
from api.dependencies import get_current_user, get_edit_logger, get_optional_user
from api.models.base import EditSource
from api.models.user import User
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_no_session():
    request = MagicMock()
    request.session = {}
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_user_not_found():
    request = MagicMock()
    request.session = {"user_id": 999}
    db = AsyncMock()
    db.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request, db)
    assert exc_info.value.status_code == 401
    assert request.session == {}


@pytest.mark.asyncio
async def test_get_current_user_success():
    user = MagicMock(spec=User, id=1, email="test@example.com")
    request = MagicMock()
    request.session = {"user_id": 1}
    db = AsyncMock()
    db.get.return_value = user

    result = await get_current_user(request, db)
    assert result == user
    db.get.assert_awaited_once()


# ---------------------------------------------------------------------------
# get_optional_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_optional_user_no_session():
    request = MagicMock()
    request.session = {}
    db = AsyncMock()

    result = await get_optional_user(request, db)
    assert result is None


@pytest.mark.asyncio
async def test_get_optional_user_user_not_found():
    request = MagicMock()
    request.session = {"user_id": 999}
    db = AsyncMock()
    db.get.return_value = None

    result = await get_optional_user(request, db)
    assert result is None
    assert request.session == {}


@pytest.mark.asyncio
async def test_get_optional_user_success():
    user = MagicMock(spec=User, id=1, email="test@example.com")
    request = MagicMock()
    request.session = {"user_id": 1}
    db = AsyncMock()
    db.get.return_value = user

    result = await get_optional_user(request, db)
    assert result == user


# ---------------------------------------------------------------------------
# get_edit_logger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_edit_logger_with_user():
    user = MagicMock(spec=User, id=42)
    request = MagicMock()
    request.client.host = "10.0.0.1"
    request.headers.get.return_value = "TestBrowser/1.0"
    db = AsyncMock()

    logger = await get_edit_logger(request, db, user)
    assert logger.source == EditSource.website
    assert logger.user_id == 42
    assert logger.editor_ip == "10.0.0.1"
    assert logger.editor_user_agent == "TestBrowser/1.0"


@pytest.mark.asyncio
async def test_get_edit_logger_anonymous():
    request = MagicMock()
    request.client.host = "10.0.0.1"
    request.headers.get.return_value = None
    db = AsyncMock()

    logger = await get_edit_logger(request, db, None)
    assert logger.user_id is None
    assert logger.editor_user_agent is None
