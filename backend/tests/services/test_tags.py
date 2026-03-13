"""Tests for the tag get-or-create helper."""

import pytest
from api.services.tags import get_or_create_tag


class TestGetOrCreateTag:
    @pytest.mark.asyncio
    async def test_creates_new_tag(self, db_session):
        tag = await get_or_create_tag(db_session, "live-music")

        assert tag is not None
        assert tag.name == "live-music"
        assert tag.id is not None

    @pytest.mark.asyncio
    async def test_returns_existing_tag(self, db_session):
        tag1 = await get_or_create_tag(db_session, "dance")
        tag2 = await get_or_create_tag(db_session, "dance")

        assert tag1.id == tag2.id
        assert tag1.name == tag2.name

    @pytest.mark.asyncio
    async def test_different_names_create_different_tags(self, db_session):
        tag_a = await get_or_create_tag(db_session, "art")
        tag_b = await get_or_create_tag(db_session, "music")

        assert tag_a.id != tag_b.id
