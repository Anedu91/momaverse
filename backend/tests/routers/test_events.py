"""Tests for the events router."""

from collections.abc import AsyncGenerator
from datetime import date, timedelta

import pytest
import pytest_asyncio
from api.database import get_db
from api.dependencies import create_access_token, hash_password
from api.models.event import Event, EventOccurrence, EventTag, EventUrl
from api.models.location import Location
from api.models.tag import Tag
from api.models.user import User
from api.models.website import Website
from api.routers.events import router
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

PREFIX = "/api/v1/events"


def _make_app(db_session: AsyncSession) -> FastAPI:
    """Create a minimal FastAPI app with the events router for testing."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = _make_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    user = User(
        email="events-test@example.com",
        display_name="Events Tester",
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(sample_user: User) -> dict[str, str]:
    token = create_access_token(sample_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_location(db_session: AsyncSession) -> Location:
    loc = Location(name="Test Venue", short_name="TV")
    db_session.add(loc)
    await db_session.flush()
    return loc


@pytest_asyncio.fixture
async def sample_website(db_session: AsyncSession) -> Website:
    ws = Website(name="Test Website")
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest_asyncio.fixture
async def sample_event(db_session: AsyncSession) -> Event:
    event = Event(name="Sample Event", description="A test event")
    db_session.add(event)
    await db_session.flush()
    return event


@pytest_asyncio.fixture
async def sample_event_with_occurrence(db_session: AsyncSession) -> Event:
    """An event with a future occurrence (for upcoming filter tests)."""
    event = Event(name="Upcoming Event")
    db_session.add(event)
    await db_session.flush()

    future_date = date.today() + timedelta(days=30)
    occ = EventOccurrence(
        event_id=event.id,
        start_date=future_date,
        sort_order=0,
    )
    db_session.add(occ)
    await db_session.flush()
    return event


# ---------------------------------------------------------------------------
# List events
# ---------------------------------------------------------------------------


class TestListEvents:
    @pytest.mark.asyncio
    async def test_list_events_empty(self, client: AsyncClient) -> None:
        # Act
        resp = await client.get(f"{PREFIX}/")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["total"] == 0

    @pytest.mark.asyncio
    async def test_list_events_returns_items(
        self, client: AsyncClient, sample_event: Event
    ) -> None:
        # Act
        resp = await client.get(f"{PREFIX}/")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        names = [item["name"] for item in body["data"]]
        assert "Sample Event" in names

    @pytest.mark.asyncio
    async def test_list_events_upcoming_filter(
        self,
        client: AsyncClient,
        sample_event: Event,
        sample_event_with_occurrence: Event,
    ) -> None:
        # Act — only events with a future occurrence
        resp = await client.get(f"{PREFIX}/", params={"upcoming": True})

        # Assert
        body = resp.json()
        names = [item["name"] for item in body["data"]]
        assert "Upcoming Event" in names
        # sample_event has no occurrences, so it should not appear
        assert "Sample Event" not in names

    @pytest.mark.asyncio
    async def test_list_events_location_filter(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_location: Location,
    ) -> None:
        # Arrange — event linked to the location
        event = Event(name="Located Event", location_id=sample_location.id)
        db_session.add(event)
        await db_session.flush()

        # Also create an unlinked event
        other = Event(name="Other Event")
        db_session.add(other)
        await db_session.flush()

        # Act
        resp = await client.get(
            f"{PREFIX}/", params={"location_id": sample_location.id}
        )

        # Assert
        body = resp.json()
        names = [item["name"] for item in body["data"]]
        assert "Located Event" in names
        assert "Other Event" not in names

    @pytest.mark.asyncio
    async def test_list_events_pagination(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Arrange — create 3 events
        for i in range(3):
            db_session.add(Event(name=f"Page Event {i}"))
        await db_session.flush()

        # Act — page with limit=2, offset=0
        resp1 = await client.get(f"{PREFIX}/", params={"limit": 2, "offset": 0})
        body1 = resp1.json()
        assert len(body1["data"]) == 2

        # Act — page with offset=2
        resp2 = await client.get(f"{PREFIX}/", params={"limit": 2, "offset": 2})
        body2 = resp2.json()
        assert len(body2["data"]) == 1

        # Total should be consistent
        assert body1["total"] == 3
        assert body2["total"] == 3


# ---------------------------------------------------------------------------
# Get event detail
# ---------------------------------------------------------------------------


class TestGetEvent:
    @pytest.mark.asyncio
    async def test_get_event_returns_detail(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Arrange — event with occurrence, url, and tag
        event = Event(name="Detail Event")
        db_session.add(event)
        await db_session.flush()

        db_session.add(
            EventOccurrence(
                event_id=event.id,
                start_date=date(2025, 7, 1),
                sort_order=0,
            )
        )
        db_session.add(
            EventUrl(event_id=event.id, url="https://example.com", sort_order=0)
        )

        tag = Tag(name="music")
        db_session.add(tag)
        await db_session.flush()
        db_session.add(EventTag(event_id=event.id, tag_id=tag.id))
        await db_session.flush()

        # Act
        resp = await client.get(f"{PREFIX}/{event.id}")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Detail Event"
        assert len(body["occurrences"]) == 1
        assert body["occurrences"][0]["start_date"] == "2025-07-01"
        assert len(body["urls"]) == 1
        assert body["urls"][0]["url"] == "https://example.com"
        assert len(body["tags"]) == 1
        assert body["tags"][0]["name"] == "music"

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, client: AsyncClient) -> None:
        # Act
        resp = await client.get(f"{PREFIX}/99999")

        # Assert
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Get event history
# ---------------------------------------------------------------------------


class TestGetEventHistory:
    @pytest.mark.asyncio
    async def test_get_history_requires_auth(
        self, client: AsyncClient, sample_event: Event
    ) -> None:
        # Act — no auth header
        resp = await client.get(f"{PREFIX}/{sample_event.id}/history")

        # Assert
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_history_returns_edits(
        self,
        client: AsyncClient,
        sample_event: Event,
        auth_headers: dict[str, str],
    ) -> None:
        # Act
        resp = await client.get(
            f"{PREFIX}/{sample_event.id}/history", headers=auth_headers
        )

        # Assert — even if empty, should be a list
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)


# ---------------------------------------------------------------------------
# Create event
# ---------------------------------------------------------------------------


class TestCreateEvent:
    @pytest.mark.asyncio
    async def test_create_event_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Arrange
        payload = {"name": "New Event"}

        # Act
        resp = await client.post(f"{PREFIX}/", json=payload, headers=auth_headers)

        # Assert
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "New Event"
        assert "id" in body

    @pytest.mark.asyncio
    async def test_create_event_with_occurrences_and_urls(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Arrange
        payload = {
            "name": "Full Event",
            "occurrences": [
                {"start_date": "2025-08-01", "start_time": "18:00"},
                {"start_date": "2025-08-02"},
            ],
            "urls": ["https://example.com/event1", "https://example.com/event2"],
            "tags": ["art", "free"],
        }

        # Act
        resp = await client.post(f"{PREFIX}/", json=payload, headers=auth_headers)

        # Assert
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["occurrences"]) == 2
        assert body["occurrences"][0]["start_date"] == "2025-08-01"
        assert body["occurrences"][0]["start_time"] == "18:00"
        assert len(body["urls"]) == 2
        assert len(body["tags"]) == 2
        tag_names = sorted(t["name"] for t in body["tags"])
        assert tag_names == ["art", "free"]

    @pytest.mark.asyncio
    async def test_create_event_with_invalid_location_id(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Arrange — reference a non-existent location
        payload = {"name": "Bad Location Event", "location_id": 99999}

        # Act
        resp = await client.post(f"{PREFIX}/", json=payload, headers=auth_headers)

        # Assert
        assert resp.status_code == 422
        assert "Location" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_event_requires_auth(self, client: AsyncClient) -> None:
        # Act — no auth header
        resp = await client.post(f"{PREFIX}/", json={"name": "No Auth"})

        # Assert
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_event_with_valid_location(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_location: Location,
    ) -> None:
        # Arrange
        payload = {"name": "Located Event", "location_id": sample_location.id}

        # Act
        resp = await client.post(f"{PREFIX}/", json=payload, headers=auth_headers)

        # Assert
        assert resp.status_code == 201
        body = resp.json()
        assert body["location_id"] == sample_location.id


# ---------------------------------------------------------------------------
# Update event
# ---------------------------------------------------------------------------


class TestUpdateEvent:
    @pytest.mark.asyncio
    async def test_update_event_partial(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_event: Event,
    ) -> None:
        # Act — only update name
        resp = await client.put(
            f"{PREFIX}/{sample_event.id}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Updated Name"
        # Description should remain unchanged
        assert body["description"] == "A test event"

    @pytest.mark.asyncio
    async def test_update_event_replaces_occurrences(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        # Arrange — event with an existing occurrence
        event = Event(name="Occ Event")
        db_session.add(event)
        await db_session.flush()

        db_session.add(
            EventOccurrence(
                event_id=event.id,
                start_date=date(2025, 1, 1),
                sort_order=0,
            )
        )
        await db_session.flush()

        # Act — replace occurrences with a new set
        resp = await client.put(
            f"{PREFIX}/{event.id}",
            json={
                "occurrences": [
                    {"start_date": "2025-09-01"},
                    {"start_date": "2025-09-02"},
                ]
            },
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["occurrences"]) == 2
        occ_dates = sorted(o["start_date"] for o in body["occurrences"])
        assert occ_dates == ["2025-09-01", "2025-09-02"]

    @pytest.mark.asyncio
    async def test_update_event_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Act
        resp = await client.put(
            f"{PREFIX}/99999",
            json={"name": "Ghost"},
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_event_requires_auth(
        self, client: AsyncClient, sample_event: Event
    ) -> None:
        # Act — no auth header
        resp = await client.put(f"{PREFIX}/{sample_event.id}", json={"name": "No Auth"})

        # Assert
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Delete event
# ---------------------------------------------------------------------------


class TestDeleteEvent:
    @pytest.mark.asyncio
    async def test_delete_event_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_event: Event,
    ) -> None:
        # Act
        resp = await client.delete(f"{PREFIX}/{sample_event.id}", headers=auth_headers)

        # Assert
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get(f"{PREFIX}/{sample_event.id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_event_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Act
        resp = await client.delete(f"{PREFIX}/99999", headers=auth_headers)

        # Assert
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_event_requires_auth(
        self, client: AsyncClient, sample_event: Event
    ) -> None:
        # Act — no auth header
        resp = await client.delete(f"{PREFIX}/{sample_event.id}")

        # Assert
        assert resp.status_code == 401
