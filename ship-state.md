# Ship State

## Requirements

### Goal
Port the event deduplication, merging, and archiving engine from `pipeline/merger.py` into the backend as a new async SQLAlchemy service at `backend/api/services/event_merging.py`. The service must replicate all 7 dedup strategies (location match, name similarity, date overlap, and false-positive guards for Men's/Women's events, episode numbers, and different showtimes), merge logic (consolidate URLs, keep shorter name and longer description, merge occurrences, create EventSource links), event creation (new Event + EventOccurrence + EventUrl + EventTag records via SQLAlchemy async), event archiving (archive events not seen by any source with a 14-day grace period for future occurrences), and audit logging to ExtractedEventLog for every processed event outcome.

### Constraints
- Python 3.14, SQLAlchemy async (AsyncSession), FastAPI/Pydantic conventions
- Follow existing backend service patterns in `backend/api/services/event_processing.py`
- Use `uv run` for all commands
- mypy strict mode must pass (`uv run mypy src/` — note: backend uses `uv run mypy` from within the backend directory)
- ruff lint + format must pass
- pytest must pass
- Max 250 lines per PR (stacked PRs required)
- Branch prefix: `ship/`
- Executor: `.claude/agents/backend-engineer.md`

### Acceptance Criteria
- 7-strategy dedup produces identical results to `pipeline/merger.py`
- False positive guards work: Men's vs Women's events, episode numbers, different showtimes
- Merge logic: URLs consolidated, shorter name kept, longer description kept
- `EventSource` links created for both new and merged events
- Archiving: events gone from all sources archived; 14-day grace for future occurrences
- All outcomes logged to `ExtractedEventLog`
- New event created; duplicate merged; archive triggers; audit logs written (tested)

### Source
- Type: github-issue
- Reference: #111

## Repo Context

### Tech Stack
- Language: Python
- Package manager: uv
- Framework: FastAPI + SQLAlchemy (async) + Pydantic
- Database: PostgreSQL (asyncpg)
- Task queue: Celery + Redis

### Validation Commands
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest`

### Project Structure
- `backend/` — FastAPI backend application root
- `backend/api/services/` — async service layer (event_processing.py already exists here)
- `backend/api/models/` — SQLAlchemy ORM models (event.py, crawl.py, location.py, tag.py, etc.)
- `backend/api/models/base.py` — shared enums (ExtractedEventStatus, EventStatus, etc.) and mixins
- `backend/api/tasks/` — Celery tasks
- `backend/tests/` — pytest test suite
- `pipeline/merger.py` — source of truth for dedup/merge/archive logic to be ported (33.4K)

### Relevant Files
- `pipeline/merger.py` — entire dedup/merge/archive logic to port; contains normalize_name_for_dedup, stem_word, get_significant_words, strip_common_prefixes, extract_core_title, is_false_positive, are_names_similar, _log_extracted_event, merge_extracted_events, archive logic
- `backend/api/services/event_processing.py` — existing async service to follow as pattern (resolve_location, process_tags, load_tag_rules)
- `backend/api/models/event.py` — Event, EventOccurrence, EventUrl, EventTag, EventSource ORM models
- `backend/api/models/crawl.py` — ExtractedEvent, ExtractedEventLog, CrawlJob ORM models
- `backend/api/models/base.py` — ExtractedEventStatus enum (created, merged, skipped_no_location, skipped_no_occurrences, skipped_duplicate, skipped_tag_removed), EventStatus enum
- `backend/api/models/location.py` — Location ORM model
- `backend/api/models/tag.py` — Tag ORM model
- `backend/pyproject.toml` — backend dependencies and tool config (mypy strict, ruff, pytest asyncio_mode=strict)
- `.ship.yaml` — ship pipeline configuration (maxLinesPerPR: 250, executor: .claude/agents/backend-engineer.md)
