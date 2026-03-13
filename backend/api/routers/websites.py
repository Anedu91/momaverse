from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from api.dependencies import CurrentUserDep, SessionDep
from api.models.event import Event
from api.models.location import Location
from api.models.website import Website, WebsiteLocation, WebsiteTag, WebsiteUrl
from api.schemas.common import PaginatedResponse
from api.schemas.edit import EditResponse
from api.schemas.website import (
    WebsiteCreate,
    WebsiteDetailResponse,
    WebsiteListItem,
    WebsiteUpdate,
)
from api.services.edit_logger import (
    get_record_history,
    log_delete,
    log_insert,
    log_updates,
)
from api.services.tags import get_or_create_tag
from api.services.utils import extract_editor_context, snapshot_record

router = APIRouter(prefix="/websites", tags=["websites"])


async def _refresh_website(db: SessionDep, website_id: int) -> Website:
    """Re-fetch a website with populate_existing to bypass stale viewonly caches."""
    stmt = (
        select(Website)
        .where(Website.id == website_id)
        .options(
            selectinload(Website.urls),
            selectinload(Website.locations),
            selectinload(Website.tags),
        )
        .execution_options(populate_existing=True)
    )
    website = await db.scalar(stmt)
    if website is None:
        raise HTTPException(status_code=404, detail="Website not found")
    return website


async def _get_website_or_404(db: SessionDep, website_id: int) -> Website:
    stmt = (
        select(Website)
        .where(Website.id == website_id)
        .options(
            selectinload(Website.urls),
            selectinload(Website.locations),
            selectinload(Website.tags),
        )
    )
    website = await db.scalar(stmt)
    if website is None:
        raise HTTPException(status_code=404, detail="Website not found")
    return website


async def _validate_location_ids(db: SessionDep, location_ids: list[int]) -> None:
    """Raise 422 if any location_id does not exist."""
    if not location_ids:
        return
    existing = await db.scalars(
        select(Location.id).where(Location.id.in_(location_ids))
    )
    found = set(existing.all())
    missing = set(location_ids) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Locations not found: {sorted(missing)}",
        )


@router.get("/", response_model=PaginatedResponse[WebsiteListItem])
async def list_websites(
    db: SessionDep,
    # TODO: Add upper bound validation (e.g. Query(ge=1, le=200)) to prevent
    # unbounded queries that could exhaust memory.
    limit: int = 50,
    offset: int = 0,
) -> PaginatedResponse[WebsiteListItem]:
    event_count_sq = (
        select(func.count(Event.id))
        .where(Event.website_id == Website.id)
        .correlate(Website)
        .scalar_subquery()
        .label("event_count")
    )

    stmt = (
        select(Website, event_count_sq)
        .order_by(Website.name)
        .limit(limit)
        .offset(offset)
    )
    total_stmt = select(func.count(Website.id))

    result = await db.execute(stmt)
    rows = result.all()
    total = await db.scalar(total_stmt) or 0

    data = [
        WebsiteListItem(
            id=ws.id,
            name=ws.name,
            description=ws.description,
            base_url=ws.base_url,
            disabled=ws.disabled,
            event_count=event_count,
        )
        for ws, event_count in rows
    ]
    return PaginatedResponse(data=data, total=total)


@router.get("/{website_id}", response_model=WebsiteDetailResponse)
async def get_website(
    website_id: int,
    db: SessionDep,
) -> WebsiteDetailResponse:
    website = await _get_website_or_404(db, website_id)
    return WebsiteDetailResponse.model_validate(website)


@router.get("/{website_id}/history", response_model=list[EditResponse])
async def get_website_history(
    website_id: int,
    db: SessionDep,
    _user: CurrentUserDep,
) -> list[EditResponse]:
    edits = await get_record_history(db, table_name="websites", record_id=website_id)
    return [EditResponse.model_validate(e) for e in edits]


@router.post(
    "/", response_model=WebsiteDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_website(
    data: WebsiteCreate,
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
) -> WebsiteDetailResponse:
    website = Website(
        name=data.name,
        description=data.description,
        base_url=data.base_url,
        max_pages=data.max_pages,
    )
    db.add(website)
    await db.flush()

    for idx, url in enumerate(data.urls):
        db.add(WebsiteUrl(website_id=website.id, url=url, sort_order=idx))

    await _validate_location_ids(db, data.location_ids)
    for loc_id in data.location_ids:
        db.add(WebsiteLocation(website_id=website.id, location_id=loc_id))

    for tag_name in data.tags:
        tag = await get_or_create_tag(db, tag_name)
        db.add(WebsiteTag(website_id=website.id, tag_id=tag.id))

    editor_ip, editor_user_agent = extract_editor_context(request)

    await log_insert(
        db,
        table_name="websites",
        record_id=website.id,
        record_data=snapshot_record(website),
        user_id=user.id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )

    await db.commit()
    website = await _refresh_website(db, website.id)
    return WebsiteDetailResponse.model_validate(website)


@router.put("/{website_id}", response_model=WebsiteDetailResponse)
async def update_website(
    website_id: int,
    data: WebsiteUpdate,
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
) -> WebsiteDetailResponse:
    website = await _get_website_or_404(db, website_id)
    old_data = snapshot_record(website)

    update_fields = data.model_dump(exclude_unset=True)
    scalar_fields = {
        k: v
        for k, v in update_fields.items()
        if k not in ("urls", "location_ids", "tags")
    }
    for field, value in scalar_fields.items():
        setattr(website, field, value)

    # Replace urls if provided
    if "urls" in update_fields:
        await db.execute(delete(WebsiteUrl).where(WebsiteUrl.website_id == website.id))
        for idx, url in enumerate(data.urls):  # type: ignore[arg-type]
            db.add(WebsiteUrl(website_id=website.id, url=url, sort_order=idx))

    # Replace location_ids if provided
    if "location_ids" in update_fields:
        await _validate_location_ids(db, data.location_ids or [])
        await db.execute(
            delete(WebsiteLocation).where(WebsiteLocation.website_id == website.id)
        )
        for loc_id in data.location_ids or []:
            db.add(WebsiteLocation(website_id=website.id, location_id=loc_id))

    # Replace tags if provided
    if "tags" in update_fields:
        await db.execute(delete(WebsiteTag).where(WebsiteTag.website_id == website.id))
        for tag_name in data.tags or []:
            tag = await get_or_create_tag(db, tag_name)
            db.add(WebsiteTag(website_id=website.id, tag_id=tag.id))

    new_data = snapshot_record(website)
    editor_ip, editor_user_agent = extract_editor_context(request)

    await log_updates(
        db,
        table_name="websites",
        record_id=website.id,
        old_record=old_data,
        new_record=new_data,
        user_id=user.id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )

    await db.commit()
    website = await _refresh_website(db, website.id)
    return WebsiteDetailResponse.model_validate(website)


@router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_website(
    website_id: int,
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
) -> Response:
    website = await _get_website_or_404(db, website_id)

    # Delete guard: check if any events reference this website
    event_count = await db.scalar(
        select(func.count(Event.id)).where(Event.website_id == website_id)
    )
    if event_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete website with associated events",
        )

    record_data = snapshot_record(website)
    editor_ip, editor_user_agent = extract_editor_context(request)

    await log_delete(
        db,
        table_name="websites",
        record_id=website.id,
        record_data=record_data,
        user_id=user.id,
        editor_ip=editor_ip,
        editor_user_agent=editor_user_agent,
    )

    # Delete children before parent (ORM delete doesn't use DB CASCADE)
    await db.execute(delete(WebsiteUrl).where(WebsiteUrl.website_id == website.id))
    await db.execute(
        delete(WebsiteLocation).where(WebsiteLocation.website_id == website.id)
    )
    await db.execute(delete(WebsiteTag).where(WebsiteTag.website_id == website.id))
    await db.delete(website)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
