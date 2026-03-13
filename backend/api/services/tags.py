"""Shared tag helper — async get-or-create for tags."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.tag import Tag


async def get_or_create_tag(db: AsyncSession, name: str) -> Tag:
    """Return an existing Tag by name, or create and flush a new one."""
    tag = await db.scalar(select(Tag).where(Tag.name == name))
    if tag is not None:
        return tag

    tag = Tag(name=name)
    db.add(tag)
    await db.flush()
    return tag
