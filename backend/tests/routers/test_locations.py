"""Tests for the locations router."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from api.database import get_db
from api.dependencies import create_access_token, hash_password
from api.models.event import Event
from api.models.location import Location, LocationAlternateName, LocationTag
from api.models.tag import Tag
from api.models.user import User
from api.routers.locations import router
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def _make_app(db_session: AsyncSession) -> FastAPI:
    """Create a minimal FastAPI app with the locations router for testing."""
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
    """Create a user for authenticated requests."""
    user = User(
        email="testuser@example.com",
        display_name="Test User",
        password_hash=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(sample_user: User) -> dict[str, str]:
    """Return Authorization header dict for the sample_user."""
    token = create_access_token(sample_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_location(db_session: AsyncSession) -> Location:
    """Create a single location in the DB."""
    location = Location(
        name="Museum of Modern Art",
        short_name="MoMA",
        very_short_name="MoMA",
        address="11 W 53rd St, New York",
        description="A famous museum.",
        lat=40.7614,
        lng=-73.9776,
        emoji="x",
    )
    db_session.add(location)
    await db_session.flush()
    return location


@pytest_asyncio.fixture
async def sample_location_with_event(
    db_session: AsyncSession, sample_location: Location
) -> Location:
    """Create a location that has an event referencing it."""
    event = Event(
        name="Art Exhibition",
        location_id=sample_location.id,
    )
    db_session.add(event)
    await db_session.flush()
    return sample_location


# ---------------------------------------------------------------------------
# List locations
# ---------------------------------------------------------------------------


class TestListLocations:
    @pytest.mark.asyncio
    async def test_list_locations_empty(self, client: AsyncClient) -> None:
        # Act
        resp = await client.get("/api/v1/locations/")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["total"] == 0

    @pytest.mark.asyncio
    async def test_list_locations_returns_items(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Arrange
        loc_b = Location(name="Brooklyn Museum")
        loc_a = Location(name="American Museum")
        db_session.add_all([loc_b, loc_a])
        await db_session.flush()

        # Act
        resp = await client.get("/api/v1/locations/")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        names = [item["name"] for item in body["data"]]
        assert names == ["American Museum", "Brooklyn Museum"]

    @pytest.mark.asyncio
    async def test_list_locations_includes_event_count(
        self, client: AsyncClient, sample_location_with_event: Location
    ) -> None:
        # Act
        resp = await client.get("/api/v1/locations/")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["event_count"] == 1

    @pytest.mark.asyncio
    async def test_list_locations_pagination(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Arrange — create 3 locations
        for name in ["Alpha", "Beta", "Gamma"]:
            db_session.add(Location(name=name))
        await db_session.flush()

        # Act — fetch with limit=2, offset=0
        resp1 = await client.get("/api/v1/locations/", params={"limit": 2, "offset": 0})
        # Act — fetch with limit=2, offset=2
        resp2 = await client.get("/api/v1/locations/", params={"limit": 2, "offset": 2})

        # Assert
        body1 = resp1.json()
        body2 = resp2.json()
        assert body1["total"] == 3
        assert len(body1["data"]) == 2
        assert body2["total"] == 3
        assert len(body2["data"]) == 1
        # All three names covered
        all_names = [i["name"] for i in body1["data"]] + [
            i["name"] for i in body2["data"]
        ]
        assert sorted(all_names) == ["Alpha", "Beta", "Gamma"]


# ---------------------------------------------------------------------------
# Get location detail
# ---------------------------------------------------------------------------


class TestGetLocationDetail:
    @pytest.mark.asyncio
    async def test_get_location_returns_detail(
        self, client: AsyncClient, db_session: AsyncSession, sample_location: Location
    ) -> None:
        # Arrange — add alternate name and tag
        db_session.add(
            LocationAlternateName(
                location_id=sample_location.id, alternate_name="MoMA NYC"
            )
        )
        tag = Tag(name="art")
        db_session.add(tag)
        await db_session.flush()
        db_session.add(LocationTag(location_id=sample_location.id, tag_id=tag.id))
        await db_session.flush()

        # Act
        resp = await client.get(f"/api/v1/locations/{sample_location.id}")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == sample_location.id
        assert body["name"] == "Museum of Modern Art"
        assert len(body["alternate_names"]) == 1
        assert body["alternate_names"][0]["alternate_name"] == "MoMA NYC"
        assert len(body["tags"]) == 1
        assert body["tags"][0]["name"] == "art"

    @pytest.mark.asyncio
    async def test_get_location_not_found(self, client: AsyncClient) -> None:
        # Act
        resp = await client.get("/api/v1/locations/99999")

        # Assert
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Create location
# ---------------------------------------------------------------------------


class TestCreateLocation:
    @pytest.mark.asyncio
    async def test_create_location_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Arrange
        payload = {
            "name": "New Gallery",
            "short_name": "NG",
            "address": "123 Art St",
            "lat": 40.0,
            "lng": -74.0,
        }

        # Act
        resp = await client.post(
            "/api/v1/locations/", json=payload, headers=auth_headers
        )

        # Assert
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "New Gallery"
        assert body["short_name"] == "NG"
        assert body["address"] == "123 Art St"
        assert body["lat"] == 40.0
        assert body["lng"] == -74.0
        assert "id" in body
        assert "created_at" in body

    @pytest.mark.asyncio
    async def test_create_location_with_tags_and_alt_names(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Arrange
        payload = {
            "name": "Tagged Venue",
            "alternate_names": ["TV", "The Venue"],
            "tags": ["music", "nightlife"],
        }

        # Act
        resp = await client.post(
            "/api/v1/locations/", json=payload, headers=auth_headers
        )

        # Assert
        assert resp.status_code == 201
        body = resp.json()
        alt_names = [a["alternate_name"] for a in body["alternate_names"]]
        assert "TV" in alt_names
        assert "The Venue" in alt_names
        tag_names = [t["name"] for t in body["tags"]]
        assert "music" in tag_names
        assert "nightlife" in tag_names

    @pytest.mark.asyncio
    async def test_create_location_requires_auth(self, client: AsyncClient) -> None:
        # Arrange
        payload = {"name": "Unauthorized Venue"}

        # Act
        resp = await client.post("/api/v1/locations/", json=payload)

        # Assert
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Update location
# ---------------------------------------------------------------------------


class TestUpdateLocation:
    @pytest.mark.asyncio
    async def test_update_location_partial(
        self,
        client: AsyncClient,
        sample_location: Location,
        auth_headers: dict[str, str],
    ) -> None:
        # Arrange — only update the name
        payload = {"name": "Updated Museum Name"}

        # Act
        resp = await client.put(
            f"/api/v1/locations/{sample_location.id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Updated Museum Name"
        # Other fields remain unchanged
        assert body["short_name"] == "MoMA"
        assert body["address"] == "11 W 53rd St, New York"

    @pytest.mark.asyncio
    async def test_update_location_replaces_tags(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_location: Location,
        auth_headers: dict[str, str],
    ) -> None:
        # Arrange — give the location an initial tag
        tag = Tag(name="old-tag")
        db_session.add(tag)
        await db_session.flush()
        db_session.add(LocationTag(location_id=sample_location.id, tag_id=tag.id))
        await db_session.flush()

        # Act — update with new tags
        payload = {"tags": ["new-tag-a", "new-tag-b"]}
        resp = await client.put(
            f"/api/v1/locations/{sample_location.id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        tag_names = sorted(t["name"] for t in body["tags"])
        assert tag_names == ["new-tag-a", "new-tag-b"]

    @pytest.mark.asyncio
    async def test_update_location_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Act
        resp = await client.put(
            "/api/v1/locations/99999",
            json={"name": "Ghost"},
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_location_requires_auth(
        self, client: AsyncClient, sample_location: Location
    ) -> None:
        # Act
        resp = await client.put(
            f"/api/v1/locations/{sample_location.id}",
            json={"name": "No Auth"},
        )

        # Assert
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Delete location
# ---------------------------------------------------------------------------


class TestDeleteLocation:
    @pytest.mark.asyncio
    async def test_delete_location_success(
        self,
        client: AsyncClient,
        sample_location: Location,
        auth_headers: dict[str, str],
    ) -> None:
        # Act
        resp = await client.delete(
            f"/api/v1/locations/{sample_location.id}",
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get(f"/api/v1/locations/{sample_location.id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_location_with_events_returns_409(
        self,
        client: AsyncClient,
        sample_location_with_event: Location,
        auth_headers: dict[str, str],
    ) -> None:
        # Act
        resp = await client.delete(
            f"/api/v1/locations/{sample_location_with_event.id}",
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 409
        assert "associated events" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_location_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Act
        resp = await client.delete(
            "/api/v1/locations/99999",
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_location_requires_auth(
        self, client: AsyncClient, sample_location: Location
    ) -> None:
        # Act
        resp = await client.delete(f"/api/v1/locations/{sample_location.id}")

        # Assert
        assert resp.status_code == 401
