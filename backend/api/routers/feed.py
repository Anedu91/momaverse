from datetime import date, timedelta

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.dependencies import SessionDep
from api.models.event import Event, EventOccurrence
from api.models.location import Location

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("/events")
async def feed_events(db: SessionDep) -> list[dict[str, object]]:
    """Return events for the public frontend map (flat JSON array)."""
    cutoff = date.today() + timedelta(days=90)

    # IDs of events with at least one occurrence between today and cutoff
    event_ids_sq = (
        select(EventOccurrence.event_id)
        .where(EventOccurrence.start_date >= date.today())
        .where(EventOccurrence.start_date <= cutoff)
        .distinct()
        .subquery()
    )

    stmt = (
        select(Event)
        .where(
            Event.id.in_(select(event_ids_sq.c.event_id)),
            Event.archived.is_(False),
            Event.suppressed.is_(False),
        )
        .options(
            selectinload(Event.occurrences),
            selectinload(Event.urls),
            selectinload(Event.tags),
            selectinload(Event.location),
        )
    )

    result = await db.scalars(stmt)
    events = result.all()

    out: list[dict[str, object]] = []
    for ev in events:
        loc = ev.location
        occurrences = [
            [
                occ.start_date.isoformat() if occ.start_date else None,
                occ.start_time,
                occ.end_date.isoformat() if occ.end_date else None,
                occ.end_time,
            ]
            for occ in sorted(ev.occurrences, key=lambda o: (o.sort_order, o.id))
        ]

        out.append(
            {
                "name": ev.name,
                "short_name": ev.short_name,
                "description": ev.description,
                "emoji": ev.emoji,
                "location": loc.name if loc else ev.location_name,
                "sublocation": ev.sublocation,
                "lat": loc.lat if loc else None,
                "lng": loc.lng if loc else None,
                "tags": [t.name for t in ev.tags],
                "occurrences": occurrences,
                "urls": [
                    u.url for u in sorted(ev.urls, key=lambda u: (u.sort_order, u.id))
                ],
            }
        )

    return out


@router.get("/locations")
async def feed_locations(db: SessionDep) -> list[dict[str, object]]:
    """Return locations for the public frontend map (flat JSON array)."""
    stmt = (
        select(Location)
        .where(Location.lat.isnot(None), Location.lng.isnot(None))
        .options(selectinload(Location.tags))
    )

    result = await db.scalars(stmt)
    locations = result.all()

    return [
        {
            "name": loc.name,
            "short_name": loc.short_name,
            "very_short_name": loc.very_short_name,
            "lat": loc.lat,
            "lng": loc.lng,
            "emoji": loc.emoji,
            "address": loc.address,
            "description": loc.description,
            "tags": [t.name for t in loc.tags],
        }
        for loc in locations
    ]
