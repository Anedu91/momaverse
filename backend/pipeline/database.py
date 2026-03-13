"""
Pipeline database session factory.

Own engine separate from the API's engine, but reuses the same
api.config settings and api.models.
Commits on successful exit, rolls back on error.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)


@asynccontextmanager
async def get_pipeline_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that commits on success, rolls back on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the pipeline engine (call on shutdown)."""
    await engine.dispose()
