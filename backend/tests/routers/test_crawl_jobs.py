"""Tests for the crawl_jobs router."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.dependencies import create_access_token, hash_password
from api.models.crawl import CrawlContent, CrawlJob, CrawlResult, ExtractedEvent
from api.models.source import Source
from api.models.user import User
from api.routers.crawl_jobs import router

PREFIX = "/api/v1/crawl-jobs"


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
        email="crawl-test@example.com",
        display_name="Crawl Tester",
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
async def sample_source(db_session: AsyncSession) -> Source:
    source = Source(name="Crawl Source", type="crawler")
    db_session.add(source)
    await db_session.flush()
    return source


@pytest_asyncio.fixture
async def sample_crawl_job(db_session: AsyncSession) -> CrawlJob:
    job = CrawlJob(status="running")
    db_session.add(job)
    await db_session.flush()
    return job


@pytest_asyncio.fixture
async def sample_crawl_result(
    db_session: AsyncSession, sample_crawl_job: CrawlJob, sample_source: Source
) -> CrawlResult:
    result = CrawlResult(
        crawl_job_id=sample_crawl_job.id,
        source_id=sample_source.id,
        status="pending",
    )
    db_session.add(result)
    await db_session.flush()
    return result


# ---------------------------------------------------------------------------
# List crawl jobs
# ---------------------------------------------------------------------------


class TestListCrawlJobs:
    @pytest.mark.asyncio
    async def test_list_crawl_jobs_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["total"] == 0

    @pytest.mark.asyncio
    async def test_list_crawl_jobs_returns_items(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_crawl_job: CrawlJob,
    ) -> None:
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_crawl_jobs_status_filter(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_crawl_job: CrawlJob,
    ) -> None:
        resp = await client.get(
            f"{PREFIX}/",
            params={"status_filter": "running"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

        # Filter by a different status should return 0
        resp2 = await client.get(
            f"{PREFIX}/",
            params={"status_filter": "completed"},
            headers=auth_headers,
        )
        body2 = resp2.json()
        assert body2["total"] == 0

    @pytest.mark.asyncio
    async def test_list_crawl_jobs_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{PREFIX}/")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get crawl job detail
# ---------------------------------------------------------------------------


class TestGetCrawlJob:
    @pytest.mark.asyncio
    async def test_get_crawl_job_returns_detail(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_crawl_job: CrawlJob,
        sample_crawl_result: CrawlResult,
    ) -> None:
        resp = await client.get(f"{PREFIX}/{sample_crawl_job.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "running"
        assert len(body["results"]) >= 1

    @pytest.mark.asyncio
    async def test_get_crawl_job_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{PREFIX}/99999", headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Get crawl result detail
# ---------------------------------------------------------------------------


class TestGetCrawlResult:
    @pytest.mark.asyncio
    async def test_get_crawl_result_returns_detail(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
        sample_crawl_job: CrawlJob,
        sample_crawl_result: CrawlResult,
    ) -> None:
        # Add extracted event and content
        ee = ExtractedEvent(
            crawl_result_id=sample_crawl_result.id,
            name="Found Event",
        )
        db_session.add(ee)
        content = CrawlContent(
            crawl_result_id=sample_crawl_result.id,
            crawled_content="<html>test</html>",
        )
        db_session.add(content)
        await db_session.flush()

        resp = await client.get(
            f"{PREFIX}/{sample_crawl_job.id}/results/{sample_crawl_result.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["extracted_events"]) >= 1
        assert body["content"] is not None

    @pytest.mark.asyncio
    async def test_get_crawl_result_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_crawl_job: CrawlJob,
    ) -> None:
        resp = await client.get(
            f"{PREFIX}/{sample_crawl_job.id}/results/99999",
            headers=auth_headers,
        )
        assert resp.status_code == 404
