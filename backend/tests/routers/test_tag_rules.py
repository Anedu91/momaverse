"""Tests for the tag_rules router."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from api.database import get_db
from api.dependencies import create_access_token, hash_password
from api.models.tag import TagRule
from api.models.user import User
from api.routers.tag_rules import router
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

PREFIX = "/api/v1/tag-rules"


def _make_app(db_session: AsyncSession) -> FastAPI:
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
        email="tagrules-test@example.com",
        display_name="TagRules Tester",
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
async def sample_tag_rule(db_session: AsyncSession) -> TagRule:
    rule = TagRule(rule_type="rewrite", pattern="old-tag", replacement="new-tag")
    db_session.add(rule)
    await db_session.flush()
    return rule


# ---------------------------------------------------------------------------
# List tag rules
# ---------------------------------------------------------------------------


class TestListTagRules:
    @pytest.mark.asyncio
    async def test_list_tag_rules_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_tag_rules_returns_items(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_tag_rule: TagRule,
    ) -> None:
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 1
        assert body[0]["pattern"] == "old-tag"

    @pytest.mark.asyncio
    async def test_list_tag_rules_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{PREFIX}/")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Create tag rule
# ---------------------------------------------------------------------------


class TestCreateTagRule:
    @pytest.mark.asyncio
    async def test_create_tag_rule_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        payload = {
            "rule_type": "rewrite",
            "pattern": "test-pattern",
            "replacement": "test-replacement",
        }
        resp = await client.post(f"{PREFIX}/", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["rule_type"] == "rewrite"
        assert body["pattern"] == "test-pattern"
        assert "id" in body

    @pytest.mark.asyncio
    async def test_create_tag_rule_exclude_no_replacement(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        payload = {"rule_type": "exclude", "pattern": "spam"}
        resp = await client.post(f"{PREFIX}/", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["replacement"] is None

    @pytest.mark.asyncio
    async def test_create_tag_rule_requires_auth(self, client: AsyncClient) -> None:
        payload = {"rule_type": "rewrite", "pattern": "test"}
        resp = await client.post(f"{PREFIX}/", json=payload)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Update tag rule
# ---------------------------------------------------------------------------


class TestUpdateTagRule:
    @pytest.mark.asyncio
    async def test_update_tag_rule_partial(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_tag_rule: TagRule,
    ) -> None:
        payload = {"pattern": "updated-pattern"}
        resp = await client.put(
            f"{PREFIX}/{sample_tag_rule.id}",
            json=payload,
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["pattern"] == "updated-pattern"
        # Other fields remain unchanged
        assert body["rule_type"] == "rewrite"
        assert body["replacement"] == "new-tag"

    @pytest.mark.asyncio
    async def test_update_tag_rule_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.put(
            f"{PREFIX}/99999",
            json={"pattern": "ghost"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete tag rule
# ---------------------------------------------------------------------------


class TestDeleteTagRule:
    @pytest.mark.asyncio
    async def test_delete_tag_rule_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_tag_rule: TagRule,
    ) -> None:
        resp = await client.delete(
            f"{PREFIX}/{sample_tag_rule.id}", headers=auth_headers
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_tag_rule_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.delete(f"{PREFIX}/99999", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_tag_rule_requires_auth(
        self, client: AsyncClient, sample_tag_rule: TagRule
    ) -> None:
        resp = await client.delete(f"{PREFIX}/{sample_tag_rule.id}")
        assert resp.status_code == 401
