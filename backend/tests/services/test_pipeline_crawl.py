"""Tests for pipeline crawl service (SQLAlchemy)."""

import pytest
import pytest_asyncio
from api.models import CrawlResult, CrawlRun, Website
from api.models.base import CrawlResultStatus, CrawlRunStatus
from pipeline.services.crawl import (
    complete_crawl_run,
    create_crawl_result,
    get_crawled_content,
    get_extracted_content,
    get_incomplete_crawl_results,
    get_or_create_crawl_run,
    update_crawl_result_crawled,
    update_crawl_result_extracted,
    update_crawl_result_failed,
    update_crawl_result_processed,
    update_website_last_crawled,
)


@pytest_asyncio.fixture
async def website(db_session):
    w = Website(name="Test Site", disabled=False)
    db_session.add(w)
    await db_session.flush()
    return w


@pytest_asyncio.fixture
async def crawl_run(db_session):
    run_id = await get_or_create_crawl_run(db_session, "2026-03-13")
    return run_id


@pytest_asyncio.fixture
async def crawl_result(db_session, crawl_run, website):
    cr_id = await create_crawl_result(db_session, crawl_run, website.id, "test.html")
    return cr_id


class TestGetOrCreateCrawlRun:
    @pytest.mark.asyncio
    async def test_creates_new_run(self, db_session):
        run_id = await get_or_create_crawl_run(db_session, "2026-01-01")
        assert run_id is not None
        assert isinstance(run_id, int)

    @pytest.mark.asyncio
    async def test_returns_existing_run(self, db_session):
        id1 = await get_or_create_crawl_run(db_session, "2026-02-01")
        id2 = await get_or_create_crawl_run(db_session, "2026-02-01")
        assert id1 == id2

    @pytest.mark.asyncio
    async def test_different_dates_different_runs(self, db_session):
        id1 = await get_or_create_crawl_run(db_session, "2026-03-01")
        id2 = await get_or_create_crawl_run(db_session, "2026-03-02")
        assert id1 != id2


class TestCreateCrawlResult:
    @pytest.mark.asyncio
    async def test_creates_result(self, db_session, crawl_run, website):
        cr_id = await create_crawl_result(
            db_session, crawl_run, website.id, "page.html"
        )
        assert cr_id is not None
        assert isinstance(cr_id, int)

    @pytest.mark.asyncio
    async def test_duplicate_resets_to_pending(self, db_session, crawl_run, website):
        cr_id = await create_crawl_result(db_session, crawl_run, website.id, "dup.html")
        # Mark as failed
        await update_crawl_result_failed(db_session, cr_id, "some error")

        # Re-create with same filename resets to pending
        cr_id2 = await create_crawl_result(
            db_session, crawl_run, website.id, "dup.html"
        )
        assert cr_id == cr_id2

        result = await db_session.get(CrawlResult, cr_id)
        assert result.status == CrawlResultStatus.pending


class TestUpdateCrawlResult:
    @pytest.mark.asyncio
    async def test_crawled(self, db_session, crawl_result):
        await update_crawl_result_crawled(
            db_session, crawl_result, "<html>content</html>"
        )

        cr = await db_session.get(CrawlResult, crawl_result)
        assert cr.status == CrawlResultStatus.crawled
        assert cr.crawled_content == "<html>content</html>"
        assert cr.crawled_at is not None

    @pytest.mark.asyncio
    async def test_extracted(self, db_session, crawl_result):
        await update_crawl_result_extracted(
            db_session, crawl_result, '[{"event": "test"}]'
        )

        cr = await db_session.get(CrawlResult, crawl_result)
        assert cr.status == CrawlResultStatus.extracted
        assert cr.extracted_content == '[{"event": "test"}]'
        assert cr.extracted_at is not None

    @pytest.mark.asyncio
    async def test_processed(self, db_session, crawl_result):
        await update_crawl_result_processed(db_session, crawl_result, 5)

        cr = await db_session.get(CrawlResult, crawl_result)
        assert cr.status == CrawlResultStatus.processed
        assert cr.event_count == 5
        assert cr.processed_at is not None

    @pytest.mark.asyncio
    async def test_failed(self, db_session, crawl_result):
        await update_crawl_result_failed(db_session, crawl_result, "timeout")

        cr = await db_session.get(CrawlResult, crawl_result)
        assert cr.status == CrawlResultStatus.failed
        assert cr.error_message == "timeout"

    @pytest.mark.asyncio
    async def test_failed_truncates_long_error(self, db_session, crawl_result):
        long_msg = "x" * 70000
        await update_crawl_result_failed(db_session, crawl_result, long_msg)

        cr = await db_session.get(CrawlResult, crawl_result)
        assert len(cr.error_message) == 65535


class TestCompleteCrawlRun:
    @pytest.mark.asyncio
    async def test_marks_completed(self, db_session, crawl_run):
        await complete_crawl_run(db_session, crawl_run)

        run = await db_session.get(CrawlRun, crawl_run)
        assert run.status == CrawlRunStatus.completed
        assert run.completed_at is not None


class TestUpdateWebsiteLastCrawled:
    @pytest.mark.asyncio
    async def test_updates_timestamp_and_resets_force(self, db_session):
        w = Website(name="Force Site", disabled=False, force_crawl=True)
        db_session.add(w)
        await db_session.flush()
        assert w.force_crawl is True

        await update_website_last_crawled(db_session, w.id)

        refreshed = await db_session.get(Website, w.id)
        assert refreshed.last_crawled_at is not None
        assert refreshed.force_crawl is False


class TestGetContent:
    @pytest.mark.asyncio
    async def test_get_crawled_content(self, db_session, crawl_result):
        await update_crawl_result_crawled(db_session, crawl_result, "page content")

        content = await get_crawled_content(db_session, crawl_result)
        assert content == "page content"

    @pytest.mark.asyncio
    async def test_get_crawled_content_missing(self, db_session):
        content = await get_crawled_content(db_session, 99999)
        assert content is None

    @pytest.mark.asyncio
    async def test_get_extracted_content(self, db_session, crawl_result):
        await update_crawl_result_extracted(db_session, crawl_result, '["events"]')

        content, wid = await get_extracted_content(db_session, crawl_result)
        assert content == '["events"]'
        assert wid is not None

    @pytest.mark.asyncio
    async def test_get_extracted_content_missing(self, db_session):
        content, wid = await get_extracted_content(db_session, 99999)
        assert content is None
        assert wid is None


class TestGetIncompleteCrawlResults:
    @pytest.mark.asyncio
    async def test_returns_crawled_status(self, db_session, crawl_result, website):
        await update_crawl_result_crawled(db_session, crawl_result, "html content")

        results = await get_incomplete_crawl_results(db_session)
        assert len(results) >= 1
        match = [r for r in results if r["crawl_result_id"] == crawl_result]
        assert len(match) == 1
        assert match[0]["status"] == "crawled"
        assert match[0]["name"] == website.name

    @pytest.mark.asyncio
    async def test_returns_extracted_status(self, db_session, crawl_result):
        await update_crawl_result_extracted(db_session, crawl_result, "json content")

        results = await get_incomplete_crawl_results(db_session)
        match = [r for r in results if r["crawl_result_id"] == crawl_result]
        assert len(match) == 1
        assert match[0]["status"] == "extracted"

    @pytest.mark.asyncio
    async def test_failed_with_crawled_content_returns_crawled(
        self, db_session, crawl_result
    ):
        # First set crawled content, then fail it
        await update_crawl_result_crawled(db_session, crawl_result, "some html")
        await update_crawl_result_failed(db_session, crawl_result, "extraction error")

        results = await get_incomplete_crawl_results(db_session)
        match = [r for r in results if r["crawl_result_id"] == crawl_result]
        assert len(match) == 1
        assert match[0]["status"] == "crawled"
        assert match[0]["original_status"] == "failed"

    @pytest.mark.asyncio
    async def test_excludes_pending(self, db_session, crawl_result):
        # crawl_result starts as pending — should not appear
        results = await get_incomplete_crawl_results(db_session)
        match = [r for r in results if r["crawl_result_id"] == crawl_result]
        assert len(match) == 0
