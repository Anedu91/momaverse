"""Tests for soft-delete and versioning mixins + query helpers."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.services.versioning import (
    create_new_version,
    filter_active,
    get_current,
    get_history,
)
from tests.models.test_models import SoftDeleteItem, VersionedItem


# ============================================================================
# SoftDeleteMixin tests
# ============================================================================


@pytest.mark.asyncio
async def test_default_values(db_session: AsyncSession) -> None:
    item = SoftDeleteItem(name="item")
    db_session.add(item)
    await db_session.flush()

    assert item.is_deleted is False
    assert item.deleted_at is None


@pytest.mark.asyncio
async def test_soft_delete_sets_fields(db_session: AsyncSession) -> None:
    item = SoftDeleteItem(name="item")
    db_session.add(item)
    await db_session.flush()

    item.soft_delete()
    await db_session.flush()

    assert item.is_deleted is True
    assert item.deleted_at is not None


@pytest.mark.asyncio
async def test_restore_clears_fields(db_session: AsyncSession) -> None:
    item = SoftDeleteItem(name="item")
    db_session.add(item)
    await db_session.flush()

    item.soft_delete()
    await db_session.flush()
    item.restore()
    await db_session.flush()

    assert item.is_deleted is False
    assert item.deleted_at is None


@pytest.mark.asyncio
async def test_active_filter_excludes_deleted(db_session: AsyncSession) -> None:
    for name in ("a", "b", "c"):
        db_session.add(SoftDeleteItem(name=name))
    await db_session.flush()

    # Soft-delete one
    result = await db_session.scalars(
        select(SoftDeleteItem).where(SoftDeleteItem.name == "b")
    )
    item_b = result.one()
    item_b.soft_delete()
    await db_session.flush()

    # Query with active filter
    active_items = (
        await db_session.scalars(select(SoftDeleteItem).where(SoftDeleteItem.active()))
    ).all()
    assert len(active_items) == 2
    assert all(i.name != "b" for i in active_items)


@pytest.mark.asyncio
async def test_query_without_active_returns_all(db_session: AsyncSession) -> None:
    for name in ("a", "b"):
        db_session.add(SoftDeleteItem(name=name))
    await db_session.flush()

    result = await db_session.scalars(
        select(SoftDeleteItem).where(SoftDeleteItem.name == "a")
    )
    result.one().soft_delete()
    await db_session.flush()

    all_items = (await db_session.scalars(select(SoftDeleteItem))).all()
    assert len(all_items) == 2


# ============================================================================
# VersionedMixin tests
# ============================================================================


@pytest.mark.asyncio
async def test_entity_id_auto_generated(db_session: AsyncSession) -> None:
    item = VersionedItem(name="v1")
    db_session.add(item)
    await db_session.flush()

    assert isinstance(item.entity_id, uuid.UUID)


@pytest.mark.asyncio
async def test_versioned_inherits_soft_delete(db_session: AsyncSession) -> None:
    item = VersionedItem(name="v1")
    db_session.add(item)
    await db_session.flush()

    assert item.is_deleted is False
    item.soft_delete()
    assert item.is_deleted is True
    item.restore()
    assert item.is_deleted is False


# ============================================================================
# Query helper tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_current_returns_active(db_session: AsyncSession) -> None:
    item = VersionedItem(name="v1")
    db_session.add(item)
    await db_session.flush()

    current = await get_current(db_session, VersionedItem, item.entity_id)
    assert current is not None
    assert current.name == "v1"


@pytest.mark.asyncio
async def test_get_current_returns_none_when_deleted(db_session: AsyncSession) -> None:
    item = VersionedItem(name="v1")
    db_session.add(item)
    await db_session.flush()

    item.soft_delete()
    await db_session.flush()

    current = await get_current(db_session, VersionedItem, item.entity_id)
    assert current is None


@pytest.mark.asyncio
async def test_get_current_returns_none_for_unknown(db_session: AsyncSession) -> None:
    current = await get_current(db_session, VersionedItem, uuid.uuid4())
    assert current is None


@pytest.mark.asyncio
async def test_filter_active_excludes_deleted(db_session: AsyncSession) -> None:
    for name in ("x", "y"):
        db_session.add(VersionedItem(name=name))
    await db_session.flush()

    result = await db_session.scalars(
        select(VersionedItem).where(VersionedItem.name == "x")
    )
    result.one().soft_delete()
    await db_session.flush()

    stmt = filter_active(select(VersionedItem), VersionedItem)
    active = (await db_session.scalars(stmt)).all()
    assert len(active) == 1
    assert active[0].name == "y"


@pytest.mark.asyncio
async def test_get_history_returns_all_versions(db_session: AsyncSession) -> None:
    item = VersionedItem(name="v1")
    db_session.add(item)
    await db_session.flush()
    eid = item.entity_id

    await create_new_version(db_session, VersionedItem, eid, name="v2")
    await create_new_version(db_session, VersionedItem, eid, name="v3")

    history = await get_history(db_session, VersionedItem, eid)
    assert len(history) == 3
    # Newest first
    assert history[0].name == "v3"
    assert history[1].name == "v2"
    assert history[2].name == "v1"


@pytest.mark.asyncio
async def test_get_history_empty_for_unknown(db_session: AsyncSession) -> None:
    history = await get_history(db_session, VersionedItem, uuid.uuid4())
    assert len(history) == 0


@pytest.mark.asyncio
async def test_create_new_version_soft_deletes_current(
    db_session: AsyncSession,
) -> None:
    item = VersionedItem(name="v1")
    db_session.add(item)
    await db_session.flush()
    eid = item.entity_id

    new = await create_new_version(db_session, VersionedItem, eid, name="v2")

    assert item.is_deleted is True
    assert item.deleted_at is not None
    assert new.is_deleted is False
    assert new.entity_id == eid
    assert new.name == "v2"


@pytest.mark.asyncio
async def test_create_new_version_preserves_entity_id(db_session: AsyncSession) -> None:
    item = VersionedItem(name="v1")
    db_session.add(item)
    await db_session.flush()
    eid = item.entity_id

    v2 = await create_new_version(db_session, VersionedItem, eid, name="v2")
    v3 = await create_new_version(db_session, VersionedItem, eid, name="v3")

    assert v2.entity_id == eid
    assert v3.entity_id == eid


@pytest.mark.asyncio
async def test_create_new_version_no_existing(db_session: AsyncSession) -> None:
    eid = uuid.uuid4()
    new = await create_new_version(db_session, VersionedItem, eid, name="first")

    assert new.entity_id == eid
    assert new.name == "first"
    assert new.is_deleted is False
