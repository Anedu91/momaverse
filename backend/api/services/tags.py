"""Shared tag helper — async get-or-create for tags."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.tag import Tag


async def get_or_create_tag(db: AsyncSession, name: str) -> Tag:
    """Return an existing Tag by name, or create and flush a new one.

    Handles the race condition where two concurrent requests try to create
    the same tag by catching the IntegrityError and re-fetching.
    """
    tag = await db.scalar(select(Tag).where(Tag.name == name))
    if tag is not None:
        return tag

    tag = Tag(name=name)
    db.add(tag)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        result = await db.scalar(select(Tag).where(Tag.name == name))
        assert result is not None, f"Tag '{name}' not found after IntegrityError"
        return result
    return tag
