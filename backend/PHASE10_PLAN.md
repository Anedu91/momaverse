# Phase 10: Migrate Pipeline DB Layer to SQLAlchemy

**Issue**: [#31](https://github.com/Anedu91/momaverse/issues/31)
**Branch**: `pipeline_to_backend`

## Context

The pipeline (in `../pipeline/`) uses raw `psycopg2` while the backend uses async SQLAlchemy.
This creates duplicate schema definitions and no shared test infrastructure.
PR #47 already removed the need for JSON export + FTP upload.

**Architecture constraint**: `crawler.py` and `extractor.py` must remain isolated
(no DB/SQLAlchemy imports) to prepare for a future standalone scraper service.

---

## Lessons Learned (from previous attempt)

These are problems we hit before and must avoid this time:

1. **Service functions must NOT call `session.commit()`** — use `flush()` only.
   The caller (runner or test fixture) manages the transaction boundary.
   The pipeline session factory (`get_pipeline_session`) should commit on successful exit.

2. **Raw SQL with PostgreSQL syntax (`ON CONFLICT`, `NOW()`, `STRING_AGG`) breaks SQLite tests.**
   Use ORM queries wherever possible. For complex queries that need raw SQL, they won't be
   testable with SQLite — accept that or provide ORM alternatives.

3. **`raw_data` JSONB columns can't store `datetime.date` objects** — serialize with
   `json.loads(json.dumps(data, default=str))` before assigning.

4. **Top-level imports of `psycopg2`, `regex`, `crawl4ai` in pipeline modules block test collection.**
   Any module imported during test collection must use lazy imports for heavy/optional deps.
   Affected: `merger.py` (imports `db`), `processor.py` (imports `db`, `regex`, `crawler`).

5. **Don't do too many steps in one run.** One step at a time, verify tests pass, commit.

---

## Steps

### Step 1: Move pipeline files into `backend/pipeline/` --- DONE

- Copied files from `../pipeline/` into `backend/pipeline/`:
  `main.py`, `db.py`, `crawler.py`, `extractor.py`, `processor.py`,
  `merger.py`, `frequency_analyzer.py`, `location_resolver.py`
- Created `backend/pipeline/__init__.py`
- Updated imports, made top-level imports lazy for `db`, `regex`, `crawl4ai`

---

### Step 2: Remove exporter and uploader references --- DONE

- Removed import/usage of `exporter` and `uploader` from `backend/pipeline/main.py`
- Removed Steps 6 (Export) and 7 (Upload) from the pipeline orchestrator

---

### Step 3: Decouple crawler.py and extractor.py from DB --- DONE

- `crawler.py`: removed DB imports, added `CrawlError`, returns data instead of persisting
- `extractor.py`: removed DB imports, added `ExtractionError`, accepts params instead of querying DB

---

### Step 4: Add pipeline dependencies to pyproject.toml --- DONE

- Added `pipeline` dependency group in `pyproject.toml`

---

### Step 5: Create pipeline SQLAlchemy service modules --- DONE (partial)

**What was done:**
- Created `backend/pipeline/crawl_service.py` (crawl run/result CRUD)
- Created `backend/pipeline/process_service.py` (location/tag/event processing)
- Created `backend/tests/services/test_pipeline_crawl.py`
- Created `backend/tests/services/test_pipeline_process.py`
- All use `flush()` only, no `session.commit()`
- All 232 tests pass

**Still needed:**
- `backend/pipeline/merge_service.py`:
  - `merge_crawl_events(session, crawl_run_id=None) -> tuple[int, int]`
  - Import pure-logic functions from `pipeline.merger`
  - **No `session.commit()` calls** — only `flush()`
- `backend/pipeline/archive_service.py`:
  - `archive_outdated_events(session, website_id) -> tuple[int, list]`
  - `run_archival_for_crawl_events(session, crawl_event_ids) -> tuple[int, int]`
  - **No `session.commit()` calls** — only `flush()`
- `save_crawl_events()` in `process_service.py`:
  - `save_crawl_events(session, crawl_result_id, events_data) -> int`
  - Serialize `raw_data` with `json.dumps(data, default=str)` before storing
- `get_websites_due_for_crawling()` in `crawl_service.py`:
  - `get_websites_due_for_crawling(session, website_ids=None) -> list[dict]`
- `get_existing_upcoming_events()` in `crawl_service.py`:
  - `get_existing_upcoming_events(session, website_id) -> list[dict]`
- Tests for merge and archive services

---

### Step 6: Create pipeline database session factory

**What to do:**
- Create `backend/pipeline/database.py`:
  - Own async engine from env vars (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`)
  - `get_pipeline_session()` async context manager that **commits on success, rolls back on error**
  - `dispose_engine()` for shutdown
  - Reuses `api.models` but NOT `api.database` engine

**Verify:**
- `cd backend && uv run python -c "from pipeline.database import get_pipeline_session"` works

---

### Step 7: Create pipeline runner (new orchestrator)

**What to do:**
- Create `backend/pipeline/runner.py` replacing `main.py` as entry point
- Uses `get_pipeline_session()` for all DB operations (which commits on exit)
- Calls isolated `crawler.py` / `extractor.py` for crawl/extract
- Calls `crawl_service.py`, `process_service.py`, etc. for all DB operations
- Maintains async worker pool pattern (6 concurrent workers)
- CLI: `cd backend && uv run python -m pipeline.runner [--ids N] [--limit N]`
- `processor.py`, `frequency_analyzer.py`, `location_resolver.py` still use psycopg2 (marked TODO)

**Verify:**
- `cd backend && uv run python -m pipeline.runner --help` works
- `cd backend && uv run pytest -v` passes

---

### Step 8: Remove old pipeline directory

**What to do:**
- Delete entire `../pipeline/` directory (except `venv/` which should be gitignored)
- Verify no remaining references

**Verify:**
- `cd backend && uv run pytest -v` passes
- `grep -r "psycopg2" backend/pipeline/crawler.py backend/pipeline/extractor.py` returns nothing

---

## Files Summary

| File | Purpose | Status |
|------|---------|--------|
| `pipeline/__init__.py` | Package marker | Done |
| `pipeline/crawl_service.py` | Crawl run/result CRUD (SQLAlchemy) | Done |
| `pipeline/process_service.py` | Location/tag/event processing (SQLAlchemy) | Done (missing `save_crawl_events`) |
| `pipeline/merge_service.py` | Event deduplication (SQLAlchemy) | TODO |
| `pipeline/archive_service.py` | Event archival (SQLAlchemy) | TODO |
| `pipeline/database.py` | Pipeline session factory | TODO |
| `pipeline/runner.py` | New orchestrator | TODO |
| `pipeline/crawler.py` | Decoupled from DB | Done |
| `pipeline/extractor.py` | Decoupled from DB | Done |
| `pipeline/processor.py` | Lazy imports for `db`, `regex`, `crawler` | Done |
| `pipeline/merger.py` | Lazy imports for `db`, `EditLogger` | Done |
| `pipeline/db.py` | Legacy (used by processor/merger TODO) | Moved as-is |
| `pipeline/main.py` | Removed exporter/uploader steps | Done |
| `pipeline/frequency_analyzer.py` | Moved as-is | Done |
| `pipeline/location_resolver.py` | Moved as-is | Done |
