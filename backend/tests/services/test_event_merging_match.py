"""Tests for match selection and audit logging helpers."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import (
    CrawlJobStatus,
    CrawlResultStatus,
    ExtractedEventStatus,
    SourceType,
)
from api.models.crawl import (
    CrawlJob,
    CrawlResult,
    ExtractedEvent,
    ExtractedEventLog,
)
from api.models.source import Source
from api.services.event_merging import (
    DedupIndex,
    EventCandidate,
    find_best_match,
    log_extracted_event,
    select_matched_event_id,
)


def test_find_best_match_prefers_exact_normalized() -> None:
    candidates = [
        EventCandidate(id=1, name="Jazz Night at the Park"),
        EventCandidate(id=2, name="Jazz Night"),
    ]
    dates_by_event_id = {
        1: {"2026-04-11"},
        2: {"2026-04-11"},
    }
    result = find_best_match(
        "Jazz Night",
        {"2026-04-11"},
        candidates,
        dates_by_event_id,
    )
    assert result == 2


def test_find_best_match_requires_date_overlap() -> None:
    candidates = [EventCandidate(id=1, name="Jazz Night")]
    dates_by_event_id = {1: {"2026-05-01"}}
    result = find_best_match(
        "Jazz Night",
        {"2026-04-11"},
        candidates,
        dates_by_event_id,
    )
    assert result is None


def test_find_best_match_returns_none_when_no_candidates() -> None:
    result = find_best_match(
        "Jazz Night",
        {"2026-04-11"},
        [],
        {},
    )
    assert result is None


def _index_with(
    *,
    location_id: int | None = None,
    coords: tuple[float, float] | None = None,
    source_id: int | None = None,
    candidate: EventCandidate,
    dates: set[str],
) -> DedupIndex:
    index = DedupIndex()
    if location_id is not None:
        index.by_location_id[location_id] = [candidate]
    if coords is not None:
        index.by_coords[coords] = [candidate]
    if source_id is not None:
        index.by_source_id[source_id] = [candidate]
    index.dates_by_event_id[candidate.id] = dates
    return index


def test_select_matched_event_id_location_first() -> None:
    loc_candidate = EventCandidate(id=10, name="Jazz Night")
    coord_candidate = EventCandidate(id=20, name="Jazz Night")
    source_candidate = EventCandidate(id=30, name="Jazz Night")

    index = DedupIndex()
    index.by_location_id[100] = [loc_candidate]
    index.by_coords[(round(40.7, 5), round(-74.0, 5))] = [coord_candidate]
    index.by_source_id[1] = [source_candidate]
    index.dates_by_event_id[10] = {"2026-04-11"}
    index.dates_by_event_id[20] = {"2026-04-11"}
    index.dates_by_event_id[30] = {"2026-04-11"}

    result = select_matched_event_id(
        name="Jazz Night",
        extracted_dates={"2026-04-11"},
        location_id=100,
        lat=40.7,
        lng=-74.0,
        source_id=1,
        index=index,
    )
    assert result == 10


def test_select_matched_event_id_falls_back_to_coords() -> None:
    coord_candidate = EventCandidate(id=20, name="Jazz Night")
    source_candidate = EventCandidate(id=30, name="Jazz Night")

    index = DedupIndex()
    index.by_coords[(round(40.7, 5), round(-74.0, 5))] = [coord_candidate]
    index.by_source_id[1] = [source_candidate]
    index.dates_by_event_id[20] = {"2026-04-11"}
    index.dates_by_event_id[30] = {"2026-04-11"}

    # location_id is None, so location lookup is skipped.
    result = select_matched_event_id(
        name="Jazz Night",
        extracted_dates={"2026-04-11"},
        location_id=None,
        lat=40.7,
        lng=-74.0,
        source_id=1,
        index=index,
    )
    assert result == 20


def test_select_matched_event_id_falls_back_to_source() -> None:
    source_candidate = EventCandidate(id=30, name="Jazz Night")
    index = _index_with(
        source_id=1,
        candidate=source_candidate,
        dates={"2026-04-11"},
    )

    result = select_matched_event_id(
        name="Jazz Night",
        extracted_dates={"2026-04-11"},
        location_id=None,
        lat=None,
        lng=None,
        source_id=1,
        index=index,
    )
    assert result == 30


async def _seed_extracted_event(db: AsyncSession) -> int:
    source = Source(name="Src", type=SourceType.crawler)
    db.add(source)
    await db.flush()

    job = CrawlJob(status=CrawlJobStatus.running)
    db.add(job)
    await db.flush()

    result = CrawlResult(
        crawl_job_id=job.id,
        source_id=source.id,
        status=CrawlResultStatus.extracted,
    )
    db.add(result)
    await db.flush()

    extracted = ExtractedEvent(
        crawl_result_id=result.id,
        name="Jazz Night",
    )
    db.add(extracted)
    await db.flush()
    return extracted.id


@pytest.mark.asyncio
async def test_log_extracted_event_writes_row(db_session: AsyncSession) -> None:
    extracted_event_id = await _seed_extracted_event(db_session)

    await log_extracted_event(
        db_session,
        extracted_event_id=extracted_event_id,
        status=ExtractedEventStatus.skipped_duplicate,
        event_id=None,
        message="already exists",
    )
    await db_session.flush()

    rows = (
        (
            await db_session.execute(
                select(ExtractedEventLog).where(
                    ExtractedEventLog.extracted_event_id == extracted_event_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    log = rows[0]
    assert log.status == ExtractedEventStatus.skipped_duplicate
    assert log.event_id is None
    assert log.message == "already exists"
