"""
Database operations for the event processing pipeline.

Async SQLAlchemy implementation replacing the original psycopg2 layer.
All functions use flush() only — the caller manages the transaction boundary.
"""

import json
from datetime import date, datetime, timedelta
from typing import Any, TypedDict

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    CrawlEvent,
    CrawlEventOccurrence,
    CrawlEventTag,
    CrawlResult,
    CrawlRun,
    Event,
    EventOccurrence,
    EventTag,
    EventUrl,
    Location,
    LocationAlternateName,
    Tag,
    TagRule,
    Website,
    WebsiteTag,
    WebsiteUrl,
)
from api.models.base import CrawlResultStatus, CrawlRunStatus, TagRuleType


class TagRulesDict(TypedDict):
    rewrite: dict[str, str]
    exclude: list[str]
    remove: list[str]


# =============================================================================
# Crawl Run / Result Operations
# =============================================================================


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
    """Create or reset a crawl result record."""
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


# =============================================================================
# Content Retrieval
# =============================================================================


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
                    [CrawlResultStatus.crawled, CrawlResultStatus.extracted]
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
        cr_status = row[1]
        crawled_content = row[7]
        extracted_content = row[8]

        if cr_status == CrawlResultStatus.failed and crawled_content is not None:
            effective_status = "crawled" if extracted_content is None else "extracted"
        else:
            effective_status = (
                cr_status.value if hasattr(cr_status, "value") else cr_status
            )

        results.append(
            {
                "crawl_result_id": row[0],
                "status": effective_status,
                "original_status": (
                    row[1].value if hasattr(row[1], "value") else row[1]
                ),
                "website_id": row[2],
                "crawl_run_id": row[3],
                "name": row[4],
                "notes": row[5],
                "run_date": row[6],
            }
        )

    return results


# =============================================================================
# Website / Location / Tag Queries
# =============================================================================


async def get_websites_due_for_crawling(
    session: AsyncSession, website_ids: list[int] | None = None
) -> list[dict[str, Any]]:
    """Get websites that are due for crawling.

    When website_ids is provided, returns those websites regardless of frequency.
    Otherwise filters by crawl_frequency / force_crawl / last_crawled_at.
    """
    stmt = select(Website)

    if website_ids:
        stmt = stmt.where(Website.id.in_(website_ids))
    else:
        now = datetime.now()
        stmt = stmt.where(
            Website.disabled == False,  # noqa: E712
            (Website.crawl_after.is_(None)) | (Website.crawl_after <= date.today()),
            (Website.force_crawl == True)  # noqa: E712
            | (Website.last_crawled_at.is_(None))
            | (
                now - Website.last_crawled_at
                >= timedelta(days=1) * func.coalesce(Website.crawl_frequency, 7)
            ),
        ).order_by(
            Website.force_crawl.desc(), Website.last_crawled_at.asc().nullsfirst()
        )

    result = await session.execute(stmt)
    website_objs = result.scalars().all()

    # Load URLs for these websites in a single query
    if not website_objs:
        return []

    website_ids_found = [w.id for w in website_objs]
    url_result = await session.execute(
        select(WebsiteUrl)
        .where(WebsiteUrl.website_id.in_(website_ids_found))
        .order_by(WebsiteUrl.website_id, WebsiteUrl.sort_order)
    )
    url_objs = url_result.scalars().all()

    # Group URLs by website_id
    urls_by_website: dict[int, list[dict[str, str | None]]] = {}
    for url_obj in url_objs:
        urls_by_website.setdefault(url_obj.website_id, []).append(
            {"url": url_obj.url, "js_code": url_obj.js_code}
        )

    websites = []
    for w in website_objs:
        urls = urls_by_website.get(w.id, [])
        crawl_mode = (
            w.crawl_mode.value
            if hasattr(w.crawl_mode, "value")
            else (w.crawl_mode or "browser")
        )

        # Skip websites with no URLs unless json_api mode
        if not urls and crawl_mode != "json_api":
            continue

        websites.append(
            {
                "id": w.id,
                "name": w.name,
                "crawl_frequency": w.crawl_frequency or 7,
                "selector": w.selector,
                "num_clicks": w.num_clicks or 2,
                "keywords": w.keywords,
                "max_pages": w.max_pages or 30,
                "max_batches": w.max_batches,
                "notes": w.notes,
                "delay_before_return_html": w.delay_before_return_html,
                "content_filter_threshold": w.content_filter_threshold,
                "scan_full_page": w.scan_full_page,
                "remove_overlay_elements": w.remove_overlay_elements,
                "javascript_enabled": w.javascript_enabled,
                "text_mode": w.text_mode,
                "light_mode": w.light_mode,
                "use_stealth": w.use_stealth,
                "scroll_delay": (
                    float(w.scroll_delay) if w.scroll_delay is not None else None
                ),
                "crawl_timeout": w.crawl_timeout,
                "process_images": w.process_images,
                "base_url": w.base_url,
                "crawl_mode": crawl_mode,
                "json_api_config": (
                    w.json_api_config
                    if isinstance(w.json_api_config, dict)
                    else (json.loads(w.json_api_config) if w.json_api_config else {})
                ),
                "urls": urls,
            }
        )

    return websites


async def get_existing_upcoming_events(
    session: AsyncSession, website_id: int
) -> list[dict[str, Any]]:
    """Get existing upcoming events from a website for the extraction prompt.

    Returns active (non-archived) events with future occurrences.
    """
    today = date.today()

    # Get events with future occurrences for this website
    event_ids_stmt = (
        select(Event.id)
        .join(EventOccurrence, Event.id == EventOccurrence.event_id)
        .where(
            Event.website_id == website_id,
            Event.archived == False,  # noqa: E712
            EventOccurrence.start_date >= today,
        )
        .distinct()
    )
    event_ids_result = await session.execute(event_ids_stmt)
    event_ids = [row[0] for row in event_ids_result.all()]

    if not event_ids:
        return []

    # Load events
    events_result = await session.execute(
        select(Event, Location.name.label("location_name_resolved"))
        .outerjoin(Location, Event.location_id == Location.id)
        .where(Event.id.in_(event_ids))
    )
    event_rows = events_result.all()

    # Load occurrences
    occ_result = await session.execute(
        select(EventOccurrence)
        .where(
            EventOccurrence.event_id.in_(event_ids),
            EventOccurrence.start_date >= today,
        )
        .order_by(EventOccurrence.event_id, EventOccurrence.start_date)
    )
    occ_objs = occ_result.scalars().all()

    occs_by_event: dict[int, list[dict[str, Any]]] = {}
    for occ in occ_objs:
        occs_by_event.setdefault(occ.event_id, []).append(
            {
                "start_date": str(occ.start_date) if occ.start_date else None,
                "start_time": occ.start_time,
                "end_date": str(occ.end_date) if occ.end_date else None,
                "end_time": occ.end_time,
            }
        )

    # Load URLs
    url_result = await session.execute(
        select(EventUrl)
        .where(EventUrl.event_id.in_(event_ids))
        .order_by(EventUrl.event_id, EventUrl.url)
    )
    url_objs = url_result.scalars().all()

    urls_by_event: dict[int, list[str]] = {}
    for url_obj in url_objs:
        urls_by_event.setdefault(url_obj.event_id, []).append(url_obj.url)

    # Load tags
    tag_result = await session.execute(
        select(EventTag.event_id, Tag.name)
        .join(Tag, EventTag.tag_id == Tag.id)
        .where(EventTag.event_id.in_(event_ids))
        .order_by(EventTag.event_id, Tag.name)
    )
    tag_rows = tag_result.all()

    tags_by_event: dict[int, list[str]] = {}
    for event_id, tag_name in tag_rows:
        tags_by_event.setdefault(event_id, []).append(tag_name)

    # Build result
    events = []
    for event_obj, location_name in event_rows:
        events.append(
            {
                "id": event_obj.id,
                "name": event_obj.name,
                "description": event_obj.description,
                "location": location_name,
                "sublocation": event_obj.sublocation,
                "occurrences": occs_by_event.get(event_obj.id, []),
                "urls": urls_by_event.get(event_obj.id, []),
                "hashtags": tags_by_event.get(event_obj.id, []),
                "emoji": event_obj.emoji,
            }
        )

    # Sort by earliest occurrence
    events.sort(
        key=lambda e: e["occurrences"][0]["start_date"] if e["occurrences"] else ""
    )

    return events


async def get_all_locations(
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """Get all locations with their alternate names for location matching."""
    result = await session.execute(
        select(Location).where(Location.lat.isnot(None), Location.lng.isnot(None))
    )
    location_objs = result.scalars().all()

    locations: dict[int, dict[str, Any]] = {}
    for loc in location_objs:
        locations[loc.id] = {
            "id": loc.id,
            "name": loc.name,
            "short_name": loc.short_name,
            "address": loc.address,
            "lat": float(loc.lat) if loc.lat else None,
            "lng": float(loc.lng) if loc.lng else None,
            "emoji": loc.emoji,
            "alternate_names": [],
            "website_scoped_names": {},
        }

    alt_result = await session.execute(select(LocationAlternateName))
    alt_names = list(alt_result.scalars().all())

    for alt in alt_names:
        if alt.location_id in locations:
            if alt.website_id is None:
                locations[alt.location_id]["alternate_names"].append(alt.alternate_name)
            else:
                locations[alt.location_id]["website_scoped_names"].setdefault(
                    alt.website_id, []
                ).append(alt.alternate_name)

    return list(locations.values())


async def get_tag_rules(session: AsyncSession) -> TagRulesDict:
    """Get tag processing rules from the database."""
    rewrite: dict[str, str] = {}
    exclude: list[str] = []
    remove: list[str] = []

    result = await session.execute(
        select(TagRule).order_by(TagRule.rule_type, TagRule.pattern)
    )
    rules = result.scalars().all()

    for rule in rules:
        if rule.rule_type == TagRuleType.rewrite:
            rewrite[rule.pattern] = rule.replacement or ""
        elif rule.rule_type == TagRuleType.exclude:
            exclude.append(rule.pattern)
        elif rule.rule_type == TagRuleType.remove:
            remove.append(rule.pattern)

    return {"rewrite": rewrite, "exclude": exclude, "remove": remove}


async def get_websites_with_tags(
    session: AsyncSession,
) -> dict[str, list[str]]:
    """Get all websites with their URLs and extra tags.

    Returns a dict mapping URL (lowercase, no trailing slash) to list of extra tags.
    """
    stmt = (
        select(WebsiteUrl.url, Tag.name)
        .join(Website, WebsiteUrl.website_id == Website.id)
        .outerjoin(WebsiteTag, Website.id == WebsiteTag.website_id)
        .outerjoin(Tag, WebsiteTag.tag_id == Tag.id)
        .where(Website.disabled == False)  # noqa: E712
        .order_by(WebsiteUrl.website_id, WebsiteUrl.sort_order)
    )

    result = await session.execute(stmt)
    rows = result.all()

    websites_map: dict[str, list[str]] = {}
    for url, tag_name in rows:
        normalized_url = url.rstrip("/").lower()
        if normalized_url not in websites_map:
            websites_map[normalized_url] = []
        if tag_name and tag_name not in websites_map[normalized_url]:
            websites_map[normalized_url].append(tag_name)

    return websites_map


# =============================================================================
# Crawl Event Storage
# =============================================================================


async def save_crawl_events(
    session: AsyncSession,
    crawl_result_id: int,
    events: list[dict[str, Any]],
) -> int:
    """Save processed events into crawl_events, occurrences, and tags.

    Args:
        session: Async SQLAlchemy session.
        crawl_result_id: The crawl result these events belong to.
        events: List of event dicts from processor (with name, occurrences, tags, etc.)

    Returns:
        Number of events saved.
    """
    event_count = 0

    for event_data in events:
        if not event_data.get("name"):
            continue

        # Serialize raw_data — JSONB can't store date objects directly
        raw_data = json.loads(json.dumps(event_data, default=str))

        crawl_event = CrawlEvent(
            crawl_result_id=crawl_result_id,
            name=event_data.get("name", "")[:500],
            short_name=(
                event_data.get("short_name", "")[:255]
                if event_data.get("short_name")
                else None
            ),
            description=event_data.get("description"),
            emoji=(
                event_data.get("emoji", "")[:10] if event_data.get("emoji") else None
            ),
            location_name=(
                event_data.get("location", "")[:255]
                if event_data.get("location")
                else None
            ),
            sublocation=(
                event_data.get("sublocation", "")[:255]
                if event_data.get("sublocation")
                else None
            ),
            location_id=event_data.get("location_id"),
            url=(
                event_data.get("urls", [None])[0][:2000]
                if event_data.get("urls")
                else None
            ),
            raw_data=raw_data,
        )
        session.add(crawl_event)
        await session.flush()

        # Insert occurrences
        for i, occ in enumerate(event_data.get("occurrences", [])):
            if len(occ) >= 1 and occ[0]:
                try:
                    occurrence = CrawlEventOccurrence(
                        crawl_event_id=crawl_event.id,
                        start_date=occ[0],
                        start_time=occ[1] if len(occ) > 1 else None,
                        end_date=occ[2] if len(occ) > 2 and occ[2] else None,
                        end_time=occ[3] if len(occ) > 3 else None,
                        sort_order=i,
                    )
                    session.add(occurrence)
                except Exception:
                    pass

        # Insert tags
        for tag in event_data.get("tags", []):
            if tag:
                crawl_tag = CrawlEventTag(
                    crawl_event_id=crawl_event.id,
                    tag=tag[:100],
                )
                session.add(crawl_tag)

        event_count += 1

    await session.flush()
    return event_count


# =============================================================================
# Archival (raw SQL — too complex for ORM conversion now)
# =============================================================================


async def archive_outdated_events(
    session: AsyncSession, website_id: int
) -> tuple[int, list[tuple[Any, ...]]]:
    """Archive events no longer found in recent crawls.

    Uses raw SQL due to complex nested EXISTS subqueries.
    """
    archive_where = """
        e.archived = FALSE
          AND EXISTS (
              SELECT 1
              FROM event_sources es
              JOIN crawl_events ce ON es.crawl_event_id = ce.id
              JOIN crawl_results cr ON ce.crawl_result_id = cr.id
              WHERE es.event_id = e.id
                AND cr.website_id = :website_id
          )
          AND NOT EXISTS (
              SELECT 1
              FROM event_sources es
              JOIN crawl_events ce ON es.crawl_event_id = ce.id
              JOIN crawl_results cr ON ce.crawl_result_id = cr.id
              WHERE es.event_id = e.id
                AND cr.processed_at = (
                    SELECT MAX(cr2.processed_at)
                    FROM crawl_results cr2
                    WHERE cr2.website_id = cr.website_id
                      AND cr2.status IN ('processed', 'extracted')
                      AND cr2.processed_at IS NOT NULL
                )
          )
          AND EXISTS (
              SELECT 1
              FROM event_sources es
              JOIN crawl_events ce ON es.crawl_event_id = ce.id
              JOIN crawl_results cr ON ce.crawl_result_id = cr.id
              WHERE es.event_id = e.id
                AND cr.status IN ('processed', 'extracted')
                AND cr.processed_at IS NOT NULL
          )
          AND (
              NOT EXISTS (
                  SELECT 1 FROM event_occurrences eo
                  WHERE eo.event_id = e.id AND eo.start_date >= CURRENT_DATE
              )
              OR
              NOT EXISTS (
                  SELECT 1
                  FROM event_sources es
                  JOIN crawl_events ce ON es.crawl_event_id = ce.id
                  JOIN crawl_results cr ON ce.crawl_result_id = cr.id
                  WHERE es.event_id = e.id
                    AND cr.processed_at >= NOW() - INTERVAL '14 days'
              )
          )
    """

    # Identify events to archive (check for upcoming ones)
    identify_sql = text(f"""
        SELECT e.id, e.name,
               (SELECT MIN(eo.start_date)
                FROM event_occurrences eo
                WHERE eo.event_id = e.id
                  AND eo.start_date >= CURRENT_DATE) as next_occurrence
        FROM events e
        WHERE {archive_where}
    """)
    identify_result = await session.execute(identify_sql, {"website_id": website_id})
    events_to_archive = identify_result.all()

    upcoming_events = [
        (event_id, name, next_occ)
        for event_id, name, next_occ in events_to_archive
        if next_occ
    ]

    # Perform archiving
    archive_sql = text(f"""
        UPDATE events e
        SET archived = TRUE
        WHERE {archive_where}
    """)
    archive_cursor = await session.execute(archive_sql, {"website_id": website_id})
    archived_count: int = (
        archive_cursor.rowcount if hasattr(archive_cursor, "rowcount") else 0
    )

    await session.flush()
    return archived_count, upcoming_events
