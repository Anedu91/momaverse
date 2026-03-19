"""Tests for soft-delete mixin."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.models.test_models import SoftDeleteItem


# ============================================================================
# SoftDeleteMixin tests
# ============================================================================


@pytest.mark.asyncio
async def test_default_deleted_at_is_none(db_session: AsyncSession) -> None:
    item = SoftDeleteItem(name="item")
    db_session.add(item)
    await db_session.flush()

    assert item.deleted_at is None


@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(db_session: AsyncSession) -> None:
    item = SoftDeleteItem(name="item")
    db_session.add(item)
    await db_session.flush()

    item.soft_delete()
    await db_session.flush()

    assert item.deleted_at is not None


@pytest.mark.asyncio
async def test_restore_clears_deleted_at(db_session: AsyncSession) -> None:
    item = SoftDeleteItem(name="item")
    db_session.add(item)
    await db_session.flush()

    item.soft_delete()
    await db_session.flush()
    item.restore()
    await db_session.flush()

    assert item.deleted_at is None


@pytest.mark.asyncio
async def test_active_filter_excludes_deleted(db_session: AsyncSession) -> None:
    for name in ("a", "b", "c"):
        db_session.add(SoftDeleteItem(name=name))
    await db_session.flush()

    result = await db_session.scalars(
        select(SoftDeleteItem).where(SoftDeleteItem.name == "b")
    )
    item_b = result.one()
    item_b.soft_delete()
    await db_session.flush()

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


@pytest.mark.asyncio
async def test_active_filter_returns_all_when_none_deleted(
    db_session: AsyncSession,
) -> None:
    for name in ("x", "y", "z"):
        db_session.add(SoftDeleteItem(name=name))
    await db_session.flush()

    active = (
        await db_session.scalars(select(SoftDeleteItem).where(SoftDeleteItem.active()))
    ).all()
    assert len(active) == 3


@pytest.mark.asyncio
async def test_soft_delete_then_restore_is_active(db_session: AsyncSession) -> None:
    item = SoftDeleteItem(name="item")
    db_session.add(item)
    await db_session.flush()

    item.soft_delete()
    await db_session.flush()
    item.restore()
    await db_session.flush()

    active = (
        await db_session.scalars(select(SoftDeleteItem).where(SoftDeleteItem.active()))
    ).all()
    assert len(active) == 1
    assert active[0].name == "item"
