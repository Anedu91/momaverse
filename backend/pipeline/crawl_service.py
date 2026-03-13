"""Crawl run and result database operations using SQLAlchemy."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import CrawlResult, CrawlRun, Website
from api.models.base import CrawlResultStatus, CrawlRunStatus


async def get_or_create_crawl_run(session: AsyncSession, run_date: str | date) -> int:
    """Get or create a crawl run for the given date."""
    if isinstance(run_date, str):
        run_date = date.fromisoformat(run_date)

    result = await session.execute(
        select(CrawlRun).where(CrawlRun.run_date == run_date)
    )
    crawl_run = result.scalar_one_or_none()
    if crawl_run:
        return crawl_run.id

    crawl_run = CrawlRun(
        run_date=run_date,
        status=CrawlRunStatus.running,
    )
    session.add(crawl_run)
    await session.flush()
    return crawl_run.id


async def create_crawl_result(
    session: AsyncSession, crawl_run_id: int, website_id: int, filename: str
) -> int:
    """Create or update a crawl result record."""
    # Check for existing result with same crawl_run_id + filename
    result = await session.execute(
        select(CrawlResult).where(
            CrawlResult.crawl_run_id == crawl_run_id,
            CrawlResult.filename == filename,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.status = CrawlResultStatus.pending
        await session.flush()
        return existing.id

    crawl_result = CrawlResult(
        crawl_run_id=crawl_run_id,
        website_id=website_id,
        filename=filename,
        status=CrawlResultStatus.pending,
    )
    session.add(crawl_result)
    await session.flush()
    return crawl_result.id


async def update_crawl_result(
    session: AsyncSession, crawl_result_id: int, status: str, **kwargs: Any
) -> None:
    """Generic update for crawl results."""
    result = await session.execute(
        select(CrawlResult).where(CrawlResult.id == crawl_result_id)
    )
    cr = result.scalar_one()

    cr.status = CrawlResultStatus(status)

    now = datetime.now()
    timestamp_map = {
        "crawled": "crawled_at",
        "extracted": "extracted_at",
        "processed": "processed_at",
    }
    if status in timestamp_map:
        setattr(cr, timestamp_map[status], now)

    if "content" in kwargs:
        if status == "crawled":
            cr.crawled_content = kwargs["content"]
        elif status == "extracted":
            cr.extracted_content = kwargs["content"]

    if "event_count" in kwargs:
        cr.event_count = kwargs["event_count"]

    if "error_message" in kwargs:
        error_msg = kwargs["error_message"]
        cr.error_message = error_msg[:65535] if error_msg else None

    await session.flush()


async def update_crawl_result_crawled(
    session: AsyncSession, crawl_result_id: int, content: str
) -> None:
    await update_crawl_result(session, crawl_result_id, "crawled", content=content)


async def update_crawl_result_extracted(
    session: AsyncSession, crawl_result_id: int, content: str
) -> None:
    await update_crawl_result(session, crawl_result_id, "extracted", content=content)


async def update_crawl_result_processed(
    session: AsyncSession, crawl_result_id: int, event_count: int
) -> None:
    await update_crawl_result(
        session, crawl_result_id, "processed", event_count=event_count
    )


async def update_crawl_result_failed(
    session: AsyncSession, crawl_result_id: int, error_message: str | None
) -> None:
    await update_crawl_result(
        session, crawl_result_id, "failed", error_message=error_message
    )


async def complete_crawl_run(session: AsyncSession, crawl_run_id: int) -> None:
    """Mark a crawl run as completed."""
    result = await session.execute(select(CrawlRun).where(CrawlRun.id == crawl_run_id))
    crawl_run = result.scalar_one()
    crawl_run.status = CrawlRunStatus.completed
    crawl_run.completed_at = datetime.now()
    await session.flush()


async def update_website_last_crawled(session: AsyncSession, website_id: int) -> None:
    """Update the last_crawled_at timestamp and reset force_crawl."""
    result = await session.execute(select(Website).where(Website.id == website_id))
    website = result.scalar_one()
    website.last_crawled_at = datetime.now()
    website.force_crawl = False
    await session.flush()


async def get_crawled_content(
    session: AsyncSession, crawl_result_id: int
) -> str | None:
    """Get crawled content for a crawl result."""
    result = await session.execute(
        select(CrawlResult.crawled_content).where(CrawlResult.id == crawl_result_id)
    )
    return result.scalar_one_or_none()


async def get_extracted_content(
    session: AsyncSession, crawl_result_id: int
) -> tuple[str | None, int | None]:
    """Get extracted content and website_id for a crawl result."""
    result = await session.execute(
        select(CrawlResult.extracted_content, CrawlResult.website_id).where(
            CrawlResult.id == crawl_result_id
        )
    )
    row = result.one_or_none()
    return (row[0], row[1]) if row else (None, None)


async def get_incomplete_crawl_results(
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """Get crawl results that need reprocessing.

    Returns results in 'crawled', 'extracted', or 'failed' (with crawled_content) status.
    """
    stmt = (
        select(
            CrawlResult.id,
            CrawlResult.status,
            CrawlResult.website_id,
            CrawlResult.crawl_run_id,
            Website.name,
            Website.notes,
            CrawlRun.run_date,
            CrawlResult.crawled_content,
            CrawlResult.extracted_content,
        )
        .join(Website, CrawlResult.website_id == Website.id)
        .join(CrawlRun, CrawlResult.crawl_run_id == CrawlRun.id)
        .where(
            Website.disabled == False,  # noqa: E712
            (
                CrawlResult.status.in_(
                    [
                        CrawlResultStatus.crawled,
                        CrawlResultStatus.extracted,
                    ]
                )
            )
            | (
                (CrawlResult.status == CrawlResultStatus.failed)
                & (CrawlResult.crawled_content.isnot(None))
            ),
        )
        .order_by(CrawlResult.status, CrawlRun.run_date.desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    results = []
    for row in rows:
        # Compute effective_status for failed results
        cr_status = row[1]
        crawled_content = row[7]
        extracted_content = row[8]

        if cr_status == CrawlResultStatus.failed and crawled_content is not None:
            if extracted_content is None:
                effective_status = "crawled"
            else:
                effective_status = "extracted"
        else:
            effective_status = (
                cr_status.value if hasattr(cr_status, "value") else cr_status
            )

        results.append(
            {
                "crawl_result_id": row[0],
                "status": effective_status,
                "original_status": row[1].value if hasattr(row[1], "value") else row[1],
                "website_id": row[2],
                "crawl_run_id": row[3],
                "name": row[4],
                "notes": row[5],
                "run_date": row[6],
            }
        )

    return results
