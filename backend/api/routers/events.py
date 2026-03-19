from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload

from api.dependencies import CurrentUserDep, SessionDep
from api.models.base import EventStatus
from api.models.event import Event, EventOccurrence, EventTag, EventUrl
from api.models.location import Location
from api.schemas.common import PaginatedResponse
from api.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventListItem,
)
from api.services.tags import get_or_create_tag

router = APIRouter(prefix="/events", tags=["events"])


async def _refresh_event(db: SessionDep, event_id: int) -> Event:
    """Re-fetch an event with populate_existing to bypass stale viewonly caches."""
    stmt = (
        select(Event)
        .where(Event.id == event_id)
        .options(
            selectinload(Event.occurrences),
            selectinload(Event.urls),
            selectinload(Event.tags),
            joinedload(Event.location),
        )
        .execution_options(populate_existing=True)
    )
    event = await db.scalar(stmt)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


async def _get_event_or_404(db: SessionDep, event_id: int) -> Event:
    stmt = (
        select(Event)
        .where(Event.id == event_id, Event.active())
        .options(
            selectinload(Event.occurrences),
            selectinload(Event.urls),
            selectinload(Event.tags),
            joinedload(Event.location),
        )
    )
    event = await db.scalar(stmt)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/", response_model=PaginatedResponse[EventListItem])
async def list_events(
    db: SessionDep,
    limit: int = 50,
    offset: int = 0,
    upcoming: bool = False,
    location_id: int | None = None,
    status_filter: EventStatus | None = None,
    include_deleted: bool = False,
) -> PaginatedResponse[EventListItem]:
    next_date_sq = (
        select(func.min(EventOccurrence.start_date))
        .where(
            EventOccurrence.event_id == Event.id,
            EventOccurrence.start_date >= func.current_date(),
        )
        .correlate(Event)
        .scalar_subquery()
        .label("next_date")
    )

    location_display = func.coalesce(Location.short_name, Location.name).label(
        "location_display_name"
    )

    stmt = select(
        Event,
        next_date_sq,
        location_display,
    ).outerjoin(Location, Event.location_id == Location.id)

    # Build count query with same filters
    count_stmt = select(func.count(Event.id))

    # Apply soft-delete filter
    if not include_deleted:
        stmt = stmt.where(Event.active())
        count_stmt = count_stmt.where(Event.active())

    # Apply filters
    if upcoming:
        upcoming_sq = (
            select(func.min(EventOccurrence.start_date))
            .where(
                EventOccurrence.event_id == Event.id,
                EventOccurrence.start_date >= func.current_date(),
            )
            .correlate(Event)
            .scalar_subquery()
        )
        stmt = stmt.where(upcoming_sq.isnot(None))
        count_stmt = count_stmt.where(upcoming_sq.isnot(None))

    if location_id is not None:
        stmt = stmt.where(Event.location_id == location_id)
        count_stmt = count_stmt.where(Event.location_id == location_id)

    if status_filter is not None:
        stmt = stmt.where(Event.status == status_filter)
        count_stmt = count_stmt.where(Event.status == status_filter)

    stmt = (
        stmt.order_by(
            next_date_sq.asc().nulls_last(),
            Event.name.asc(),
        )
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(stmt)
    rows = result.all()
    total = await db.scalar(count_stmt) or 0

    data = [
        EventListItem(
            id=event.id,
            name=event.name,
            short_name=event.short_name,
            emoji=event.emoji,
            location_id=event.location_id,
            location_display_name=loc_display,
            status=event.status,
            next_date=next_date,
        )
        for event, next_date, loc_display in rows
    ]
    return PaginatedResponse(data=data, total=total)


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: int,
    db: SessionDep,
) -> EventDetailResponse:
    event = await _get_event_or_404(db, event_id)
    return EventDetailResponse.model_validate(event)


@router.post(
    "/", response_model=EventDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_event(
    data: EventCreate,
    db: SessionDep,
    user: CurrentUserDep,
) -> EventDetailResponse:
    # Validate FK reference (reject soft-deleted locations)
    loc = await db.scalar(
        select(Location.id).where(Location.id == data.location_id, Location.active())
    )
    if loc is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Location {data.location_id} not found",
        )

    event = Event(
        name=data.name,
        short_name=data.short_name,
        description=data.description,
        emoji=data.emoji,
        location_id=data.location_id,
        sublocation=data.sublocation,
    )
    db.add(event)
    await db.flush()

    for occ in data.occurrences:
        db.add(
            EventOccurrence(
                event_id=event.id,
                start_date=occ.start_date,
                start_time=occ.start_time,
                end_date=occ.end_date,
                end_time=occ.end_time,
            )
        )

    for url in data.urls:
        db.add(EventUrl(event_id=event.id, url=url))

    for tag_name in data.tags:
        tag = await get_or_create_tag(db, tag_name)
        db.add(EventTag(event_id=event.id, tag_id=tag.id))

    await db.commit()
    event = await _refresh_event(db, event.id)
    return EventDetailResponse.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: SessionDep,
    user: CurrentUserDep,
) -> Response:
    event = await _get_event_or_404(db, event_id)

    event.soft_delete()
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
