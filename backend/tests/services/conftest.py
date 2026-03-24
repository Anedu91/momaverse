"""Shared fixtures for service tests."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.user import User


@pytest_asyncio.fixture(autouse=True)
async def _seed_user(db_session: AsyncSession) -> AsyncGenerator[None, None]:
    """Ensure a user with id=1 exists for FK-dependent service tests.

    On SQLite foreign keys were disabled so this was not needed, but
    PostgreSQL enforces FK constraints.  Some service tests reference
    ``user_id=1`` directly, so the user must exist with that exact id.
    """
    user = User(
        id=1,
        email="service-test@example.com",
        display_name="Service Test User",
        password_hash="fakehash",
    )
    db_session.add(user)
    await db_session.flush()
    yield
