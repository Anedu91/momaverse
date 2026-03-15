"""Tests for SQLAdmin setup and authentication."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqladmin import Admin

from api.admin import setup_admin
from api.admin.auth import AdminAuth
from api.admin.views import (
    ALL_VIEWS,
    EditAdmin,
    FeedbackAdmin,
    UserAdmin,
)
from api.dependencies import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_user(
    user_id: int = 1,
    email: str = "admin@example.com",
    password: str = "secret",
    is_admin: bool = True,
) -> object:
    """Return a lightweight object that quacks like a User row."""

    class FakeUser:
        pass

    fake = FakeUser()
    fake.id = user_id  # type: ignore[attr-defined]
    fake.email = email  # type: ignore[attr-defined]
    fake.password_hash = hash_password(password)  # type: ignore[attr-defined]
    fake.is_admin = is_admin  # type: ignore[attr-defined]
    return fake


def _patch_db_lookup(
    fake_user: object | None,
) -> Any:
    """Patch AsyncSessionLocal so the auth backend finds *fake_user*."""
    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=fake_user)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    # AsyncSessionLocal() must return the async context manager directly
    # (not a coroutine), since async_sessionmaker.__call__ returns an
    # AsyncSession which is used as `async with AsyncSessionLocal() as s:`.
    mock_factory = MagicMock(return_value=mock_session)
    return patch("api.admin.auth.AsyncSessionLocal", mock_factory)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_requires_authentication() -> None:
    """GET /admin/ without a session should redirect to the login page."""
    from api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/admin/", follow_redirects=False)

    # SQLAdmin returns a 302 redirect to its login page for unauthenticated users
    assert response.status_code in (302, 303, 401)


@pytest.mark.asyncio
async def test_admin_auth_rejects_non_admin() -> None:
    """Login with a user that has is_admin=False should fail."""
    fake_user = _make_fake_user(is_admin=False, password="secret")

    with _patch_db_lookup(fake_user):
        auth = AdminAuth(secret_key="test-secret")
        request = _build_login_request("admin@example.com", "secret")
        result = await auth.login(request)  # type: ignore[arg-type]

    assert result is False


@pytest.mark.asyncio
async def test_admin_auth_accepts_admin() -> None:
    """Login with a valid admin user should succeed."""
    fake_user = _make_fake_user(is_admin=True, password="secret")

    with _patch_db_lookup(fake_user):
        auth = AdminAuth(secret_key="test-secret")
        request = _build_login_request("admin@example.com", "secret")
        result = await auth.login(request)  # type: ignore[arg-type]

    assert result is True
    assert request.session.get("user_id") == 1


@pytest.mark.asyncio
async def test_admin_auth_rejects_invalid_credentials() -> None:
    """Login with wrong password should fail."""
    fake_user = _make_fake_user(is_admin=True, password="correct")

    with _patch_db_lookup(fake_user):
        auth = AdminAuth(secret_key="test-secret")
        request = _build_login_request("admin@example.com", "wrong")
        result = await auth.login(request)  # type: ignore[arg-type]

    assert result is False


@pytest.mark.asyncio
async def test_admin_auth_rejects_unknown_user() -> None:
    """Login with an email that does not exist should fail."""
    with _patch_db_lookup(None):
        auth = AdminAuth(secret_key="test-secret")
        request = _build_login_request("nobody@example.com", "secret")
        result = await auth.login(request)  # type: ignore[arg-type]

    assert result is False


def test_edit_admin_is_read_only() -> None:
    """EditAdmin must not allow create, edit, or delete."""
    assert EditAdmin.can_create is False
    assert EditAdmin.can_edit is False
    assert EditAdmin.can_delete is False


def test_feedback_admin_is_read_only() -> None:
    """FeedbackAdmin must not allow create, edit, or delete."""
    assert FeedbackAdmin.can_create is False
    assert FeedbackAdmin.can_edit is False
    assert FeedbackAdmin.can_delete is False


def test_all_admin_views_registered() -> None:
    """All expected admin views should be present in the ALL_VIEWS list."""
    assert len(ALL_VIEWS) == 15

    from fastapi import FastAPI
    from unittest.mock import MagicMock

    test_app = FastAPI()
    with patch("api.admin.engine", MagicMock()):
        admin = setup_admin(test_app)

    assert isinstance(admin, Admin)


@pytest.mark.asyncio
async def test_admin_logout_clears_session() -> None:
    """Logout should clear the session."""
    auth = AdminAuth(secret_key="test-secret")

    # Build a request with a session containing user_id
    request = _build_login_request("", "")
    request.session["user_id"] = 1

    result = await auth.logout(request)  # type: ignore[arg-type]
    assert result is True
    assert "user_id" not in request.session


@pytest.mark.asyncio
async def test_admin_authenticate_requires_user_id() -> None:
    """authenticate() should return False when session has no user_id."""
    auth = AdminAuth(secret_key="test-secret")
    request = _build_login_request("", "")

    result = await auth.authenticate(request)  # type: ignore[arg-type]
    assert result is False


@pytest.mark.asyncio
async def test_admin_authenticate_succeeds_with_session() -> None:
    """authenticate() should return True when session has a valid admin user_id."""
    fake_user = _make_fake_user(is_admin=True)

    with _patch_db_lookup(fake_user):
        auth = AdminAuth(secret_key="test-secret")
        request = _build_login_request("", "")
        request.session["user_id"] = 1

        result = await auth.authenticate(request)  # type: ignore[arg-type]
    assert result is True


@pytest.mark.asyncio
async def test_admin_authenticate_rejects_demoted_user() -> None:
    """authenticate() should reject and clear session for a demoted user."""
    fake_user = _make_fake_user(is_admin=False)

    with _patch_db_lookup(fake_user):
        auth = AdminAuth(secret_key="test-secret")
        request = _build_login_request("", "")
        request.session["user_id"] = 1

        result = await auth.authenticate(request)  # type: ignore[arg-type]
    assert result is False
    assert "user_id" not in request.session


@pytest.mark.asyncio
async def test_admin_authenticate_rejects_deleted_user() -> None:
    """authenticate() should reject and clear session for a deleted user."""
    with _patch_db_lookup(None):
        auth = AdminAuth(secret_key="test-secret")
        request = _build_login_request("", "")
        request.session["user_id"] = 999

        result = await auth.authenticate(request)  # type: ignore[arg-type]
    assert result is False
    assert "user_id" not in request.session


def test_user_admin_cannot_create() -> None:
    """UserAdmin must not allow user creation (users are created via the API)."""
    assert UserAdmin.can_create is False


# ---------------------------------------------------------------------------
# Request builder
# ---------------------------------------------------------------------------


class _FakeFormData(dict):  # type: ignore[type-arg]
    """Minimal awaitable form data for testing."""


class _FakeRequest:
    """Minimal Starlette-like request compatible with AdminAuth methods.

    Quacks enough like ``starlette.requests.Request`` for unit tests.
    We suppress mypy arg-type errors at call sites because building a
    real ASGI request just for the session dict is not worthwhile.
    """

    def __init__(self, form_data: dict[str, str]) -> None:
        self._form_data = form_data
        self.session: dict[str, object] = {}

    async def form(self) -> _FakeFormData:
        return _FakeFormData(self._form_data)


def _build_login_request(email: str, password: str) -> _FakeRequest:
    """Build a fake request with login form data."""
    return _FakeRequest({"username": email, "password": password})
