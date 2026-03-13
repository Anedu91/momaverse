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

### Step 1: Move pipeline files into `backend/pipeline/`

**What to do:**
- Copy these files from `../pipeline/` into `backend/pipeline/`:
  - `main.py`, `db.py`, `crawler.py`, `extractor.py`, `processor.py`
  - `merger.py`, `frequency_analyzer.py`, `location_resolver.py`
- Copy test files: `../pipeline/tests/test_merger.py`, `../pipeline/tests/test_processor.py`
  into `backend/pipeline/tests/`
- Do NOT copy: `venv/`, `__pycache__/`, `exporter.py`, `uploader.py`
- Create `backend/pipeline/__init__.py`, `backend/pipeline/tests/__init__.py`
- Update imports in all moved files (e.g., `from pipeline import db`)
- **Make top-level imports lazy** for `db`, `regex`, `crawl4ai` in modules that have
  pure-logic functions used by tests (`merger.py`, `processor.py`)
- Add `regex` to dev dependencies: `uv add --group dev regex`

**Verify:**
- `cd backend && uv run python -c "import pipeline"` works
- `cd backend && uv run pytest pipeline/tests/ -v` — existing pure-logic tests pass
- `cd backend && uv run pytest tests/ -v` — existing backend tests still pass

---

### Step 2: Remove exporter and uploader references

**What to do:**
- Remove import/usage of `exporter` and `uploader` from `backend/pipeline/main.py`
- Remove Steps 6 (Export) and 7 (Upload) from the pipeline orchestrator
- Do NOT delete `../pipeline/exporter.py` or `../pipeline/uploader.py` yet (Step 9)

**Verify:**
- `cd backend && uv run pytest -v` passes

---

### Step 3: Decouple crawler.py and extractor.py from DB

**What to do:**

`crawler.py`:
- Remove `import db` / `from pipeline import db`
- Add `CrawlError` exception class
- `crawl_website()`: return `(content, filename)` instead of persisting to DB
- `crawl_json_api()`: return `(content, raw_data, filename)` instead of persisting to DB

`extractor.py`:
- Remove `import db` / `from pipeline import db`
- Add `ExtractionError` exception class
- `extract_events()`: accept `page_content` as parameter, return JSON string
- Accept `existing_events` as parameter instead of querying DB

**Verify:**
- `grep -r "import db" backend/pipeline/crawler.py backend/pipeline/extractor.py` returns nothing
- `cd backend && uv run pytest -v` passes

---

### Step 4: Add pipeline dependencies to pyproject.toml

**What to do:**
- Add a `pipeline` dependency group in `pyproject.toml`:
  ```toml
  pipeline = [
      "crawl4ai>=0.8.0",
      "google-genai>=1.65.0",
      "python-dotenv>=1.2.2",
      "httpx>=0.28.1",
      "Pillow>=12.1.1",
      "regex>=2026.2.28",
      "psycopg2-binary>=2.9.10",
  ]
  ```
- Add under the existing `[dependency-groups]` section (don't create a duplicate header)

**Verify:**
- `cd backend && uv sync` succeeds
- `cd backend && uv run pytest -v` passes

---

### Step 5: Create pipeline database session factory

**What to do:**
- Create `backend/pipeline/database.py`:
  - Own async engine from env vars (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`)
  - `get_pipeline_session()` async context manager that **commits on success, rolls back on error**
  - `dispose_engine()` for shutdown
  - Reuses `api.models` but NOT `api.database` engine

**Verify:**
- `cd backend && uv run python -c "from pipeline.database import get_pipeline_session"` works

---

### Step 6: Create pipeline services (SQLAlchemy DB operations)

**What to do:**
- Create `backend/pipeline/services/__init__.py`

- Create `backend/pipeline/services/crawl.py`:
  - `get_or_create_crawl_run(session, run_date) -> int`
  - `create_crawl_result(session, crawl_run_id, website_id, filename) -> int`
    (use ORM, NOT raw SQL `ON CONFLICT` — breaks SQLite tests)
  - `update_crawl_result_status(session, crawl_result_id, status, **kwargs)`
  - `update_crawl_result_crawled/extracted/processed/failed()`
  - `complete_crawl_run(session, crawl_run_id)`
  - `get_crawled_content(session, crawl_result_id) -> str | None`
  - `get_extracted_content(session, crawl_result_id) -> tuple`
  - `update_website_last_crawled(session, website_id)`
  - `get_websites_due_for_crawling(session, website_ids=None) -> list[dict]`
  - `get_existing_upcoming_events(session, website_id) -> list[dict]`
  - `get_incomplete_crawl_results(session) -> list[dict]`
  - **No `session.commit()` calls** — only `flush()`

- Create `backend/pipeline/services/process.py`:
  - `get_all_locations(session) -> list[dict]`
  - `get_tag_rules(session) -> dict`
  - `get_websites_with_tags(session) -> dict`
  - `save_crawl_events(session, crawl_result_id, events_data) -> int`
    (serialize `raw_data` with `json.dumps(data, default=str)` before storing)
  - **No `session.commit()` calls** — only `flush()`

- Create `backend/pipeline/services/merge.py`:
  - `merge_crawl_events(session, crawl_run_id=None) -> tuple[int, int]`
  - Import pure-logic functions from `pipeline.merger`
  - **No `session.commit()` calls** — only `flush()`

- Create `backend/pipeline/services/archive.py`:
  - `archive_outdated_events(session, website_id) -> tuple[int, list]`
  - `run_archival_for_crawl_events(session, crawl_event_ids) -> tuple[int, int]`
  - **No `session.commit()` calls** — only `flush()`

**Verify:**
- `cd backend && uv run python -c "from pipeline.services import crawl, process, merge, archive"` works

---

### Step 7: Add tests for pipeline services

**What to do:**
- Create `backend/tests/test_pipeline_crawl_service.py`
- Create `backend/tests/test_pipeline_process_service.py`
- Reuse existing `conftest.py` fixtures (`db_session`, `async_engine`)
- Tests use the transactional session (begin + rollback) — services use `flush()` not `commit()`

**Verify:**
- `cd backend && uv run pytest tests/ -v` — all tests pass (old + new)

---

### Step 8: Create pipeline runner (new orchestrator)

**What to do:**
- Create `backend/pipeline/runner.py` replacing `main.py` as entry point
- Uses `get_pipeline_session()` for all DB operations (which commits on exit)
- Calls isolated `crawler.py` / `extractor.py` for crawl/extract
- Calls `services/` for all DB operations
- Maintains async worker pool pattern (6 concurrent workers)
- CLI: `cd backend && uv run python -m pipeline.runner [--ids N] [--limit N]`
- `processor.py`, `frequency_analyzer.py`, `location_resolver.py` still use psycopg2 (marked TODO)

**Verify:**
- `cd backend && uv run python -m pipeline.runner --help` works
- `cd backend && uv run pytest -v` passes

---

### Step 9: Remove old pipeline directory

**What to do:**
- Delete entire `../pipeline/` directory (except `venv/` which should be gitignored)
- Verify no remaining references

**Verify:**
- `cd backend && uv run pytest -v` passes
- `grep -r "psycopg2" backend/pipeline/crawler.py backend/pipeline/extractor.py` returns nothing

---

## Files Summary

| New File | Purpose |
|----------|---------|
| `backend/pipeline/__init__.py` | Package marker |
| `backend/pipeline/database.py` | Pipeline session factory |
| `backend/pipeline/runner.py` | New orchestrator |
| `backend/pipeline/services/__init__.py` | Services package |
| `backend/pipeline/services/crawl.py` | Crawl run/result CRUD |
| `backend/pipeline/services/process.py` | Location/tag/event processing |
| `backend/pipeline/services/merge.py` | Event deduplication |
| `backend/pipeline/services/archive.py` | Event archival |

| Moved File | Changes |
|------------|---------|
| `backend/pipeline/crawler.py` | Decoupled from DB |
| `backend/pipeline/extractor.py` | Decoupled from DB |
| `backend/pipeline/processor.py` | Lazy imports for `db`, `regex`, `crawler` |
| `backend/pipeline/merger.py` | Lazy imports for `db`, `EditLogger` |
| `backend/pipeline/db.py` | Moved as-is (legacy, used by processor/merger TODO) |
| `backend/pipeline/main.py` | Removed exporter/uploader steps |
| `backend/pipeline/frequency_analyzer.py` | Moved as-is |
| `backend/pipeline/location_resolver.py` | Moved as-is |
