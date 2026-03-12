---
name: "Migration Task"
about: "PHP to Python/FastAPI migration task"
title: "[Migration]: "
labels: ["track:migration", "component:backend"]
---

## Migration Task

### Current PHP Behavior
<!-- REQUIRED: Describe what the current PHP code does. Include:
- Which PHP file(s) implement this (e.g., src/api/events.php)
- The endpoint URL and HTTP method
- Request parameters and response format
- Any database queries involved
- Authentication/authorization if applicable
-->

### Target Python Implementation
<!-- REQUIRED: Describe what the FastAPI implementation should look like. Include:
- Target router file (e.g., backend/api/routers/events.py)
- Pydantic schemas needed (request/response models)
- SQLAlchemy models/queries to use
- Any new dependencies required
-->

### Database Impact
<!-- REQUIRED: Does this migration affect the database layer?
- Tables involved
- Any query differences between PHP (MySQL legacy) and Python (PostgreSQL)
- Read-only or read-write operations
- Note: We use SQLAlchemy ORM with existing PostgreSQL schema (no migrations)
-->

### API Contract
<!-- REQUIRED: Define the exact API contract for the new endpoint -->
```
Method: GET/POST/PUT/DELETE
Path: /api/v1/...
Request Body/Params:
Response (200):
Response (4xx/5xx):
```

### Dependencies
<!-- List any issues that must be completed before this one -->
- Depends on: #
- Blocks: #

### Acceptance Criteria
<!-- REQUIRED: Checklist of conditions that must be true when this is done -->
- [ ] FastAPI endpoint returns same data as PHP endpoint
- [ ] Pydantic schemas validate input/output
- [ ] SQLAlchemy queries match expected behavior
- [ ] Unit tests cover happy path and error cases
- [ ] PHP endpoint can be deprecated after verification

### Tech Stack Reference
<!-- DO NOT EDIT: Standard tech context for the implementing agent -->
- **Framework**: FastAPI >= 0.135.1
- **ORM**: SQLAlchemy >= 2.0.48
- **Validation**: Pydantic v2
- **Database**: PostgreSQL (28 tables, see database/schema_postgres.sql)
- **Package manager**: uv
- **Testing**: pytest
- **Project root**: backend/
