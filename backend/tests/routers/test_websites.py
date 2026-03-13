"""Tests for the websites router."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from api.database import get_db
from api.dependencies import create_access_token, hash_password
from api.models.event import Event
from api.models.location import Location
from api.models.tag import Tag
from api.models.user import User
from api.models.website import Website, WebsiteLocation, WebsiteTag, WebsiteUrl
from api.routers.websites import router
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def _make_app(db_session: AsyncSession) -> FastAPI:
    """Create a minimal FastAPI app with the websites router for testing."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = _make_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create a user with a hashed password for auth tests."""
    user = User(
        email="webtest@example.com",
        display_name="Web Test User",
        password_hash=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(sample_user: User) -> dict[str, str]:
    """Return Authorization headers with a valid Bearer token."""
    token = create_access_token(sample_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_location(db_session: AsyncSession) -> Location:
    """Create a location for testing location_ids."""
    location = Location(name="Test Gallery", address="123 Art St")
    db_session.add(location)
    await db_session.flush()
    return location


@pytest_asyncio.fixture
async def sample_website(db_session: AsyncSession) -> Website:
    """Create a website in the DB for read/update/delete tests."""
    website = Website(
        name="Alpha Site",
        description="A test website",
        base_url="https://alpha.example.com",
    )
    db_session.add(website)
    await db_session.flush()

    # Add a URL
    db_session.add(
        WebsiteUrl(
            website_id=website.id, url="https://alpha.example.com/events", sort_order=0
        )
    )
    await db_session.flush()
    return website


@pytest_asyncio.fixture
async def sample_website_with_event(
    db_session: AsyncSession, sample_website: Website
) -> Website:
    """Create a website with an associated event (for delete guard testing)."""
    event = Event(name="Test Event", website_id=sample_website.id)
    db_session.add(event)
    await db_session.flush()
    return sample_website


# ── List Websites ─────────────────────────────────────────────────────


class TestListWebsites:
    @pytest.mark.asyncio
    async def test_list_websites_empty(self, client: AsyncClient) -> None:
        # Act
        resp = await client.get("/api/v1/websites/")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["total"] == 0

    @pytest.mark.asyncio
    async def test_list_websites_returns_items(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Arrange — two websites, should be sorted by name
        ws_b = Website(name="Bravo Site", base_url="https://bravo.example.com")
        ws_a = Website(name="Alpha Site", base_url="https://alpha.example.com")
        db_session.add_all([ws_b, ws_a])
        await db_session.flush()

        # Add one event to ws_a to verify event_count
        event = Event(name="Some Event", website_id=ws_a.id)
        db_session.add(event)
        await db_session.flush()

        # Act
        resp = await client.get("/api/v1/websites/")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["data"]) == 2
        # Sorted by name: Alpha before Bravo
        assert body["data"][0]["name"] == "Alpha Site"
        assert body["data"][1]["name"] == "Bravo Site"
        # event_count check
        assert body["data"][0]["event_count"] == 1
        assert body["data"][1]["event_count"] == 0

    @pytest.mark.asyncio
    async def test_list_websites_pagination(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Arrange — create 3 websites
        for i in range(3):
            db_session.add(Website(name=f"Site {i:02d}"))
        await db_session.flush()

        # Act — request with limit=2, offset=0
        resp1 = await client.get("/api/v1/websites/", params={"limit": 2, "offset": 0})
        # Act — request with limit=2, offset=2
        resp2 = await client.get("/api/v1/websites/", params={"limit": 2, "offset": 2})

        # Assert
        body1 = resp1.json()
        body2 = resp2.json()
        assert body1["total"] == 3
        assert len(body1["data"]) == 2
        assert body2["total"] == 3
        assert len(body2["data"]) == 1


# ── Get Website Detail ────────────────────────────────────────────────


class TestGetWebsite:
    @pytest.mark.asyncio
    async def test_get_website_returns_detail(
        self, client: AsyncClient, db_session: AsyncSession, sample_website: Website
    ) -> None:
        # Arrange — add a tag and a location to the website
        tag = Tag(name="art")
        db_session.add(tag)
        await db_session.flush()
        db_session.add(WebsiteTag(website_id=sample_website.id, tag_id=tag.id))

        location = Location(name="Gallery X")
        db_session.add(location)
        await db_session.flush()
        db_session.add(
            WebsiteLocation(website_id=sample_website.id, location_id=location.id)
        )
        await db_session.flush()

        # Act
        resp = await client.get(f"/api/v1/websites/{sample_website.id}")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == sample_website.id
        assert body["name"] == "Alpha Site"
        assert isinstance(body["urls"], list)
        assert len(body["urls"]) >= 1
        assert body["urls"][0]["url"] == "https://alpha.example.com/events"
        assert isinstance(body["locations"], list)
        assert len(body["locations"]) == 1
        assert body["locations"][0]["name"] == "Gallery X"
        assert isinstance(body["tags"], list)
        assert len(body["tags"]) == 1
        assert body["tags"][0]["name"] == "art"

    @pytest.mark.asyncio
    async def test_get_website_not_found(self, client: AsyncClient) -> None:
        # Act
        resp = await client.get("/api/v1/websites/99999")

        # Assert
        assert resp.status_code == 404


# ── Get Website History ───────────────────────────────────────────────


class TestGetWebsiteHistory:
    @pytest.mark.asyncio
    async def test_get_history_requires_auth(
        self, client: AsyncClient, sample_website: Website
    ) -> None:
        # Act — no auth header
        resp = await client.get(f"/api/v1/websites/{sample_website.id}/history")

        # Assert
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_history_returns_edits(
        self,
        client: AsyncClient,
        sample_website: Website,
        auth_headers: dict[str, str],
    ) -> None:
        # Act
        resp = await client.get(
            f"/api/v1/websites/{sample_website.id}/history",
            headers=auth_headers,
        )

        # Assert — no edits logged yet, but the response should be a list
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)


# ── Create Website ────────────────────────────────────────────────────


class TestCreateWebsite:
    @pytest.mark.asyncio
    async def test_create_website_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Arrange
        payload = {"name": "New Website"}

        # Act
        resp = await client.post(
            "/api/v1/websites/", json=payload, headers=auth_headers
        )

        # Assert
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "New Website"
        assert "id" in body
        assert "created_at" in body

    @pytest.mark.asyncio
    async def test_create_website_with_urls_and_tags(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Arrange
        payload = {
            "name": "Tagged Site",
            "urls": ["https://example.com/page1", "https://example.com/page2"],
            "tags": ["music", "dance"],
        }

        # Act
        resp = await client.post(
            "/api/v1/websites/", json=payload, headers=auth_headers
        )

        # Assert
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["urls"]) == 2
        assert body["urls"][0]["url"] == "https://example.com/page1"
        assert body["urls"][1]["url"] == "https://example.com/page2"
        tag_names = sorted(t["name"] for t in body["tags"])
        assert tag_names == ["dance", "music"]

    @pytest.mark.asyncio
    async def test_create_website_with_location_ids(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_location: Location,
    ) -> None:
        # Arrange
        payload = {
            "name": "Located Site",
            "location_ids": [sample_location.id],
        }

        # Act
        resp = await client.post(
            "/api/v1/websites/", json=payload, headers=auth_headers
        )

        # Assert
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["locations"]) == 1
        assert body["locations"][0]["id"] == sample_location.id

    @pytest.mark.asyncio
    async def test_create_website_invalid_location_id(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Arrange — use a non-existent location id
        payload = {
            "name": "Bad Location Site",
            "location_ids": [999999],
        }

        # Act
        resp = await client.post(
            "/api/v1/websites/", json=payload, headers=auth_headers
        )

        # Assert
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_website_requires_auth(self, client: AsyncClient) -> None:
        # Arrange
        payload = {"name": "No Auth Site"}

        # Act — no auth header
        resp = await client.post("/api/v1/websites/", json=payload)

        # Assert
        assert resp.status_code == 401


# ── Update Website ────────────────────────────────────────────────────


class TestUpdateWebsite:
    @pytest.mark.asyncio
    async def test_update_website_partial(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_website: Website,
    ) -> None:
        # Arrange — only update description
        payload = {"description": "Updated description"}

        # Act
        resp = await client.put(
            f"/api/v1/websites/{sample_website.id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["description"] == "Updated description"
        # Name should remain unchanged
        assert body["name"] == "Alpha Site"

    @pytest.mark.asyncio
    async def test_update_website_replaces_urls(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_website: Website,
    ) -> None:
        # Arrange — replace urls
        payload = {"urls": ["https://new.example.com/a", "https://new.example.com/b"]}

        # Act
        resp = await client.put(
            f"/api/v1/websites/{sample_website.id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        urls = [u["url"] for u in body["urls"]]
        assert urls == ["https://new.example.com/a", "https://new.example.com/b"]

    @pytest.mark.asyncio
    async def test_update_website_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Act
        resp = await client.put(
            "/api/v1/websites/99999",
            json={"name": "Ghost"},
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_website_requires_auth(
        self, client: AsyncClient, sample_website: Website
    ) -> None:
        # Act — no auth header
        resp = await client.put(
            f"/api/v1/websites/{sample_website.id}",
            json={"name": "Hacked"},
        )

        # Assert
        assert resp.status_code == 401


# ── Delete Website ────────────────────────────────────────────────────


class TestDeleteWebsite:
    @pytest.mark.asyncio
    async def test_delete_website_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_website: Website,
    ) -> None:
        # Act
        resp = await client.delete(
            f"/api/v1/websites/{sample_website.id}",
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 204

        # Verify it's actually gone
        get_resp = await client.get(f"/api/v1/websites/{sample_website.id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_website_with_events_returns_409(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_website_with_event: Website,
    ) -> None:
        # Act
        resp = await client.delete(
            f"/api/v1/websites/{sample_website_with_event.id}",
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 409
        assert "events" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_website_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Act
        resp = await client.delete(
            "/api/v1/websites/99999",
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_website_requires_auth(
        self, client: AsyncClient, sample_website: Website
    ) -> None:
        # Act — no auth header
        resp = await client.delete(f"/api/v1/websites/{sample_website.id}")

        # Assert
        assert resp.status_code == 401
