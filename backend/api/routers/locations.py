from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from api.dependencies import CurrentUserDep, SessionDep
from api.models.event import Event
from api.models.location import Location, LocationAlternateName, LocationTag
from api.schemas.common import PaginatedResponse
from api.schemas.edit import EditResponse
from api.schemas.location import (
    LocationCreate,
    LocationDetailResponse,
    LocationListItem,
    LocationUpdate,
)
from api.services.edit_logger import (
    get_record_history,
    log_delete,
    log_insert,
    log_updates,
)
from api.services.tags import get_or_create_tag

router = APIRouter(prefix="/locations", tags=["locations"])


def _snapshot(record: Location) -> dict[str, object]:
    """Extract loggable scalar fields from a Location instance."""
    from sqlalchemy import inspect as sa_inspect

    return {
        c.key: getattr(record, c.key) for c in sa_inspect(record).mapper.column_attrs
    }


async def _refresh_location(db: SessionDep, location_id: int) -> Location:
    """Re-fetch a location with populate_existing to bypass stale viewonly caches."""
    stmt = (
        select(Location)
        .where(Location.id == location_id)
        .options(
            selectinload(Location.alternate_names),
            selectinload(Location.tags),
            selectinload(Location.websites),
        )
        .execution_options(populate_existing=True)
    )
    location = await db.scalar(stmt)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


async def _get_location_or_404(db: SessionDep, location_id: int) -> Location:
    stmt = (
        select(Location)
        .where(Location.id == location_id)
        .options(
            selectinload(Location.alternate_names),
            selectinload(Location.tags),
            selectinload(Location.websites),
        )
    )
    location = await db.scalar(stmt)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.get("/", response_model=PaginatedResponse[LocationListItem])
async def list_locations(
    db: SessionDep,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedResponse[LocationListItem]:
    event_count_sq = (
        select(func.count(Event.id))
        .where(Event.location_id == Location.id)
        .correlate(Location)
        .scalar_subquery()
        .label("event_count")
    )

    stmt = (
        select(Location, event_count_sq)
        .order_by(Location.name)
        .limit(limit)
        .offset(offset)
    )
    total_stmt = select(func.count(Location.id))

    result = await db.execute(stmt)
    rows = result.all()
    total = await db.scalar(total_stmt) or 0

    data = [
        LocationListItem(
            id=loc.id,
            name=loc.name,
            short_name=loc.short_name,
            very_short_name=loc.very_short_name,
            emoji=loc.emoji,
            event_count=event_count,
        )
        for loc, event_count in rows
    ]
    return PaginatedResponse(data=data, total=total)


@router.get("/{location_id}", response_model=LocationDetailResponse)
async def get_location(
    location_id: int,
    db: SessionDep,
) -> LocationDetailResponse:
    location = await _get_location_or_404(db, location_id)
    return LocationDetailResponse.model_validate(location)


@router.get("/{location_id}/history", response_model=list[EditResponse])
async def get_location_history(
    location_id: int,
    db: SessionDep,
    _user: CurrentUserDep,
) -> list[EditResponse]:
    edits = await get_record_history(db, table_name="locations", record_id=location_id)
    return [EditResponse.model_validate(e) for e in edits]


@router.post(
    "/", response_model=LocationDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_location(
    data: LocationCreate,
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
) -> LocationDetailResponse:
    location = Location(
        name=data.name,
        short_name=data.short_name,
        very_short_name=data.very_short_name,
        address=data.address,
        description=data.description,
        lat=data.lat,
        lng=data.lng,
        emoji=data.emoji,
        alt_emoji=data.alt_emoji,
    )
    db.add(location)
    await db.flush()

    for alt_name in data.alternate_names:
        db.add(LocationAlternateName(location_id=location.id, alternate_name=alt_name))

    for tag_name in data.tags:
        tag = await get_or_create_tag(db, tag_name)
        db.add(LocationTag(location_id=location.id, tag_id=tag.id))

    editor_ip = request.client.host if request.client else None
    raw_ua = request.headers.get("user-agent")
    editor_user_agent = raw_ua[:500] if raw_ua else None

    await log_insert(
        db,
        table_name="locations",
        record_id=location.id,
        record_data=_snapshot(location),
        user_id=user.id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )

    await db.commit()
    location = await _refresh_location(db, location.id)
    return LocationDetailResponse.model_validate(location)


@router.put("/{location_id}", response_model=LocationDetailResponse)
async def update_location(
    location_id: int,
    data: LocationUpdate,
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
) -> LocationDetailResponse:
    location = await _get_location_or_404(db, location_id)
    old_data = _snapshot(location)

    # Apply scalar updates
    update_fields = data.model_dump(exclude_unset=True)
    scalar_fields = {
        k: v for k, v in update_fields.items() if k not in ("alternate_names", "tags")
    }
    for field, value in scalar_fields.items():
        setattr(location, field, value)

    # Replace alternate_names if provided
    if "alternate_names" in update_fields:
        await db.execute(
            delete(LocationAlternateName).where(
                LocationAlternateName.location_id == location.id
            )
        )
        for alt_name in data.alternate_names:  # type: ignore[union-attr]
            db.add(
                LocationAlternateName(location_id=location.id, alternate_name=alt_name)
            )

    # Replace tags if provided
    if "tags" in update_fields:
        await db.execute(
            delete(LocationTag).where(LocationTag.location_id == location.id)
        )
        for tag_name in data.tags:  # type: ignore[union-attr]
            tag = await get_or_create_tag(db, tag_name)
            db.add(LocationTag(location_id=location.id, tag_id=tag.id))

    new_data = _snapshot(location)
    editor_ip = request.client.host if request.client else None
    raw_ua = request.headers.get("user-agent")
    editor_user_agent = raw_ua[:500] if raw_ua else None

    await log_updates(
        db,
        table_name="locations",
        record_id=location.id,
        old_record=old_data,
        new_record=new_data,
        user_id=user.id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )

    await db.commit()
    location = await _refresh_location(db, location.id)
    return LocationDetailResponse.model_validate(location)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: int,
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
) -> Response:
    location = await _get_location_or_404(db, location_id)

    # Delete guard: check if any events reference this location
    event_count = await db.scalar(
        select(func.count(Event.id)).where(Event.location_id == location_id)
    )
    if event_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete location with associated events",
        )

    record_data = _snapshot(location)
    editor_ip = request.client.host if request.client else None
    raw_ua = request.headers.get("user-agent")
    editor_user_agent = raw_ua[:500] if raw_ua else None

    await log_delete(
        db,
        table_name="locations",
        record_id=location.id,
        record_data=record_data,
        user_id=user.id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )

    # Delete children before parent (ORM delete doesn't use DB CASCADE)
    await db.execute(
        delete(LocationAlternateName).where(
            LocationAlternateName.location_id == location.id
        )
    )
    await db.execute(delete(LocationTag).where(LocationTag.location_id == location.id))
    await db.delete(location)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
