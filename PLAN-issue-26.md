# Issue #26: API Routers — Events, Locations, Websites, Feedback, Auth CRUD

Branch: `endpoints`
Issue: https://github.com/Anedu91/momaverse/issues/26

---

## Wave 1: Shared Infrastructure

- [ ] **1.1 EditLogger Service** — `backend/api/services/edit_logger.py`
  - Async functions: `log_insert()`, `log_update()`, `log_updates()`, `log_delete()`, `get_record_history()`
  - UUID via `uuid.uuid4()`, same 14 tracked tables as PHP
  - Value serialization: JSON for dicts/lists, ISO for datetimes, str for rest
  - Explicit context passing (user_id, ip, user_agent) — no global state
  - `# TODO: consider replacing with SQLAlchemy ORM events once migration is verified`

- [ ] **1.2 Response Wrapper Middleware** — `backend/api/middleware/response_wrapper.py`
  - ASGI middleware on `/api/v1/*` routes
  - 2xx → `{"success": true, ...body}`
  - 4xx/5xx → `{"success": false, "error": "message"}`
  - Non-JSON passthrough
  - Temporary — removed when frontend is refactored

- [ ] **1.3 Auth Dependencies** — `backend/api/dependencies.py` (extend)
  - JWT extraction from `Authorization: Bearer` header
  - `get_current_user()` → User or 401
  - `get_optional_user()` → User | None
  - Password hashing utilities
  - Type aliases: `CurrentUserDep`, `OptionalUserDep`
  - New deps: `python-jose[cryptography]` + `passlib[bcrypt]` (via `uv add`)

- [ ] **1.4 Shared Tag Helper** — `backend/api/services/tags.py`
  - `get_or_create_tag(db, name) -> Tag` — async get-or-create
  - Used by events, locations, websites routers

---

## Wave 2: Simple Routers

- [ ] **2.1 Feedback Router** — `backend/api/routers/feedback.py`
  - `POST /api/v1/feedback` → 201
  - Extract `User-Agent` from request header
  - Schema addition: `FeedbackResponse` in `schemas/feedback.py`

- [ ] **2.2 Auth Router** — `backend/api/routers/auth.py`
  - `POST /register` → 201 (create user, JWT + UserResponse)
  - `POST /login` → 200 (verify password, update last_login_at, JWT + UserResponse)
  - `POST /logout` → 204
  - `GET /me` → 200/401
  - Schema addition: `AuthResponse` in `schemas/auth.py`

---

## Wave 3: CRUD Routers

- [ ] **3.1 Locations Router** — `backend/api/routers/locations.py`
  - `GET /` — list with `event_count` subquery, order by name
  - `GET /{id}` — detail with selectinload (alternate_names, tags, websites)
  - `GET /{id}/history` — via EditLogger
  - `POST /` — create + alternate_names + get-or-create tags + log
  - `PUT /{id}` — partial update + replace alternate_names/tags if provided + log
  - `DELETE /{id}` — delete guard (409 if events reference) + log + delete
  - Schema additions: `LocationListItem` (with `event_count`), add `websites` to `LocationDetailResponse`

- [ ] **3.2 Websites Router** — `backend/api/routers/websites.py`
  - `GET /` — list with `event_count` subquery
  - `GET /{id}` — detail with selectinload (urls, locations, tags)
  - `GET /{id}/history` — via EditLogger
  - `POST /` — create + urls (WebsiteUrl) + location links (WebsiteLocation) + tags (WebsiteTag) + log
  - `PUT /{id}` — partial update + replace urls/locations/tags if provided + log
  - `DELETE /{id}` — delete guard (409 if events reference) + log + delete
  - Schema addition: `WebsiteListItem` (with `event_count`)

- [ ] **3.3 Events Router** — `backend/api/routers/events.py`
  - `GET /` — list with JOINs (locations/websites) + `next_date` subquery. Filters: limit, offset, upcoming, location_id, website_id. Order by next_date ASC, name ASC
  - `GET /{id}` — detail with selectinload (occurrences, urls, tags) + joinedload (location, website)
  - `GET /{id}/history` — via EditLogger
  - `POST /` — create + nested occurrences + urls + get-or-create tags + log
  - `PUT /{id}` — partial update scalars + replace occurrences/urls/tags if provided + log
  - `DELETE /{id}` — log snapshot + cascade delete
  - Schema additions: `EventListItem` (with `next_date`, `location_display_name`, `website_name`)

---

## Wave 4: Wire Up

- [ ] **4.1 Register Routers** — `backend/api/main.py`
  - `include_router()` for all 5 routers
  - Add response wrapper middleware
  - Middleware order: CORS → response wrapper

- [ ] **4.2 Router Package** — `backend/api/routers/__init__.py`

---

## Wave 5: Tests

- [ ] **5.1 Test Infrastructure** — `backend/tests/conftest.py`
  - Async fixtures: test DB session with transaction rollback
  - `AsyncClient` (httpx) fixture
  - Factory fixtures (users, events, locations, websites)

- [ ] **5.2 Router Tests**
  - [ ] `tests/routers/test_feedback.py` — POST happy path, missing message, max length
  - [ ] `tests/routers/test_auth.py` — register, login, logout, me, duplicate 409, wrong password 401
  - [ ] `tests/routers/test_locations.py` — CRUD happy path, lat/lng 422, delete guard 409, history
  - [ ] `tests/routers/test_websites.py` — CRUD happy path, delete guard 409, history
  - [ ] `tests/routers/test_events.py` — CRUD happy path, filters, nested create/update, history

- [ ] **5.3 Service Tests**
  - [ ] `tests/services/test_edit_logger.py` — log_insert, log_update (skip unchanged), log_updates, log_delete, get_record_history
  - [ ] `tests/middleware/test_response_wrapper.py` — success wrapping, error wrapping, non-JSON passthrough

---

## Schema Changes Summary

| File | Addition | Reason |
|------|----------|--------|
| `schemas/feedback.py` | `FeedbackResponse` | Return created feedback with id + created_at |
| `schemas/auth.py` | `AuthResponse(token, user)` | JWT token + user data wrapper |
| `schemas/event.py` | `EventListItem` (+next_date, location_display_name, website_name) | List endpoint computed fields |
| `schemas/location.py` | `LocationListItem` (+event_count) | List endpoint event count |
| `schemas/location.py` | Add `websites` to `LocationDetailResponse` | PHP returns linked websites |
| `schemas/website.py` | `WebsiteListItem` (+event_count) | List endpoint event count |
| `schemas/edit.py` | `EditHistoryEntry` (+user_name, user_email) | History endpoint |

---

## New Dependencies

```bash
uv add python-jose[cryptography] passlib[bcrypt]
```

---

## Related Issues

- Depends on: #25 (config, db session, auth deps) ✅ Complete
- Blocks: #30 (wire up routers)
- Related: #40 (unified soft delete — future research)
