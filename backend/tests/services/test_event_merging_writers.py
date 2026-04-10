"""Tests for the async merge/create writers in ``event_merging``."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import (
    CrawlJobStatus,
    CrawlResultStatus,
    EventStatus,
    SourceType,
)
from api.models.crawl import CrawlJob, CrawlResult, ExtractedEvent
from api.models.event import (
    Event,
    EventOccurrence,
    EventSource,
    EventTag,
    EventUrl,
)
from api.models.location import Location
from api.models.source import Source
from api.models.tag import Tag
from api.services.event_merging import (
    ExtractedEventInput,
    ParsedOccurrence,
    create_new_event,
    merge_into_existing_event,
)

TODAY = date(2026, 4, 10)


async def _make_source(db: AsyncSession, *, name: str = "Src") -> Source:
    source = Source(name=name, type=SourceType.crawler)
    db.add(source)
    await db.flush()
    return source


async def _make_location(db: AsyncSession, *, name: str = "Venue") -> Location:
    loc = Location(name=name, emoji="\U0001f3a8")
    db.add(loc)
    await db.flush()
    return loc


async def _make_extracted_event(
    db: AsyncSession, *, source: Source, name: str = "EE"
) -> ExtractedEvent:
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
    ee = ExtractedEvent(crawl_result_id=result.id, name=name)
    db.add(ee)
    await db.flush()
    return ee


async def _make_event(
    db: AsyncSession,
    *,
    location: Location,
    name: str = "Existing Event",
    status: EventStatus = EventStatus.active,
    location_id_override: int | None = None,
) -> Event:
    event = Event(
        name=name,
        location_id=location_id_override
        if location_id_override is not None
        else location.id,
        status=status,
    )
    db.add(event)
    await db.flush()
    return event


def _make_input(
    *,
    ee_id: int,
    source_id: int,
    location_id: int | None,
    name: str = "Tagged Event",
    url: str | None = "https://example.com/evt",
    tags: list[str] | None = None,
    occurrences: list[ParsedOccurrence] | None = None,
) -> ExtractedEventInput:
    return ExtractedEventInput(
        ee_id=ee_id,
        name=name,
        short_name="short",
        description="desc",
        emoji="\U0001f3a8",
        sublocation="Room 1",
        location_id=location_id,
        url=url,
        source_id=source_id,
        lat=None,
        lng=None,
        occurrences=occurrences
        or [
            ParsedOccurrence(
                start_date=TODAY + timedelta(days=1),
                start_time="19:00",
                end_date=None,
                end_time=None,
            )
        ],
        tags=tags or [],
    )


@pytest.mark.asyncio
async def test_create_new_event_inserts_all_rows(db_session: AsyncSession) -> None:
    source = await _make_source(db_session)
    location = await _make_location(db_session)
    ee = await _make_extracted_event(db_session, source=source)

    input_ = _make_input(
        ee_id=ee.id,
        source_id=source.id,
        location_id=location.id,
        tags=["music"],
        occurrences=[
            ParsedOccurrence(
                start_date=TODAY + timedelta(days=1),
                start_time="19:00",
                end_date=None,
                end_time=None,
            ),
            ParsedOccurrence(
                start_date=TODAY + timedelta(days=2),
                start_time="20:00",
                end_date=TODAY + timedelta(days=2),
                end_time="22:00",
            ),
        ],
    )

    new_id = await create_new_event(db_session, extracted=input_)
    await db_session.flush()

    event = (
        await db_session.execute(select(Event).where(Event.id == new_id))
    ).scalar_one()
    assert event.name == "Tagged Event"
    assert event.location_id == location.id
    assert event.sublocation == "Room 1"

    occ_count = len(
        (
            await db_session.execute(
                select(EventOccurrence).where(EventOccurrence.event_id == new_id)
            )
        )
        .scalars()
        .all()
    )
    assert occ_count == 2

    urls = (
        (
            await db_session.execute(
                select(EventUrl.url).where(EventUrl.event_id == new_id)
            )
        )
        .scalars()
        .all()
    )
    assert urls == ["https://example.com/evt"]

    sources = (
        (
            await db_session.execute(
                select(EventSource).where(EventSource.event_id == new_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(sources) == 1
    assert sources[0].is_primary is True
    assert sources[0].extracted_event_id == ee.id
    assert sources[0].source_id == source.id


@pytest.mark.asyncio
async def test_create_new_event_creates_missing_tags(db_session: AsyncSession) -> None:
    source = await _make_source(db_session)
    location = await _make_location(db_session)
    ee = await _make_extracted_event(db_session, source=source)

    input_ = _make_input(
        ee_id=ee.id,
        source_id=source.id,
        location_id=location.id,
        tags=["brandnew"],
    )
    new_id = await create_new_event(db_session, extracted=input_)

    tag = (
        await db_session.execute(select(Tag).where(Tag.name == "brandnew"))
    ).scalar_one()
    link = (
        await db_session.execute(
            select(EventTag).where(
                EventTag.event_id == new_id, EventTag.tag_id == tag.id
            )
        )
    ).scalar_one()
    assert link.event_id == new_id


@pytest.mark.asyncio
async def test_create_new_event_reuses_existing_tags(db_session: AsyncSession) -> None:
    source = await _make_source(db_session)
    location = await _make_location(db_session)
    ee = await _make_extracted_event(db_session, source=source)

    existing_tag = Tag(name="reuse-me")
    db_session.add(existing_tag)
    await db_session.flush()
    existing_id = existing_tag.id

    input_ = _make_input(
        ee_id=ee.id,
        source_id=source.id,
        location_id=location.id,
        tags=["reuse-me"],
    )
    new_id = await create_new_event(db_session, extracted=input_)

    tags = (
        (await db_session.execute(select(Tag).where(Tag.name == "reuse-me")))
        .scalars()
        .all()
    )
    assert len(tags) == 1
    assert tags[0].id == existing_id

    link = (
        await db_session.execute(
            select(EventTag).where(
                EventTag.event_id == new_id, EventTag.tag_id == existing_id
            )
        )
    ).scalar_one()
    assert link.tag_id == existing_id


@pytest.mark.asyncio
async def test_merge_into_existing_event_adds_url(db_session: AsyncSession) -> None:
    source = await _make_source(db_session)
    location = await _make_location(db_session)
    event = await _make_event(db_session, location=location)
    ee = await _make_extracted_event(db_session, source=source)

    input_ = _make_input(
        ee_id=ee.id,
        source_id=source.id,
        location_id=location.id,
        url="https://example.com/new",
    )
    await merge_into_existing_event(db_session, event_id=event.id, extracted=input_)
    await db_session.flush()

    urls = (
        (
            await db_session.execute(
                select(EventUrl.url).where(EventUrl.event_id == event.id)
            )
        )
        .scalars()
        .all()
    )
    assert urls == ["https://example.com/new"]


@pytest.mark.asyncio
async def test_merge_into_existing_event_skips_duplicate_url(
    db_session: AsyncSession,
) -> None:
    source = await _make_source(db_session)
    location = await _make_location(db_session)
    event = await _make_event(db_session, location=location)

    db_session.add(EventUrl(event_id=event.id, url="https://example.com/dup"))
    await db_session.flush()

    ee = await _make_extracted_event(db_session, source=source)
    input_ = _make_input(
        ee_id=ee.id,
        source_id=source.id,
        location_id=location.id,
        url="https://example.com/dup",
    )
    await merge_into_existing_event(db_session, event_id=event.id, extracted=input_)
    await db_session.flush()

    urls = (
        (
            await db_session.execute(
                select(EventUrl.url).where(EventUrl.event_id == event.id)
            )
        )
        .scalars()
        .all()
    )
    assert urls == ["https://example.com/dup"]


@pytest.mark.asyncio
async def test_merge_into_existing_event_unarchives(db_session: AsyncSession) -> None:
    source = await _make_source(db_session)
    location = await _make_location(db_session)
    event = await _make_event(
        db_session, location=location, status=EventStatus.archived
    )
    ee = await _make_extracted_event(db_session, source=source)

    input_ = _make_input(
        ee_id=ee.id,
        source_id=source.id,
        location_id=location.id,
        url=None,
    )
    await merge_into_existing_event(db_session, event_id=event.id, extracted=input_)
    await db_session.flush()

    refreshed = (
        await db_session.execute(select(Event).where(Event.id == event.id))
    ).scalar_one()
    assert refreshed.status == EventStatus.active


@pytest.mark.asyncio
async def test_merge_into_existing_event_links_source(
    db_session: AsyncSession,
) -> None:
    source = await _make_source(db_session)
    location = await _make_location(db_session)
    event = await _make_event(db_session, location=location)
    ee = await _make_extracted_event(db_session, source=source)

    input_ = _make_input(
        ee_id=ee.id,
        source_id=source.id,
        location_id=location.id,
        url=None,
    )
    await merge_into_existing_event(db_session, event_id=event.id, extracted=input_)
    await db_session.flush()

    sources = (
        (
            await db_session.execute(
                select(EventSource).where(EventSource.event_id == event.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(sources) == 1
    assert sources[0].is_primary is False
    assert sources[0].extracted_event_id == ee.id
    assert sources[0].source_id == source.id
