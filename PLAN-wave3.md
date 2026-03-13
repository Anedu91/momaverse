# Wave 3: CRUD Routers — Detailed Implementation Plan

Branch: `endpoints`
Parent plan: `PLAN-issue-26.md`
Assumes: Wave 1 (shared infra) and Wave 2 (feedback, auth) are complete.

---

## Pre-requisites (from Wave 1 & 2, assumed done)

- `SessionDep`, `CurrentUserDep`, `OptionalUserDep` in `dependencies.py`
- `edit_logger.py` — `log_insert`, `log_update`, `log_updates`, `log_delete`, `get_record_history`
- `tags.py` — `get_or_create_tag(db, name) -> Tag`
- `response_wrapper.py` middleware active
- Auth router mounted (JWT available)

---

## Schema Additions Required

Before building routers, add these schemas that the PLAN specifies but don't exist yet.

### S1. `LocationListItem` — `backend/api/schemas/location.py`

```python
class LocationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str | None = None
    very_short_name: str | None = None
    emoji: str | None = None
    event_count: int = 0
```

- Subset of `LocationResponse` + computed `event_count`
- Used only by the list endpoint to avoid loading full detail

### S2. Add `websites` to `LocationDetailResponse` — `backend/api/schemas/location.py`

```python
class LocationDetailResponse(LocationResponse):
    alternate_names: list[AlternateNameResponse] = []
    tags: list[TagResponse] = []
    websites: list["WebsiteResponse"] = []  # ADD THIS
```

- Import `WebsiteResponse` from `schemas/website.py`
- Matches PHP behavior that returns linked websites on location detail

### S3. `WebsiteListItem` — `backend/api/schemas/website.py`

```python
class WebsiteListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    base_url: str | None = None
    disabled: bool = False
    event_count: int = 0
```

### S4. `EventListItem` — `backend/api/schemas/event.py`

```python
class EventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str | None = None
    emoji: str | None = None
    location_id: int | None = None
    location_display_name: str | None = None
    website_id: int | None = None
    website_name: str | None = None
    next_date: date | None = None
    archived: bool = False
    suppressed: bool = False
```

- `location_display_name` = `Location.short_name ?? Location.name` (COALESCE)
- `website_name` = `Website.name`
- `next_date` = MIN of future `EventOccurrence.start_date` (subquery)

---

## 3.1 Locations Router — `backend/api/routers/locations.py`

### File: `backend/api/routers/locations.py`

```
router = APIRouter(prefix="/locations", tags=["locations"])
```

### Endpoints

#### `GET /` — List locations

| Aspect | Detail |
|--------|--------|
| Auth | None (public) |
| Query params | `limit: int = 50`, `offset: int = 0` |
| Response | `PaginatedResponse[LocationListItem]` |
| Query | SELECT locations + subquery COUNT events WHERE location_id = l.id AS event_count |
| Order | `name ASC` |
| Notes | Use `func.count(Event.id)` as a correlated subquery or `outerjoin` + `group_by` |

**SQL sketch:**
```python
event_count_sq = (
    select(func.count(Event.id))
    .where(Event.location_id == Location.id)
    .correlate(Location)
    .scalar_subquery()
    .label("event_count")
)
stmt = select(Location, event_count_sq).order_by(Location.name)
total_stmt = select(func.count(Location.id))
```

**Response mapping:**
- Map each `(Location, event_count)` row to `LocationListItem` manually via dict unpacking

#### `GET /{id}` — Location detail

| Aspect | Detail |
|--------|--------|
| Auth | None (public) |
| Response | `LocationDetailResponse` (with `websites` field) |
| Eager load | `selectinload(Location.alternate_names)`, `selectinload(Location.tags)`, `selectinload(Location.websites)` |
| 404 | Raise `HTTPException(404)` if not found |

#### `GET /{id}/history` — Edit history

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` (admin only) |
| Response | `list[EditResponse]` |
| Implementation | `get_record_history(db, table_name="locations", record_id=id)` |
| Serialize | `EditResponse.model_validate(edit)` for each |

#### `POST /` — Create location

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` |
| Request body | `LocationCreate` |
| Response | `LocationDetailResponse`, status 201 |
| Steps | 1. Create `Location` from scalar fields |
|        | 2. `db.flush()` to get `location.id` |
|        | 3. Create `LocationAlternateName` rows for each `data.alternate_names` |
|        | 4. For each `data.tags`: `get_or_create_tag(db, name)` → create `LocationTag(location_id, tag_id)` |
|        | 5. `log_insert(db, table_name="locations", record_id=location.id, record_data={...}, user_id=user.id, editor_ip=request.client.host, editor_user_agent=...)` |
|        | 6. `db.commit()` + `db.refresh(location)` with selectinload |
| IP/UA | Extract from `Request` object: `request.client.host`, `request.headers.get("user-agent")` |

#### `PUT /{id}` — Update location

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` |
| Request body | `LocationUpdate` |
| Response | `LocationDetailResponse` |
| Steps | 1. Fetch location or 404 |
|        | 2. Snapshot old scalar values as dict |
|        | 3. Apply `data.model_dump(exclude_unset=True)` scalars to location |
|        | 4. If `alternate_names` provided: delete existing `LocationAlternateName` rows, create new ones |
|        | 5. If `tags` provided: delete existing `LocationTag` rows, get-or-create + insert new ones |
|        | 6. `log_updates(db, table_name="locations", ...)` with old/new scalar dicts |
|        | 7. `db.commit()` + refresh with selectinload |
| Partial update | Only fields included in the request body are changed (`exclude_unset=True`) |

#### `DELETE /{id}` — Delete location

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` |
| Response | 204 No Content |
| Steps | 1. Fetch location or 404 |
|        | 2. **Delete guard**: check if any `Event` references this `location_id` → 409 Conflict |
|        | 3. Snapshot record data for audit |
|        | 4. `log_delete(db, table_name="locations", ...)` |
|        | 5. `await db.delete(location)` |
|        | 6. `await db.commit()` |
| Guard query | `select(func.count(Event.id)).where(Event.location_id == id)` |

### Helper: `_get_location_or_404`

```python
async def _get_location_or_404(db: AsyncSession, location_id: int) -> Location:
    stmt = select(Location).where(Location.id == location_id).options(
        selectinload(Location.alternate_names),
        selectinload(Location.tags),
        selectinload(Location.websites),
    )
    location = await db.scalar(stmt)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return location
```

---

## 3.2 Websites Router — `backend/api/routers/websites.py`

### File: `backend/api/routers/websites.py`

```
router = APIRouter(prefix="/websites", tags=["websites"])
```

### Endpoints

#### `GET /` — List websites

| Aspect | Detail |
|--------|--------|
| Auth | None (public) |
| Query params | `limit: int = 50`, `offset: int = 0` |
| Response | `PaginatedResponse[WebsiteListItem]` |
| Query | SELECT websites + subquery COUNT events WHERE website_id = w.id AS event_count |
| Order | `name ASC` |

#### `GET /{id}` — Website detail

| Aspect | Detail |
|--------|--------|
| Auth | None (public) |
| Response | `WebsiteDetailResponse` |
| Eager load | `selectinload(Website.urls)`, `selectinload(Website.locations)`, `selectinload(Website.tags)` |
| 404 | Raise `HTTPException(404)` |

#### `GET /{id}/history` — Edit history

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` |
| Response | `list[EditResponse]` |
| Implementation | `get_record_history(db, table_name="websites", record_id=id)` |

#### `POST /` — Create website

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` |
| Request body | `WebsiteCreate` |
| Response | `WebsiteDetailResponse`, status 201 |
| Steps | 1. Create `Website` from scalar fields (name, description, base_url, max_pages) |
|        | 2. `db.flush()` to get `website.id` |
|        | 3. Create `WebsiteUrl` rows for each `data.urls` (set `sort_order` from index) |
|        | 4. For each `data.location_ids`: validate location exists → create `WebsiteLocation(website_id, location_id)` |
|        | 5. For each `data.tags`: `get_or_create_tag(db, name)` → create `WebsiteTag(website_id, tag_id)` |
|        | 6. `log_insert(...)` |
|        | 7. `db.commit()` + refresh with selectinload |
| Location validation | Query each location_id exists, raise 422 if any missing |

#### `PUT /{id}` — Update website

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` |
| Request body | `WebsiteUpdate` |
| Response | `WebsiteDetailResponse` |
| Steps | 1. Fetch website or 404 |
|        | 2. Snapshot old scalar values |
|        | 3. Apply scalar updates from `exclude_unset=True` |
|        | 4. If `urls` provided: delete existing `WebsiteUrl` rows, create new ones with sort_order from index |
|        | 5. If `location_ids` provided: delete existing `WebsiteLocation` rows, validate + insert new ones |
|        | 6. If `tags` provided: delete existing `WebsiteTag` rows, get-or-create + insert new ones |
|        | 7. `log_updates(...)` |
|        | 8. `db.commit()` + refresh |

#### `DELETE /{id}` — Delete website

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` |
| Response | 204 No Content |
| Steps | 1. Fetch website or 404 |
|        | 2. **Delete guard**: check if any `Event` references this `website_id` → 409 Conflict |
|        | 3. Snapshot + `log_delete(...)` |
|        | 4. `await db.delete(website)` + commit |

### Helper: `_get_website_or_404`

Same pattern as locations — select with selectinload for urls, locations, tags.

---

## 3.3 Events Router — `backend/api/routers/events.py`

### File: `backend/api/routers/events.py`

```
router = APIRouter(prefix="/events", tags=["events"])
```

### Endpoints

#### `GET /` — List events

| Aspect | Detail |
|--------|--------|
| Auth | None (public) |
| Query params | `limit: int = 50`, `offset: int = 0`, `upcoming: bool = False`, `location_id: int | None = None`, `website_id: int | None = None` |
| Response | `PaginatedResponse[EventListItem]` |
| Joins | LEFT JOIN `locations` → `COALESCE(Location.short_name, Location.name)` as `location_display_name` |
|       | LEFT JOIN `websites` → `Website.name` as `website_name` |
| Subquery | `next_date` = `SELECT MIN(start_date) FROM event_occurrences WHERE event_id = e.id AND start_date >= CURRENT_DATE` |
| Filters | `upcoming=True` → only events with `next_date IS NOT NULL` |
|         | `location_id` → `Event.location_id == location_id` |
|         | `website_id` → `Event.website_id == website_id` |
| Order | `next_date ASC NULLS LAST`, `name ASC` |

**SQL sketch:**
```python
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

location_display = func.coalesce(Location.short_name, Location.name).label("location_display_name")

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
```

**Response mapping:**
- Construct `EventListItem` from Event attrs + computed columns

#### `GET /{id}` — Event detail

| Aspect | Detail |
|--------|--------|
| Auth | None (public) |
| Response | `EventDetailResponse` |
| Eager load | `selectinload(Event.occurrences)`, `selectinload(Event.urls)`, `selectinload(Event.tags)` |
|           | `joinedload(Event.location)`, `joinedload(Event.website)` |
| 404 | Raise `HTTPException(404)` |

#### `GET /{id}/history` — Edit history

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` |
| Response | `list[EditResponse]` |
| Implementation | `get_record_history(db, table_name="events", record_id=id)` |

#### `POST /` — Create event

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` |
| Request body | `EventCreate` |
| Response | `EventDetailResponse`, status 201 |
| Steps | 1. Create `Event` from scalar fields |
|        | 2. `db.flush()` to get `event.id` |
|        | 3. Create `EventOccurrence` rows (set `sort_order` from index) |
|        | 4. Create `EventUrl` rows (set `sort_order` from index) |
|        | 5. For each `data.tags`: `get_or_create_tag(db, name)` → create `EventTag(event_id, tag_id)` |
|        | 6. `log_insert(...)` |
|        | 7. `db.commit()` + refresh with selectinload |
| Note | `location_id` and `website_id` are optional FKs — if provided, should validate they exist (422 if not) |

#### `PUT /{id}` — Update event

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` |
| Request body | `EventUpdate` |
| Response | `EventDetailResponse` |
| Steps | 1. Fetch event or 404 |
|        | 2. Snapshot old scalar values |
|        | 3. Apply scalar updates from `exclude_unset=True` |
|        | 4. If `occurrences` provided: delete existing `EventOccurrence` rows, create new ones with sort_order |
|        | 5. If `urls` provided: delete existing `EventUrl` rows, create new ones with sort_order |
|        | 6. If `tags` provided: delete existing `EventTag` rows, get-or-create + insert new ones |
|        | 7. `log_updates(...)` |
|        | 8. `db.commit()` + refresh |

#### `DELETE /{id}` — Delete event

| Aspect | Detail |
|--------|--------|
| Auth | `CurrentUserDep` |
| Response | 204 No Content |
| Steps | 1. Fetch event or 404 |
|        | 2. Snapshot record data for audit |
|        | 3. `log_delete(db, table_name="events", ...)` |
|        | 4. `await db.delete(event)` — CASCADE handles occurrences, urls, tags, sources |
|        | 5. `await db.commit()` |
| Note | No delete guard — events can always be deleted (children cascade) |

### Helper: `_get_event_or_404`

```python
async def _get_event_or_404(db: AsyncSession, event_id: int) -> Event:
    stmt = select(Event).where(Event.id == event_id).options(
        selectinload(Event.occurrences),
        selectinload(Event.urls),
        selectinload(Event.tags),
        joinedload(Event.location),
        joinedload(Event.website),
    )
    event = await db.scalar(stmt)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
```

---

## Shared Patterns Across All Three Routers

### Edit Logging Context

Every mutating endpoint (POST, PUT, DELETE) needs:
```python
request: Request  # FastAPI Request object

user_id = user.id
editor_ip = request.client.host if request.client else None
raw_ua = request.headers.get("user-agent")
editor_user_agent = raw_ua[:500] if raw_ua else None
```

### Replace-children Pattern (tags, alternate_names, urls, etc.)

Used on PUT when a list field is provided (not None):
```python
# 1. Delete existing join rows
await db.execute(delete(LocationTag).where(LocationTag.location_id == location.id))

# 2. Create new ones
for tag_name in data.tags:
    tag = await get_or_create_tag(db, tag_name)
    db.add(LocationTag(location_id=location.id, tag_id=tag.id))
```

### Record Snapshot for Logging

```python
def _snapshot(record) -> dict:
    """Extract loggable scalar fields from an ORM instance."""
    return {
        c.key: getattr(record, c.key)
        for c in inspect(record).mapper.column_attrs
    }
```

---

## Execution Order

1. **Schema additions** (S1–S4) — can all be done in parallel
2. **Locations router** (3.1) — no dependency on other Wave 3 routers
3. **Websites router** (3.2) — no dependency on other Wave 3 routers
4. **Events router** (3.3) — no dependency on other Wave 3 routers

Routers 3.1, 3.2, and 3.3 are independent and can be built in parallel (worktree agents).

---

## Files Created / Modified

| Action | File |
|--------|------|
| Modify | `backend/api/schemas/location.py` — add `LocationListItem`, add `websites` to `LocationDetailResponse` |
| Modify | `backend/api/schemas/website.py` — add `WebsiteListItem` |
| Modify | `backend/api/schemas/event.py` — add `EventListItem` |
| Create | `backend/api/routers/locations.py` |
| Create | `backend/api/routers/websites.py` |
| Create | `backend/api/routers/events.py` |
