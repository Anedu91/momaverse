"""Query helpers for soft-delete and versioned models."""

import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any, Sequence, TypeVar, cast

from sqlalchemy import column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from api.models.base import SoftDeleteMixin, VersionedMixin

SoftDeleteModelT = TypeVar("SoftDeleteModelT", bound=SoftDeleteMixin)
VersionedModelT = TypeVar("VersionedModelT", bound=VersionedMixin)


async def get_current(
    session: AsyncSession,
    model: type[VersionedModelT],
    entity_id: uuid_mod.UUID,
) -> VersionedModelT | None:
    """Get the current (non-deleted) version of a versioned record."""
    stmt = select(model).where(
        model.entity_id == entity_id,
        model.active(),
    )
    return cast(VersionedModelT | None, await session.scalar(stmt))


def filter_active(
    stmt: Select[tuple[SoftDeleteModelT]],
    model: type[SoftDeleteModelT],
) -> Select[tuple[SoftDeleteModelT]]:
    """Apply the active (non-deleted) filter to a select statement."""
    return stmt.where(model.active())


async def get_history(
    session: AsyncSession,
    model: type[VersionedModelT],
    entity_id: uuid_mod.UUID,
) -> Sequence[VersionedModelT]:
    """Get all versions (including deleted) of a record, newest first."""
    stmt = (
        select(model).where(model.entity_id == entity_id).order_by(column("id").desc())
    )
    result = await session.scalars(stmt)
    return result.all()


async def create_new_version(
    session: AsyncSession,
    model: type[VersionedModelT],
    entity_id: uuid_mod.UUID,
    **new_values: Any,
) -> VersionedModelT:
    """Soft-delete the current version and insert a new one.

    The new record shares the same entity_id.
    Flushes but does NOT commit — caller owns the transaction.
    """
    current = await get_current(session, model, entity_id)
    if current is not None:
        current.is_deleted = True
        current.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)

    new_record = model(entity_id=entity_id, **new_values)  # type: ignore[call-arg]
    session.add(new_record)
    await session.flush()
    return new_record
