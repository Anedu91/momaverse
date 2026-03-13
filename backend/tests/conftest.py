"""Shared test fixtures for the momaverse backend test suite."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from api.database import Base
from api.models.crawl import CrawlResult  # noqa: F401
from api.models.edit import Edit  # noqa: F401
from api.models.event import Event, EventOccurrence, EventSource, EventTag, EventUrl  # noqa: F401
from api.models.feedback import Feedback  # noqa: F401
from api.models.instagram import InstagramAccount  # noqa: F401
from api.models.tag import Tag  # noqa: F401
from api.models.user import User  # noqa: F401

# SQLite does not support JSONB. Map it to JSON for tests.
# Import models that use JSONB so their tables are registered.
from api.models.website import Website  # noqa: F401
from sqlalchemy import JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture(scope="session")
def async_engine() -> AsyncEngine:
    """Create an async in-memory SQLite engine for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn: Any, _: Any) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    return engine


@pytest_asyncio.fixture(scope="session")
async def _create_tables(
    async_engine: AsyncEngine,
) -> AsyncGenerator[None, None]:
    """Create all tables once per test session."""

    # Replace JSONB columns with JSON for SQLite compatibility.
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(
    async_engine: AsyncEngine, _create_tables: None
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session that rolls back."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create and return a sample user in the test DB."""
    user = User(
        email="test@example.com",
        display_name="Test User",
        password_hash="fakehash",
    )
    db_session.add(user)
    await db_session.flush()
    return user
