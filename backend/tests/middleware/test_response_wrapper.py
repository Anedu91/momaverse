"""Tests for the ResponseWrapperMiddleware."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.middleware.response_wrapper import ResponseWrapperMiddleware


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with the middleware for testing."""
    app = FastAPI()
    app.add_middleware(ResponseWrapperMiddleware)

    @app.get("/api/v1/ok")
    async def ok():
        return {"message": "hello"}

    @app.get("/api/v1/list")
    async def list_endpoint():
        return [1, 2, 3]

    @app.get("/api/v1/error", status_code=400)
    async def bad_request():
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400,
            content={"detail": "bad input"},
        )

    @app.get("/api/v1/server-error", status_code=500)
    async def server_error():
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=500,
            content={"message": "internal"},
        )

    @app.get("/api/v1/plain")
    async def plain():
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse("plain text")

    @app.get("/outside/path")
    async def outside():
        return {"data": "not wrapped"}

    return app


@pytest.fixture
def test_app():
    return _make_app()


@pytest_asyncio.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestResponseWrapper2xx:
    @pytest.mark.asyncio
    async def test_wraps_dict_with_success_true(self, client):
        resp = await client.get("/api/v1/ok")
        body = resp.json()

        assert body["success"] is True
        assert body["message"] == "hello"

    @pytest.mark.asyncio
    async def test_wraps_list_response_with_data_key(self, client):
        resp = await client.get("/api/v1/list")
        body = resp.json()

        assert body["success"] is True
        assert body["data"] == [1, 2, 3]


class TestResponseWrapperErrors:
    @pytest.mark.asyncio
    async def test_wraps_400_with_success_false(self, client):
        resp = await client.get("/api/v1/error")
        body = resp.json()

        assert body["success"] is False
        assert body["error"] == "bad input"

    @pytest.mark.asyncio
    async def test_wraps_500_with_message_field(self, client):
        resp = await client.get("/api/v1/server-error")
        body = resp.json()

        assert body["success"] is False
        assert body["error"] == "internal"


class TestResponseWrapperPassthrough:
    @pytest.mark.asyncio
    async def test_non_json_passes_through(self, client):
        resp = await client.get("/api/v1/plain")

        assert resp.text == "plain text"
        assert "success" not in resp.text

    @pytest.mark.asyncio
    async def test_outside_prefix_not_wrapped(self, client):
        resp = await client.get("/outside/path")
        body = resp.json()

        assert "success" not in body
        assert body["data"] == "not wrapped"
