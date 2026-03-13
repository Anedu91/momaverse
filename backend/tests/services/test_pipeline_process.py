"""Tests for pipeline process service (SQLAlchemy)."""

import pytest
from api.models import (
    Location,
    LocationAlternateName,
    Tag,
    TagRule,
    Website,
    WebsiteTag,
    WebsiteUrl,
)
from api.models.base import TagRuleType
from pipeline.db import (
    get_all_locations,
    get_tag_rules,
    get_websites_with_tags,
)


class TestGetAllLocations:
    @pytest.mark.asyncio
    async def test_returns_locations_with_lat_lng(self, db_session):
        loc = Location(name="MoMA PS1", lat=40.7, lng=-73.9, emoji="🏛️")
        db_session.add(loc)
        await db_session.flush()

        result = await get_all_locations(db_session)
        assert len(result) >= 1
        match = [r for r in result if r["name"] == "MoMA PS1"]
        assert len(match) == 1
        assert match[0]["lat"] == 40.7
        assert match[0]["lng"] == -73.9

    @pytest.mark.asyncio
    async def test_excludes_locations_without_lat_lng(self, db_session):
        loc = Location(name="No Coords")
        db_session.add(loc)
        await db_session.flush()

        result = await get_all_locations(db_session)
        match = [r for r in result if r["name"] == "No Coords"]
        assert len(match) == 0

    @pytest.mark.asyncio
    async def test_includes_alternate_names(self, db_session):
        loc = Location(name="The Shed", lat=40.75, lng=-74.0)
        db_session.add(loc)
        await db_session.flush()

        alt = LocationAlternateName(
            location_id=loc.id, alternate_name="Hudson Yards Shed"
        )
        db_session.add(alt)
        await db_session.flush()

        result = await get_all_locations(db_session)
        match = [r for r in result if r["name"] == "The Shed"][0]
        assert "Hudson Yards Shed" in match["alternate_names"]

    @pytest.mark.asyncio
    async def test_includes_website_scoped_names(self, db_session):
        loc = Location(name="Venue X", lat=40.0, lng=-74.0)
        db_session.add(loc)
        w = Website(name="Site A", disabled=False)
        db_session.add(w)
        await db_session.flush()

        alt = LocationAlternateName(
            location_id=loc.id, alternate_name="Venue X Alt", website_id=w.id
        )
        db_session.add(alt)
        await db_session.flush()

        result = await get_all_locations(db_session)
        match = [r for r in result if r["name"] == "Venue X"][0]
        assert w.id in match["website_scoped_names"]
        assert "Venue X Alt" in match["website_scoped_names"][w.id]


class TestGetTagRules:
    @pytest.mark.asyncio
    async def test_returns_rewrite_rules(self, db_session):
        rule = TagRule(
            rule_type=TagRuleType.rewrite, pattern="hip hop", replacement="hip-hop"
        )
        db_session.add(rule)
        await db_session.flush()

        result = await get_tag_rules(db_session)
        assert result["rewrite"]["hip hop"] == "hip-hop"

    @pytest.mark.asyncio
    async def test_returns_exclude_rules(self, db_session):
        rule = TagRule(rule_type=TagRuleType.exclude, pattern="internal")
        db_session.add(rule)
        await db_session.flush()

        result = await get_tag_rules(db_session)
        assert "internal" in result["exclude"]

    @pytest.mark.asyncio
    async def test_returns_remove_rules(self, db_session):
        rule = TagRule(rule_type=TagRuleType.remove, pattern="spam")
        db_session.add(rule)
        await db_session.flush()

        result = await get_tag_rules(db_session)
        assert "spam" in result["remove"]

    @pytest.mark.asyncio
    async def test_empty_when_no_rules(self, db_session):
        result = await get_tag_rules(db_session)
        assert result == {"rewrite": {}, "exclude": [], "remove": []}


class TestGetWebsitesWithTags:
    @pytest.mark.asyncio
    async def test_returns_url_to_tags_mapping(self, db_session):
        w = Website(name="Tagged Site", disabled=False)
        db_session.add(w)
        await db_session.flush()

        url = WebsiteUrl(
            website_id=w.id, url="https://example.com/events/", sort_order=0
        )
        tag = Tag(name="music")
        db_session.add_all([url, tag])
        await db_session.flush()

        wt = WebsiteTag(website_id=w.id, tag_id=tag.id)
        db_session.add(wt)
        await db_session.flush()

        result = await get_websites_with_tags(db_session)
        assert "https://example.com/events" in result
        assert "music" in result["https://example.com/events"]

    @pytest.mark.asyncio
    async def test_excludes_disabled_websites(self, db_session):
        w = Website(name="Disabled Site", disabled=True)
        db_session.add(w)
        await db_session.flush()

        url = WebsiteUrl(website_id=w.id, url="https://disabled.com", sort_order=0)
        db_session.add(url)
        await db_session.flush()

        result = await get_websites_with_tags(db_session)
        assert "https://disabled.com" not in result

    @pytest.mark.asyncio
    async def test_url_without_tags_has_empty_list(self, db_session):
        w = Website(name="No Tags Site", disabled=False)
        db_session.add(w)
        await db_session.flush()

        url = WebsiteUrl(website_id=w.id, url="https://notags.com/", sort_order=0)
        db_session.add(url)
        await db_session.flush()

        result = await get_websites_with_tags(db_session)
        assert "https://notags.com" in result
        assert result["https://notags.com"] == []
