"""Shared fixtures for router integration tests."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@pytest_asyncio.fixture
async def db_session(
    async_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session using savepoints.

    A top-level transaction wraps each test and is rolled back at the end,
    giving full isolation even when the code under test calls ``commit()``.
    The ``commit()`` from the router only commits the inner savepoint, not
    the outer transaction.
    """
    async with async_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)

        # Start a nested savepoint so that commit() inside the router
        # only commits the savepoint, not the outer transaction.
        await conn.begin_nested()

        # After every commit (which finishes the savepoint), start a
        # fresh savepoint so subsequent operations still work.
        @event.listens_for(session.sync_session, "after_transaction_end")
        def _restart_savepoint(sync_session, transaction):  # noqa: ANN001
            if transaction.nested and not transaction._parent.nested:
                sync_session.begin_nested()

        yield session

        await session.close()
        await trans.rollback()
