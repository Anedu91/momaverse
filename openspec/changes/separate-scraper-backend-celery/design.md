## Context

The pipeline (`pipeline/main.py`) is a monolithic async script that runs 4 stages sequentially: crawl → extract → process → merge. It connects directly to PostgreSQL via psycopg2 with raw SQL, bypassing the backend's SQLAlchemy models entirely. The backend (FastAPI) is essentially a CRUD viewer — it doesn't own its domain logic.

The scraper needs to become an independent service that can scale and evolve (toward autonomous web surfing). The backend needs to own all event domain logic. Celery + Redis connects the two.

Current state:
- `pipeline/main.py` (orchestrator) → `crawler.py` → `extractor.py` → `processor.py` → `merger.py`
- All use `pipeline/db.py` (psycopg2, raw SQL)
- Backend has SQLAlchemy async models for the same tables but only reads them
- Geocoding exists in both: `pipeline/location_resolver.py` and `backend/api/services/geocoding.py`

## Goals / Non-Goals

**Goals:**
- Scraper as independent service: own pyproject.toml, own deploy, only crawl + AI extract
- Backend owns all domain logic: location resolution, tags, dedup, merge, archive
- Celery + Redis as the async communication layer between services
- Non-blocking geocoding on separate Celery queue
- Incremental migration — pipeline stays functional during transition

**Non-Goals:**
- Rewriting the scraper's crawl4ai or Gemini extraction logic (stays as-is)
- Building a scraper management UI or admin panel
- Implementing scraper auto-discovery / autonomous surfing (future work)
- Migrating from PostgreSQL or changing the DB schema
- Real-time event streaming (batch processing per crawl job is fine)

## Decisions

### 1. One Celery app, owned by the backend

The Celery application lives in `backend/api/celery_app.py`. The scraper imports and uses it only to publish tasks — it never defines workers or consumes tasks.

**Why over two Celery apps**: Avoids queue ownership confusion, task name collisions, and double config maintenance. The scraper is a producer, not a consumer.

**Why over Cloud Tasks / DB polling**: The scraper will evolve into an autonomous agent. Celery gives us a real event-driven boundary with retry logic, task chaining, and monitoring (Flower) — infrastructure that scales with the scraper's future complexity. DB polling would require the backend to know when to check, and Cloud Tasks would tie us to GCP.

### 2. Scraper writes to DB, signals via Celery (hybrid approach)

The scraper writes `ExtractedEvent` rows and `CrawlResult` status updates directly to the DB (keeps psycopg2 for these writes), then sends a lightweight Celery task `process_crawl_job(job_id)` to signal the backend.

**Why not send data through Celery**: ExtractedEvents can be large (hundreds of events per crawl). Serializing through Redis adds latency and memory pressure. The DB is already the shared state — use it as such. The Celery message is just a notification: "job X has data ready."

**Why scraper keeps DB writes for crawl data**: The scraper needs to track its own state (crawl_results status, crawl_contents). Moving these writes to the backend would create a circular dependency — the scraper would need to call the backend just to save its own crawl output.

### 3. Task granularity: per crawl job

One Celery task per crawl job, not per source or per event.

**Why**: Sources within a job share dedup context. Per-source would require distributed coordination to know when the full job is done. Per-event is too granular — dedup needs to see all events from a source together. The backend consumer iterates over sources within the job internally.

### 4. Processing logic converts from psycopg2 to SQLAlchemy async

`processor.py` and `merger.py` logic moves to backend as services. These currently use raw SQL via psycopg2. In the backend, they'll use SQLAlchemy async (matching the existing backend patterns).

**Why not keep psycopg2 in backend**: The backend already uses SQLAlchemy async + asyncpg. Adding psycopg2 would mean two DB connection pools, two transaction management patterns, and model drift. Converting to SQLAlchemy is more work upfront but eliminates dual-driver complexity.

**Alternative considered**: Wrapping existing psycopg2 functions in sync Celery tasks. Rejected because it creates a maintenance burden — two ORMs in the same codebase with no migration path.

### 5. Geocoder runs on a separate Celery queue

Geocoding tasks go to a `geocoding` queue, consumed by the same backend worker process but configurable to run on dedicated workers later.

**Why separate queue**: Geocoding calls an external API (Geoapify) with rate limits and latency. If it shared the default queue, a batch of geocoding tasks could block event processing. Separate queues allow independent concurrency control.

### 6. Scraper publishes tasks via a shared Celery config module

The scraper needs to send Celery tasks without importing the full backend. A lightweight shared config (broker URL, task names as constants) is enough. The scraper uses `celery.send_task()` to publish by name — no need to import the actual task functions.

**Why**: Keeps the scraper truly independent. It doesn't need FastAPI, SQLAlchemy, or any backend code. Just a Redis connection string and a task name.

## Risks / Trade-offs

**[Risk] psycopg2 → SQLAlchemy conversion may introduce bugs in dedup/merge logic** → Mitigation: Port logic function-by-function with integration tests. Run both paths in parallel during migration and compare results before cutting over.

**[Risk] Celery adds operational complexity (worker monitoring, Redis availability)** → Mitigation: Use Flower for monitoring. Redis on GCP Memorystore has 99.9% SLA. Celery task retries handle transient failures.

**[Risk] Shared DB between scraper and backend creates implicit coupling** → Mitigation: Scraper only writes to `crawl_jobs`, `crawl_results`, `crawl_contents`, and `extracted_events` tables. Backend only reads these and writes to `events`, `locations`, `tags`. Clear table ownership boundaries. Future: replace shared DB with API calls if needed.

**[Risk] Migration period where pipeline has mixed old/new paths** → Mitigation: Feature flag (`USE_CELERY=true/false`) in pipeline. Old path runs full pipeline. New path stops after extract and fires Celery task. Remove old path once backend consumer is verified.

**[Trade-off] Scraper still needs DB credentials** → Accepted. The scraper needs to write crawl results and extracted events. A pure message-based approach would require serializing large payloads through Redis. DB writes are pragmatic.

## Migration Plan

1. **Phase 1: Infrastructure** — Add Celery + Redis to backend. Create celery app, task definitions (stubs). Verify worker starts and processes test tasks.
2. **Phase 2: Geocoder worker** — Easiest migration. Move existing `backend/api/services/geocoding.py` into a Celery task. Update location creation endpoints to queue geocoding instead of inline calls.
3. **Phase 3: Event processing consumer** — Port `processor.py` logic to `backend/api/services/event_processing.py` using SQLAlchemy. Port `merger.py` to `backend/api/services/event_merging.py`. Create `process_crawl_job` Celery task that calls both services.
4. **Phase 4: Scraper isolation** — Trim `pipeline/main.py` to crawl + extract only. Remove processor/merger imports. Add Celery task publishing after extract phase. Remove processing/merge functions from `pipeline/db.py`.
5. **Phase 5: Cleanup** — Remove dead code from pipeline. Update pipeline's pyproject.toml (remove processing deps). Update deployment configs.

Rollback: At any phase, the pipeline's old path can be re-enabled via feature flag. No DB schema changes are needed, so rollback is code-only.

## Open Questions

- **Redis hosting**: GCP Memorystore (managed) vs. self-hosted Redis container? Memorystore is simpler but costs more. For current scale (~30 sources), a small container might suffice.
- **Celery worker deployment**: Same Cloud Run service as FastAPI (different entrypoint) or separate Cloud Run service? Same service is simpler; separate gives independent scaling.
- **Token tracking**: `TokenTracker` in extractor.py writes crawl_summaries via psycopg2. Should this stay with scraper or move to backend? Leaning: stays with scraper since it tracks extraction costs.
