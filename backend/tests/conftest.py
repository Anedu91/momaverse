"""Shared test fixtures for the momaverse backend test suite."""

from collections.abc import AsyncGenerator

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
from api.models.website import Website  # noqa: F401
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container() -> PostgresContainer:
    """Start a PostgreSQL 16 container for the test session."""
    with PostgresContainer("postgres:16") as pg:
        yield pg


@pytest_asyncio.fixture(scope="session")
async def async_engine(
    postgres_container: PostgresContainer,
) -> AsyncGenerator[AsyncEngine, None]:
    """Create an async engine connected to the test PostgreSQL container."""
    sync_url = postgres_container.get_connection_url()
    # Convert psycopg2 URL to asyncpg URL
    async_url = sync_url.replace("psycopg2", "asyncpg")
    engine = create_async_engine(async_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    async_engine: AsyncEngine,
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
