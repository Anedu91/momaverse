"""Processing-related database operations using SQLAlchemy."""

from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Location, LocationAlternateName, TagRule
from api.models import WebsiteUrl, Website
from api.models.base import TagRuleType


class TagRules(TypedDict):
    rewrite: dict[str, str]
    exclude: list[str]
    remove: list[str]


async def get_all_locations(session: AsyncSession) -> list[dict[str, Any]]:
    """Get all locations with their alternate names for location matching."""
    # Get locations with lat/lng
    result = await session.execute(
        select(Location).where(Location.lat.isnot(None), Location.lng.isnot(None))
    )
    location_objs = result.scalars().all()

    locations: dict[int, dict[str, Any]] = {}
    for loc in location_objs:
        locations[loc.id] = {
            "id": loc.id,
            "name": loc.name,
            "short_name": loc.short_name,
            "address": loc.address,
            "lat": float(loc.lat) if loc.lat else None,
            "lng": float(loc.lng) if loc.lng else None,
            "emoji": loc.emoji,
            "alternate_names": [],
            "website_scoped_names": {},
        }

    # Get all alternate names
    alt_result = await session.execute(select(LocationAlternateName))
    alt_names: list[LocationAlternateName] = list(alt_result.scalars().all())

    for alt in alt_names:
        if alt.location_id in locations:
            if alt.website_id is None:
                locations[alt.location_id]["alternate_names"].append(alt.alternate_name)
            else:
                locations[alt.location_id]["website_scoped_names"].setdefault(
                    alt.website_id, []
                ).append(alt.alternate_name)

    return list(locations.values())


async def get_tag_rules(
    session: AsyncSession,
) -> TagRules:
    """Get tag processing rules from the database."""
    rewrite: dict[str, str] = {}
    exclude: list[str] = []
    remove: list[str] = []

    result = await session.execute(
        select(TagRule).order_by(TagRule.rule_type, TagRule.pattern)
    )
    rules = result.scalars().all()

    for rule in rules:
        if rule.rule_type == TagRuleType.rewrite:
            rewrite[rule.pattern] = rule.replacement or ""
        elif rule.rule_type == TagRuleType.exclude:
            exclude.append(rule.pattern)
        elif rule.rule_type == TagRuleType.remove:
            remove.append(rule.pattern)

    return {"rewrite": rewrite, "exclude": exclude, "remove": remove}


async def get_websites_with_tags(
    session: AsyncSession,
) -> dict[str, list[str]]:
    """Get all websites with their URLs and extra tags.

    Returns a dict mapping URL (lowercase, no trailing slash) to list of extra tags.
    """
    from api.models import WebsiteTag, Tag

    stmt = (
        select(WebsiteUrl.url, Tag.name)
        .join(Website, WebsiteUrl.website_id == Website.id)
        .outerjoin(WebsiteTag, Website.id == WebsiteTag.website_id)
        .outerjoin(Tag, WebsiteTag.tag_id == Tag.id)
        .where(Website.disabled == False)  # noqa: E712
        .order_by(WebsiteUrl.website_id, WebsiteUrl.sort_order)
    )

    result = await session.execute(stmt)
    rows = result.all()

    websites_map: dict[str, list[str]] = {}
    for url, tag_name in rows:
        normalized_url = url.rstrip("/").lower()
        if normalized_url not in websites_map:
            websites_map[normalized_url] = []
        if tag_name and tag_name not in websites_map[normalized_url]:
            websites_map[normalized_url].append(tag_name)

    return websites_map
