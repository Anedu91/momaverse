## Why

The pipeline (`pipeline/main.py`) owns all logic end-to-end: crawling, AI extraction, text processing, location resolution, tag handling, 7-strategy deduplication, event merging, archiving, and direct DB writes via psycopg2. This makes the scraper and backend tightly coupled — the backend is just a CRUD viewer while the pipeline contains all intelligence. We need separation of concerns so the scraper can scale independently (and evolve toward autonomous web surfing), and the backend owns its domain logic.

## What Changes

- **Split pipeline into a standalone scraper service** that only handles crawling (crawl4ai) and AI extraction (Gemini). Scraper writes `ExtractedEvent` rows to DB and signals completion via Celery task.
- **Move all domain logic to the backend** — location resolution, tag processing, short_name generation, emoji extraction, deduplication, event create/merge/archive, and audit logging become backend services triggered by Celery worker.
- **Add Celery + Redis infrastructure** — one Celery app owned by the backend. Scraper publishes tasks to it. Two queues: `default` (event processing) and `geocoding` (non-blocking).
- **Extract geocoding into async Celery task** — geocoding runs on a separate queue so it never blocks event processing.
- **BREAKING**: Pipeline no longer writes directly to events table. Backend consumer is the only writer.
- **BREAKING**: Pipeline's psycopg2 DB operations for processing/merging are removed. Backend uses SQLAlchemy async for all domain operations.

## Capabilities

### New Capabilities
- `celery-infrastructure`: Celery app configuration, Redis broker setup, worker entrypoints, task routing between queues
- `event-processing-consumer`: Backend Celery worker that consumes crawl results — location resolution, tag processing, dedup, merge, archive, audit logging (migrated from pipeline's processor.py + merger.py)
- `geocoding-worker`: Non-blocking Celery task for geocoding new locations via Geoapify, running on separate queue
- `scraper-service`: Standalone scraper service with trimmed scope — crawl + AI extract + basic sanitization only, fires Celery task on completion

### Modified Capabilities

## Impact

- **Pipeline**: `main.py` simplified to crawl+extract orchestration. `processor.py`, `merger.py`, `location_resolver.py` removed from pipeline. `db.py` trimmed to crawl/extract operations only.
- **Backend**: New services at `backend/api/services/event_processing.py` and `backend/api/services/event_merging.py`. New Celery app config. New worker entrypoint.
- **Infrastructure**: Redis instance needed (GCP Memorystore or container). Celery worker process alongside FastAPI.
- **Dependencies**: Backend gains `celery`, `redis`. Pipeline gains `celery`, `redis` (lightweight — only for task publishing).
- **DB access pattern**: Pipeline stops using psycopg2 for domain writes. Backend handles all event/location/tag writes through SQLAlchemy.
