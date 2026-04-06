## ADDED Requirements

### Requirement: Scraper scope is crawl and extract only
The scraper service SHALL only perform: web crawling (crawl4ai), AI extraction (Gemini), and basic text sanitization (HTML entities, whitespace normalization). It SHALL NOT perform location resolution, tag processing, deduplication, or event merging.

#### Scenario: Scraper completes a crawl job
- **WHEN** the scraper runs for a set of sources
- **THEN** it crawls each source, extracts events via Gemini AI, and writes `ExtractedEvent` rows to the database
- **THEN** it updates `CrawlResult` status to `extracted`
- **THEN** it does NOT write to the `events`, `locations`, or `tags` tables

#### Scenario: Scraper processes a JSON API source
- **WHEN** the scraper crawls a source with `crawl_mode=json_api`
- **THEN** it fetches structured JSON, extracts events, and writes `ExtractedEvent` rows
- **THEN** it does NOT resolve location names to location records (backend handles this)

### Requirement: Scraper signals backend via Celery
After completing extraction for a crawl job, the scraper SHALL publish a Celery task to notify the backend.

#### Scenario: Crawl job extraction completes
- **WHEN** all sources in a crawl job have been extracted (or failed)
- **THEN** the scraper publishes `process_crawl_job(job_id)` to the default Celery queue
- **THEN** the scraper uses `send_task()` (by name) — it does not import backend task functions

#### Scenario: Crawl job with all sources failed
- **WHEN** all sources in a crawl job fail during crawl or extraction
- **THEN** the scraper still publishes `process_crawl_job(job_id)` so the backend can update job status and log the failure

### Requirement: Scraper is independently deployable
The scraper SHALL have its own `pyproject.toml` with only its required dependencies (crawl4ai, google-genai, psycopg2-binary, celery, redis). It SHALL NOT depend on FastAPI, SQLAlchemy, or any backend module.

#### Scenario: Scraper builds without backend
- **WHEN** the scraper's dependencies are installed from its own `pyproject.toml`
- **THEN** it runs successfully without any backend code present
- **THEN** it only needs `REDIS_URL` and `DATABASE_URL` (or equivalent DB config) as environment variables

### Requirement: Scraper retains its DB connection pattern
The scraper SHALL continue using psycopg2 for writing crawl results, crawl contents, and extracted events. It writes to its own tables (`crawl_jobs`, `crawl_results`, `crawl_contents`, `extracted_events`) only.

#### Scenario: Scraper writes crawl data
- **WHEN** the scraper completes a crawl
- **THEN** it writes to `crawl_jobs`, `crawl_results`, and `crawl_contents` via psycopg2
- **THEN** it does NOT use SQLAlchemy or the backend's database module

#### Scenario: Scraper writes extracted events
- **WHEN** the scraper completes AI extraction
- **THEN** it writes `ExtractedEvent` rows to the `extracted_events` table via psycopg2
- **THEN** it includes: name, short_name (if generated), description, emoji, location_name (raw), sublocation, url, occurrences (JSONB), tags (JSONB)

### Requirement: Feature flag for migration
The scraper SHALL support a `USE_CELERY` environment variable that controls whether it fires Celery tasks after extraction.

#### Scenario: USE_CELERY is true
- **WHEN** `USE_CELERY=true` and extraction completes
- **THEN** the scraper publishes `process_crawl_job` via Celery and stops (does not run processor or merger)

#### Scenario: USE_CELERY is false or unset
- **WHEN** `USE_CELERY` is not set or is `false`
- **THEN** the scraper runs the full legacy pipeline (crawl → extract → process → merge) for backwards compatibility during migration
