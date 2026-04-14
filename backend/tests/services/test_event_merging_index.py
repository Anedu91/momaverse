"""Tests for the async dedup-index loader."""

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import EventStatus, SourceType
from api.models.event import Event, EventOccurrence, EventSource
from api.models.location import Location
from api.models.source import Source
from api.services.event_merging import (
    DedupIndex,
    EventCandidate,
    load_dedup_index,
)

TODAY = date(2026, 4, 10)


async def _make_location(
    db: AsyncSession,
    *,
    name: str = "Test Venue",
    lat: float | None = None,
    lng: float | None = None,
) -> Location:
    loc = Location(name=name, lat=lat, lng=lng, emoji="\U0001f3a8")
    db.add(loc)
    await db.flush()
    return loc


async def _make_event(
    db: AsyncSession,
    *,
    name: str,
    location: Location,
    status: EventStatus = EventStatus.active,
    occurrence_offsets: list[int] | None = None,
) -> Event:
    """Create an Event with occurrences at ``TODAY + offset_days``."""
    event = Event(name=name, location_id=location.id, status=status)
    db.add(event)
    await db.flush()

    for offset in occurrence_offsets or [1]:
        db.add(
            EventOccurrence(
                event_id=event.id,
                start_date=TODAY + timedelta(days=offset),
            )
        )
    await db.flush()
    return event


async def _make_source(db: AsyncSession, *, name: str = "Test Source") -> Source:
    source = Source(name=name, type=SourceType.crawler)
    db.add(source)
    await db.flush()
    return source


@pytest.mark.asyncio
async def test_load_dedup_index_empty(db_session: AsyncSession) -> None:
    index = await load_dedup_index(db_session, today=TODAY)
    assert isinstance(index, DedupIndex)
    assert index.by_location_id == {}
    assert index.by_coords == {}
    assert index.by_source_id == {}
    assert index.dates_by_event_id == {}


@pytest.mark.asyncio
async def test_load_dedup_index_groups_by_location_id(
    db_session: AsyncSession,
) -> None:
    loc = await _make_location(db_session, name="Loc A")
    event = await _make_event(
        db_session, name="Event A", location=loc, occurrence_offsets=[2]
    )

    index = await load_dedup_index(db_session, today=TODAY)

    assert loc.id in index.by_location_id
    assert index.by_location_id[loc.id] == [EventCandidate(id=event.id, name="Event A")]
    assert index.dates_by_event_id[event.id] == {str(TODAY + timedelta(days=2))}


@pytest.mark.asyncio
async def test_load_dedup_index_groups_by_coords(db_session: AsyncSession) -> None:
    loc = await _make_location(db_session, name="Loc B", lat=40.7, lng=-74.0)
    event = await _make_event(db_session, name="Event B", location=loc)

    index = await load_dedup_index(db_session, today=TODAY)

    key = (round(40.7, 5), round(-74.0, 5))
    assert key in index.by_coords
    assert index.by_coords[key] == [EventCandidate(id=event.id, name="Event B")]


@pytest.mark.asyncio
async def test_load_dedup_index_groups_by_source_id(
    db_session: AsyncSession,
) -> None:
    loc = await _make_location(db_session, name="Loc C", lat=40.7, lng=-74.0)
    event = await _make_event(db_session, name="Event C", location=loc)
    source = await _make_source(db_session, name="Src C")
    db_session.add(EventSource(event_id=event.id, source_id=source.id))
    await db_session.flush()

    index = await load_dedup_index(db_session, today=TODAY)

    assert source.id in index.by_source_id
    assert index.by_source_id[source.id] == [
        EventCandidate(id=event.id, name="Event C")
    ]
    # Event with location_id, source_id, and coords should appear in all
    # three indexes.
    assert index.by_location_id[loc.id][0].id == event.id
    assert index.by_coords[(round(40.7, 5), round(-74.0, 5))][0].id == event.id


@pytest.mark.asyncio
async def test_load_dedup_index_excludes_archived(db_session: AsyncSession) -> None:
    loc = await _make_location(db_session, name="Loc D")
    await _make_event(
        db_session,
        name="Archived",
        location=loc,
        status=EventStatus.archived,
    )

    index = await load_dedup_index(db_session, today=TODAY)

    assert index.by_location_id == {}
    assert index.dates_by_event_id == {}


@pytest.mark.asyncio
async def test_load_dedup_index_excludes_events_with_only_past_occurrences(
    db_session: AsyncSession,
) -> None:
    loc = await _make_location(db_session, name="Loc E")
    # Occurrence is older than today - RECENT_BUFFER_DAYS (10).
    await _make_event(
        db_session,
        name="Old",
        location=loc,
        occurrence_offsets=[-30],
    )

    index = await load_dedup_index(db_session, today=TODAY)

    assert index.by_location_id == {}
    assert index.dates_by_event_id == {}
