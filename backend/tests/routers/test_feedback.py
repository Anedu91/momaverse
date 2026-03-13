"""Tests for the feedback router."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from api.database import get_db
from api.routers.feedback import router
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def _make_app(db_session: AsyncSession) -> FastAPI:
    """Create a minimal FastAPI app with the feedback router for testing."""
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


class TestCreateFeedbackHappyPath:
    @pytest.mark.asyncio
    async def test_returns_201_with_id_and_created_at(self, client):
        # Arrange
        payload = {"message": "Great site!"}

        # Act
        resp = await client.post("/api/v1/feedback/", json=payload)

        # Assert
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert "created_at" in body
        assert body["message"] == "Great site!"

    @pytest.mark.asyncio
    async def test_stores_page_url_when_provided(self, client):
        # Arrange
        payload = {
            "message": "Bug on this page",
            "page_url": "https://example.com/page",
        }

        # Act
        resp = await client.post("/api/v1/feedback/", json=payload)

        # Assert
        assert resp.status_code == 201
        body = resp.json()
        assert body["page_url"] == "https://example.com/page"

    @pytest.mark.asyncio
    async def test_captures_user_agent_header(self, client):
        # Arrange
        payload = {"message": "Feedback with UA"}
        headers = {"user-agent": "TestBrowser/1.0"}

        # Act
        resp = await client.post("/api/v1/feedback/", json=payload, headers=headers)

        # Assert
        assert resp.status_code == 201
        body = resp.json()
        assert body["user_agent"] == "TestBrowser/1.0"


class TestCreateFeedbackValidation:
    @pytest.mark.asyncio
    async def test_missing_message_returns_422(self, client):
        # Arrange
        payload: dict[str, str] = {}

        # Act
        resp = await client.post("/api/v1/feedback/", json=payload)

        # Assert
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_message_exceeding_max_length_returns_422(self, client):
        # Arrange
        payload = {"message": "x" * 10_001}

        # Act
        resp = await client.post("/api/v1/feedback/", json=payload)

        # Assert
        assert resp.status_code == 422
