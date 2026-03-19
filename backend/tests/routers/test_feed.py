"""Tests for the feed router."""

from collections.abc import AsyncGenerator
from datetime import date, timedelta

import pytest
import pytest_asyncio
from api.database import get_db
from api.models.base import EventStatus
from api.models.event import Event, EventOccurrence
from api.models.location import Location
from api.routers.feed import router
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def _make_app(db_session: AsyncSession) -> FastAPI:
    """Create a minimal FastAPI app with the feed router for testing."""
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


class TestFeedEvents:
    @pytest.mark.asyncio
    async def test_returns_200_with_list(self, client):
        # Act
        resp = await client.get("/api/v1/feed/events")

        # Assert
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_returns_event_with_future_occurrence(self, client, db_session):
        # Arrange
        location = Location(name="Test Venue", lat=40.7128, lng=-74.0060)
        db_session.add(location)
        await db_session.flush()

        event = Event(
            name="Test Event",
            location_id=location.id,
            status=EventStatus.active,
        )
        db_session.add(event)
        await db_session.flush()

        tomorrow = date.today() + timedelta(days=1)
        occurrence = EventOccurrence(
            event_id=event.id,
            start_date=tomorrow,
        )
        db_session.add(occurrence)
        await db_session.flush()

        # Act
        resp = await client.get("/api/v1/feed/events")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        names = [e["name"] for e in body]
        assert "Test Event" in names


class TestFeedLocations:
    @pytest.mark.asyncio
    async def test_returns_200_with_list(self, client):
        # Act
        resp = await client.get("/api/v1/feed/locations")

        # Assert
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_returns_location_with_coordinates(self, client, db_session):
        # Arrange
        location = Location(
            name="Test Location",
            lat=40.7128,
            lng=-74.0060,
            emoji="x",
            address="123 Test St",
        )
        db_session.add(location)
        await db_session.flush()

        # Act
        resp = await client.get("/api/v1/feed/locations")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        names = [loc["name"] for loc in body]
        assert "Test Location" in names
