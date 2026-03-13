from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import joinedload, selectinload

from api.dependencies import CurrentUserDep, SessionDep
from api.models.event import Event, EventOccurrence, EventTag, EventUrl
from api.models.location import Location
from api.models.website import Website
from api.schemas.common import PaginatedResponse
from api.schemas.edit import EditResponse
from api.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventListItem,
    EventUpdate,
)
from api.services.edit_logger import (
    get_record_history,
    log_delete,
    log_insert,
    log_updates,
)
from api.services.tags import get_or_create_tag

router = APIRouter(prefix="/events", tags=["events"])


def _snapshot(record: Event) -> dict[str, object]:
    """Extract loggable scalar fields from an Event instance."""
    from sqlalchemy import inspect as sa_inspect

    return {
        c.key: getattr(record, c.key) for c in sa_inspect(record).mapper.column_attrs
    }


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
            joinedload(Event.website),
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
        .where(Event.id == event_id)
        .options(
            selectinload(Event.occurrences),
            selectinload(Event.urls),
            selectinload(Event.tags),
            joinedload(Event.location),
            joinedload(Event.website),
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
    website_id: int | None = None,
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

    stmt = (
        select(
            Event,
            next_date_sq,
            location_display,
            Website.name.label("website_name"),
        )
        .outerjoin(Location, Event.location_id == Location.id)
        .outerjoin(Website, Event.website_id == Website.id)
    )

    # Build count query with same filters
    count_stmt = select(func.count(Event.id))

    # Apply filters
    if upcoming:
        # Only events with a future occurrence
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

    if website_id is not None:
        stmt = stmt.where(Event.website_id == website_id)
        count_stmt = count_stmt.where(Event.website_id == website_id)

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
            website_id=event.website_id,
            website_name=ws_name,
            next_date=next_date,
            archived=event.archived,
            suppressed=event.suppressed,
        )
        for event, next_date, loc_display, ws_name in rows
    ]
    return PaginatedResponse(data=data, total=total)


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: int,
    db: SessionDep,
) -> EventDetailResponse:
    event = await _get_event_or_404(db, event_id)
    return EventDetailResponse.model_validate(event)


@router.get("/{event_id}/history", response_model=list[EditResponse])
async def get_event_history(
    event_id: int,
    db: SessionDep,
    _user: CurrentUserDep,
) -> list[EditResponse]:
    edits = await get_record_history(db, table_name="events", record_id=event_id)
    return [EditResponse.model_validate(e) for e in edits]


@router.post(
    "/", response_model=EventDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_event(
    data: EventCreate,
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
) -> EventDetailResponse:
    # Validate FK references if provided
    if data.location_id is not None:
        loc = await db.scalar(
            select(Location.id).where(Location.id == data.location_id)
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
        location_name=data.location_name,
        sublocation=data.sublocation,
    )
    db.add(event)
    await db.flush()

    for idx, occ in enumerate(data.occurrences):
        db.add(
            EventOccurrence(
                event_id=event.id,
                start_date=occ.start_date,
                start_time=occ.start_time,
                end_date=occ.end_date,
                end_time=occ.end_time,
                sort_order=idx,
            )
        )

    for idx, url in enumerate(data.urls):
        db.add(EventUrl(event_id=event.id, url=url, sort_order=idx))

    for tag_name in data.tags:
        tag = await get_or_create_tag(db, tag_name)
        db.add(EventTag(event_id=event.id, tag_id=tag.id))

    editor_ip = request.client.host if request.client else None
    raw_ua = request.headers.get("user-agent")
    editor_user_agent = raw_ua[:500] if raw_ua else None

    await log_insert(
        db,
        table_name="events",
        record_id=event.id,
        record_data=_snapshot(event),
        user_id=user.id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )

    await db.commit()
    event = await _refresh_event(db, event.id)
    return EventDetailResponse.model_validate(event)


@router.put("/{event_id}", response_model=EventDetailResponse)
async def update_event(
    event_id: int,
    data: EventUpdate,
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
) -> EventDetailResponse:
    event = await _get_event_or_404(db, event_id)
    old_data = _snapshot(event)

    update_fields = data.model_dump(exclude_unset=True)
    scalar_fields = {
        k: v
        for k, v in update_fields.items()
        if k not in ("occurrences", "urls", "tags")
    }

    # Validate location_id FK if being updated
    if "location_id" in scalar_fields and scalar_fields["location_id"] is not None:
        loc = await db.scalar(
            select(Location.id).where(Location.id == scalar_fields["location_id"])
        )
        if loc is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Location {scalar_fields['location_id']} not found",
            )

    for field, value in scalar_fields.items():
        setattr(event, field, value)

    # Replace occurrences if provided
    if "occurrences" in update_fields:
        await db.execute(
            delete(EventOccurrence).where(EventOccurrence.event_id == event.id)
        )
        for idx, occ in enumerate(data.occurrences):  # type: ignore[arg-type]
            db.add(
                EventOccurrence(
                    event_id=event.id,
                    start_date=occ.start_date,
                    start_time=occ.start_time,
                    end_date=occ.end_date,
                    end_time=occ.end_time,
                    sort_order=idx,
                )
            )

    # Replace urls if provided
    if "urls" in update_fields:
        await db.execute(delete(EventUrl).where(EventUrl.event_id == event.id))
        for idx, url in enumerate(data.urls):  # type: ignore[arg-type]
            db.add(EventUrl(event_id=event.id, url=url, sort_order=idx))

    # Replace tags if provided
    if "tags" in update_fields:
        await db.execute(delete(EventTag).where(EventTag.event_id == event.id))
        for tag_name in data.tags or []:
            tag = await get_or_create_tag(db, tag_name)
            db.add(EventTag(event_id=event.id, tag_id=tag.id))

    new_data = _snapshot(event)
    editor_ip = request.client.host if request.client else None
    raw_ua = request.headers.get("user-agent")
    editor_user_agent = raw_ua[:500] if raw_ua else None

    await log_updates(
        db,
        table_name="events",
        record_id=event.id,
        old_record=old_data,
        new_record=new_data,
        user_id=user.id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )

    await db.commit()
    event = await _refresh_event(db, event.id)
    return EventDetailResponse.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
) -> Response:
    event = await _get_event_or_404(db, event_id)

    record_data = _snapshot(event)
    editor_ip = request.client.host if request.client else None
    raw_ua = request.headers.get("user-agent")
    editor_user_agent = raw_ua[:500] if raw_ua else None

    await log_delete(
        db,
        table_name="events",
        record_id=event.id,
        record_data=record_data,
        user_id=user.id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )

    # Delete children before parent (ORM delete doesn't use DB CASCADE)
    await db.execute(
        delete(EventOccurrence).where(EventOccurrence.event_id == event.id)
    )
    await db.execute(delete(EventUrl).where(EventUrl.event_id == event.id))
    await db.execute(delete(EventTag).where(EventTag.event_id == event.id))
    await db.delete(event)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
