# Ship Plan — Event Merging Service (Issue #111)

Port `pipeline/merger.py` (33.4K) into the backend as an async SQLAlchemy service at `backend/api/services/event_merging.py`, following the pattern established by `backend/api/services/event_processing.py`. Work is split into 8 stacked PRs, each under 250 lines, each a complete, passing, mypy-strict increment.

## Stack

1. `ship/111-01-name-normalization` — pure name normalization + stemming helpers
2. `ship/111-02-title-extraction` — prefix stripping + core title extraction
3. `ship/111-03-false-positive-guards` — `is_false_positive` + `are_names_similar`
4. `ship/111-04-occurrence-parsing` — JSONB occurrence/tag parsing + date filtering
5. `ship/111-05-dedup-index-loader` — async loader building location/coord/source indexes
6. `ship/111-06-match-and-log` — `find_best_match` + `log_extracted_event` audit helper
7. `ship/111-07-merge-and-create` — `merge_event` + `create_event` async DB writers
8. `ship/111-08-orchestrator-and-archive` — top-level `merge_extracted_events` + 14-day archive

All PRs use `backend-engineer.md`. No DevOps work involved.

---

## PR 1: Name normalization and stemming helpers

**Branch:** `ship/111-01-name-normalization`
**Executor:** `.claude/agents/backend-engineer.md`
**Status:** done

### Description
Create the foundation of the merging service: unicode-normalized name handling, semantic stemming, and significant-word extraction. Pure functions, no DB access, verbatim port of `pipeline/merger.py:17-87`.

### Files
- `backend/api/services/event_merging.py` [CREATE]: New module with:
  - Module docstring noting port from `pipeline/merger.py`
  - `STOP_WORDS: frozenset[str] = frozenset({"the", "and", "for", "with", "from", "into", "your"})`
  - `SEMANTIC_EQUIVALENTS: dict[str, str]` — dine/dinner/dining/diner + day abbreviations
  - `STEM_SUFFIXES: list[tuple[str, str]]` — (ency->enc, ence->enc, ing->"", tion->t, sion->s, ies->y, es->"", s->"")
  - `def normalize_name_for_dedup(name: str) -> str` — NFKD unicode, drop combining marks, drop underscores, replace punctuation with space, lowercase, collapse whitespace
  - `def stem_word(word: str) -> str` — apply semantic_equivalents first, else walk STEM_SUFFIXES with `len(word) > len(suffix) + 2` guard
  - `def _is_year(word: str) -> bool` — 4-digit `20XX`
  - `def get_significant_words(name: str, *, stem: bool = False) -> frozenset[str]` — returns frozenset of 3+ char words, minus STOP_WORDS and years, optionally stemmed
- `backend/tests/services/test_event_merging_normalization.py` [CREATE]: pytest module (not class-based, per project convention) with test functions:
  - `test_normalize_name_for_dedup_strips_accents` ("café" -> "cafe")
  - `test_normalize_name_for_dedup_replaces_punctuation_with_space` ("Alice/Bob" -> "alice bob")
  - `test_normalize_name_for_dedup_collapses_whitespace`
  - `test_stem_word_semantic_equivalents` (dinner -> dine, tues -> tuesday)
  - `test_stem_word_suffix_rules` (residency -> residenc, stories -> story)
  - `test_stem_word_short_word_unchanged` (cat stays cat)
  - `test_get_significant_words_drops_stop_words_and_years`
  - `test_get_significant_words_stemmed`

### Estimated lines
~130 (100 src + 30 test)

### Acceptance
- `normalize_name_for_dedup("Café Noël")` returns `"cafe noel"`
- `stem_word("dinner")` returns `"dine"`, `stem_word("residency")` returns `"residenc"`
- `get_significant_words("The 2025 Jazz Festival")` returns `frozenset({"jazz", "festival"})`
- Module imports cleanly; no SQLAlchemy imports yet.

### Validation
- `cd backend && uv run ruff check .`
- `cd backend && uv run ruff format --check .`
- `cd backend && uv run mypy api/services/event_merging.py`
- `cd backend && uv run pytest tests/services/test_event_merging_normalization.py -v`

---

## PR 2: Prefix stripping and core title extraction

**Branch:** `ship/111-02-title-extraction`
**Executor:** `.claude/agents/backend-engineer.md`
**Status:** done

### Description
Add the title-normalization layer on top of PR 1: strip bracketed/program prefixes and extract core titles by removing presenter prefixes and subtitles. Pure functions, port of `pipeline/merger.py:90-154`.

### Files
- `backend/api/services/event_merging.py` [MODIFY]: Append:
  - `KNOWN_PROGRAM_PREFIXES: tuple[str, ...] = ("FIDO",)`
  - `PRESENTER_PATTERNS: tuple[re.Pattern[str], ...]` — compiled patterns for `^.+?\s+presents?\s*:?\s*`, `^.+?\s+productions?\s*:?\s*`, `^hosted\s+by\s+.+?:\s*` (IGNORECASE)
  - `_BRACKETED_PREFIX_RE = re.compile(r"^\s*\[[^\]]+\]\s*")`
  - `def strip_common_prefixes(name: str) -> str` — strip bracketed prefix, then case-insensitive `^{prefix}\s+` for each in KNOWN_PROGRAM_PREFIXES
  - `def extract_core_title(name: str) -> str` — call strip_common_prefixes, apply PRESENTER_PATTERNS in order, then if ":" present and main_title >= 5 chars, keep part before colon
- `backend/tests/services/test_event_merging_titles.py` [CREATE]: Test functions:
  - `test_strip_common_prefixes_bracketed` ("[member-only] Sewing" -> "Sewing")
  - `test_strip_common_prefixes_fido` ("FIDO Coffee Bark" -> "Coffee Bark")
  - `test_strip_common_prefixes_nested` ("[FREE] Jazz" -> "Jazz")
  - `test_extract_core_title_presenter` ("Manhattan Theatre Club Presents The Monsters" -> "The Monsters")
  - `test_extract_core_title_subtitle` ("The Monsters: a Sibling Love Story" -> "The Monsters")
  - `test_extract_core_title_short_main_keeps_subtitle` ("ABC: Long Title Here" unchanged-ish)
  - `test_extract_core_title_hosted_by` ("Hosted by Jane: Talk" -> "Talk")

### Estimated lines
~100 (60 src + 40 test)

### Acceptance
- `strip_common_prefixes("[member-only] Sewing Machines")` returns `"Sewing Machines"`
- `extract_core_title("Lincoln Center Presents: Jazz at Midnight")` returns `"Jazz at Midnight"`
- Matches reference behavior from `pipeline/merger.py:122-154`.

### Validation
- `cd backend && uv run ruff check .`
- `cd backend && uv run ruff format --check .`
- `cd backend && uv run mypy api/services/event_merging.py`
- `cd backend && uv run pytest tests/services/test_event_merging_titles.py -v`

---

## PR 3: False-positive guards and name similarity

**Branch:** `ship/111-03-false-positive-guards`
**Executor:** `.claude/agents/backend-engineer.md`
**Status:** done

### Description
Add `is_false_positive` (Men's/Women's, episodes, showtimes, set/part/volume, vs-opponents) and `are_names_similar` (6-strategy matcher). Pure functions, port of `pipeline/merger.py:157-361`.

### Files
- `backend/api/services/event_merging.py` [MODIFY]: Append:
  - Precompiled patterns as module constants: `_TIME_END_RE`, `_NIGHT_RE`, `_EPISODE_RE`, `_NUMBERED_RE_BY_KEYWORD` (dict keyword -> compiled pattern for `\b{kw}\.?\s*(\d+)`), `_SEQ_RE`, `_VS_RE`, `_TIME_ANYWHERE_RE`
  - `NUMBERED_KEYWORDS: tuple[str, ...] = ("set", "part", "vol", "volume", "chapter", "session", "round")`
  - `def is_false_positive(name1: str, name2: str) -> bool` — return True for any guard mismatch; signature and semantics identical to source lines 157-244
  - `def are_names_similar(name1: str, name2: str) -> bool` — 6 strategies from source lines 247-361, including the subtitle-match exception for colon-separated series titles, Jaccard >= 0.7, asymmetric 0.75 containment on stemmed words
- `backend/tests/services/test_event_merging_similarity.py` [CREATE]: Test functions:
  - False-positive guards: `test_fp_mens_vs_womens`, `test_fp_different_episodes`, `test_fp_different_showtimes`, `test_fp_set_1_vs_set_2`, `test_fp_different_vs_opponents`, `test_fp_early_vs_late`
  - Similarity: `test_similar_exact_normalized`, `test_similar_after_prefix_strip`, `test_similar_substring`, `test_similar_presenter_prefix`, `test_similar_jaccard_70`, `test_similar_stemmed_residency_residence`, `test_not_similar_backstage_pass_different_subtitles`

### Estimated lines
~220 (140 src + 80 test)

### Acceptance
- `is_false_positive("Knicks Men's Game", "Knicks Women's Game")` returns True
- `are_names_similar("The Residency Program", "The Residence Program")` returns True via stemming
- `are_names_similar("Backstage Pass: Duran Duran", "Backstage Pass: Arctic Monkeys")` returns False
- All 13 test functions pass; parity with `pipeline/merger.py` behavior.

### Validation
- `cd backend && uv run ruff check .`
- `cd backend && uv run ruff format --check .`
- `cd backend && uv run mypy api/services/event_merging.py`
- `cd backend && uv run pytest tests/services/test_event_merging_similarity.py -v`

---

## PR 4: Occurrence and tag JSONB parsing

**Branch:** `ship/111-04-occurrence-parsing`
**Executor:** `.claude/agents/backend-engineer.md`
**Status:** done

### Description
Add pure helpers to parse and filter the JSONB `occurrences` and `tags` columns from `ExtractedEvent`, with 14-day future grace and 90-day look-ahead. Ports `pipeline/merger.py:364-375, 563-610`.

### Files
- `backend/api/services/event_merging.py` [MODIFY]: Append:
  - `from datetime import date, datetime, timedelta`
  - `FUTURE_LIMIT_DAYS: int = 90`
  - `ARCHIVE_GRACE_DAYS: int = 14`
  - `@dataclass(frozen=True) class ParsedOccurrence: start_date: date; start_time: str | None; end_date: date | None; end_time: str | None`
  - `def _parse_jsonb(value: object) -> list[Any] | dict[str, Any] | None` — accept None, list/dict, or str (json.loads)
  - `def parse_occurrences(raw: object, *, today: date) -> list[ParsedOccurrence]` — filter to today <= start_date <= today+90d, parse start_time/end_time/end_date strings safely
  - `def parse_tags(raw: object) -> list[str]` — coerce jsonb, drop non-str, strip
- `backend/tests/services/test_event_merging_parsing.py` [CREATE]: Tests for:
  - `test_parse_jsonb_passthrough_dict`, `test_parse_jsonb_string`, `test_parse_jsonb_none`, `test_parse_jsonb_invalid`
  - `test_parse_occurrences_filters_past`, `test_parse_occurrences_filters_far_future`, `test_parse_occurrences_keeps_end_date`, `test_parse_occurrences_handles_bad_format`
  - `test_parse_tags_list`, `test_parse_tags_drops_non_string`

### Estimated lines
~150 (80 src + 70 test)

### Acceptance
- `parse_occurrences([{"start_date": "2099-01-01"}], today=date(2026,4,10))` returns `[]` (too far future)
- `parse_occurrences([{"start_date": "2020-01-01"}], today=date(2026,4,10))` returns `[]` (past)
- `parse_tags(["Music", "", None, 42, "Art"])` returns `["Music", "Art"]`

### Validation
- `cd backend && uv run ruff check .`
- `cd backend && uv run ruff format --check .`
- `cd backend && uv run mypy api/services/event_merging.py`
- `cd backend && uv run pytest tests/services/test_event_merging_parsing.py -v`

---

## PR 5: Async dedup-index loader

**Branch:** `ship/111-05-dedup-index-loader`
**Executor:** `.claude/agents/backend-engineer.md`
**Status:** done

### Description
First DB-touching PR. Introduce the `DedupIndex` dataclass and an async loader that builds the three lookup indexes (by location_id, by coords, by source_id) plus the per-event future-date set. Ports `pipeline/merger.py:437-520`.

### Files
- `backend/api/services/event_merging.py` [MODIFY]: Append:
  - `from sqlalchemy import select`
  - `from sqlalchemy.ext.asyncio import AsyncSession`
  - `from api.models.event import Event, EventOccurrence, EventSource`
  - `from api.models.base import EventStatus`
  - `@dataclass class EventCandidate: id: int; name: str`
  - `@dataclass class DedupIndex:`
    - `by_location_id: dict[int, list[EventCandidate]]`
    - `by_coords: dict[tuple[float, float], list[EventCandidate]]`
    - `by_source_id: dict[int, list[EventCandidate]]`
    - `dates_by_event_id: dict[int, set[str]]`
    - `def add(self, candidate: EventCandidate, *, location_id: int | None, lat: float | None, lng: float | None, source_id: int | None, dates: set[str]) -> None`
  - `async def load_dedup_index(db: AsyncSession, *, today: date) -> DedupIndex` — query active, non-deleted events with occurrences within `[today-10d, today+90d]`, left-join locations for lat/lng, then a second query for `EventSource.source_id`, then a third for `EventOccurrence.start_date` within the window; populate all four maps. Round coords to 5 decimals via `(round(float(lat), 5), round(float(lng), 5))`.
- `backend/tests/services/test_event_merging_index.py` [CREATE]: Async tests (pytest-asyncio) with in-memory/Postgres fixture (follow existing conventions in `backend/tests/services/test_event_processing.py`):
  - `test_load_dedup_index_empty`
  - `test_load_dedup_index_groups_by_location_id`
  - `test_load_dedup_index_groups_by_coords`
  - `test_load_dedup_index_groups_by_source_id`
  - `test_load_dedup_index_excludes_archived`
  - `test_load_dedup_index_excludes_events_with_only_past_occurrences`

### Estimated lines
~230 (110 src + 120 test)

### Acceptance
- Returns empty `DedupIndex` for an empty DB.
- Event with `location_id=5, source_id=2, lat=40.7, lng=-74.0` appears in all three indexes.
- Archived events and events with only past occurrences are excluded.

### Validation
- `cd backend && uv run ruff check .`
- `cd backend && uv run ruff format --check .`
- `cd backend && uv run mypy api/services/event_merging.py`
- `cd backend && uv run pytest tests/services/test_event_merging_index.py -v`

---

## PR 6: Match selection and audit logging

**Branch:** `ship/111-06-match-and-log`
**Executor:** `.claude/agents/backend-engineer.md`
**Status:** done

### Description
Add the best-match selection logic (location -> coords -> source fallback) and the async `log_extracted_event` helper that writes `ExtractedEventLog` rows. Ports `pipeline/merger.py:378-384, 617-652`.

### Files
- `backend/api/services/event_merging.py` [MODIFY]: Append:
  - `from api.models.crawl import ExtractedEventLog`
  - `from api.models.base import ExtractedEventStatus`
  - `def find_best_match(name: str, extracted_dates: set[str], candidates: list[EventCandidate], dates_by_event_id: dict[int, set[str]]) -> int | None` — iterate candidates, require date overlap, use `are_names_similar`, prefer exact normalized-name match, else first partial match (parity with `pipeline/merger.py:621-632`)
  - `def select_matched_event_id(*, name: str, extracted_dates: set[str], location_id: int | None, lat: float | None, lng: float | None, source_id: int, index: DedupIndex) -> int | None` — try location_id index, then coords index, then source_id fallback
  - `async def log_extracted_event(db: AsyncSession, *, extracted_event_id: int, status: ExtractedEventStatus, event_id: int | None = None, message: str | None = None) -> None` — `db.add(ExtractedEventLog(...))`; no commit (caller owns transaction)
- `backend/tests/services/test_event_merging_match.py` [CREATE]: Tests:
  - `test_find_best_match_prefers_exact_normalized`
  - `test_find_best_match_requires_date_overlap`
  - `test_find_best_match_returns_none_when_no_candidates`
  - `test_select_matched_event_id_location_first`
  - `test_select_matched_event_id_falls_back_to_coords`
  - `test_select_matched_event_id_falls_back_to_source`
  - `test_log_extracted_event_writes_row` (async with DB fixture)

### Estimated lines
~200 (90 src + 110 test)

### Acceptance
- Given two candidates with overlapping dates and similar names, the one with exact normalized-name match is returned.
- `select_matched_event_id` checks in order: location_id, coords, source_id.
- `log_extracted_event` inserts a row with correct `status` and `event_id`.

### Validation
- `cd backend && uv run ruff check .`
- `cd backend && uv run ruff format --check .`
- `cd backend && uv run mypy api/services/event_merging.py`
- `cd backend && uv run pytest tests/services/test_event_merging_match.py -v`

---

## PR 7: Merge and create async writers

**Branch:** `ship/111-07-merge-and-create`
**Executor:** `.claude/agents/backend-engineer.md`
**Status:** in-progress

### Description
Add the two async mutating operations: `merge_into_existing_event` (un-archive, add URL de-duped, set missing location_id, create EventSource link) and `create_new_event` (Event + EventOccurrence + EventUrl + EventTag + EventSource primary). Ports `pipeline/merger.py:654-802`.

### Files
- `backend/api/services/event_merging.py` [MODIFY]: Append:
  - `from api.models.event import Event, EventOccurrence, EventUrl, EventTag, EventSource`
  - `from api.models.tag import Tag`
  - `@dataclass class ExtractedEventInput:` — ee_id, name, short_name, description, emoji, sublocation, location_id, url, source_id, lat, lng, occurrences: list[ParsedOccurrence], tags: list[str]
  - `async def merge_into_existing_event(db: AsyncSession, *, event_id: int, extracted: ExtractedEventInput) -> None`:
    - Un-archive if status == archived (update via `select` then mutate)
    - If `extracted.url`: check existing EventUrl for (event_id, url[:2000]); insert if absent
    - If event has no location_id and `extracted.location_id` is set: update
    - Insert EventSource with `is_primary=False`
  - `async def create_new_event(db: AsyncSession, *, extracted: ExtractedEventInput) -> int`:
    - Build Event (name[:500], short_name[:255], description, emoji[:10], location_id, sublocation[:255])
    - `db.add(event); await db.flush()` to get id
    - Add EventOccurrence rows (one per parsed occurrence)
    - Add EventUrl if url present (truncate 2000)
    - For each tag: select Tag by name; if missing insert; link via EventTag (ON CONFLICT DO NOTHING equivalent: catch IntegrityError or check first)
    - Insert EventSource with `is_primary=True`
    - Return new event id
    - No `commit` — caller owns transaction
- `backend/tests/services/test_event_merging_writers.py` [CREATE]: Async tests:
  - `test_create_new_event_inserts_all_rows`
  - `test_create_new_event_creates_missing_tags`
  - `test_create_new_event_reuses_existing_tags`
  - `test_merge_into_existing_event_adds_url`
  - `test_merge_into_existing_event_skips_duplicate_url`
  - `test_merge_into_existing_event_unarchives`
  - `test_merge_into_existing_event_links_source`

### Estimated lines
~240 (130 src + 110 test)

### Acceptance
- `create_new_event` inserts Event + occurrences + url + tags + primary EventSource in one flush.
- `merge_into_existing_event` is idempotent for duplicate URLs.
- Archived event is flipped to active when merged.
- Both functions return cleanly without committing.

### Validation
- `cd backend && uv run ruff check .`
- `cd backend && uv run ruff format --check .`
- `cd backend && uv run mypy api/services/event_merging.py`
- `cd backend && uv run pytest tests/services/test_event_merging_writers.py -v`

---

## PR 8: Top-level orchestrator and 14-day archiving

**Branch:** `ship/111-08-orchestrator-and-archive`
**Executor:** `.claude/agents/backend-engineer.md`
**Status:** pending

### Description
Final PR: wire all previous pieces into the public `merge_extracted_events` async orchestrator, plus port the archiving logic (events no longer seen from any source, with 14-day future-occurrence grace period). Ports `pipeline/merger.py:387-431, 525-562, 808-868`.

### Files
- `backend/api/services/event_merging.py` [MODIFY]: Append:
  - `@dataclass class MergeResult: new_events_count: int; merged_count: int; archived_count: int`
  - `async def archive_outdated_events(db: AsyncSession, *, source_id: int, today: date) -> tuple[int, list[tuple[int, str, date]]]`:
    - For each active event linked to `source_id`, check that ALL linked sources stopped listing it in their latest crawl
    - Apply 14-day grace: skip archiving if event has any occurrence with `start_date >= today + 14 days` (upcoming flag)
    - Archive (status=archived) events with no future grace; collect (event_id, name, next_occurrence) for those that WERE archived despite having upcoming occurrences (warning list)
    - Return (archived_count, upcoming_warnings)
  - `async def merge_extracted_events(db: AsyncSession, *, crawl_job_id: int | None = None, today: date | None = None) -> MergeResult`:
    - `today = today or date.today()`
    - Load unprocessed `ExtractedEvent`s (JOIN CrawlResult where status='processed' and no EventSource)
    - Call `load_dedup_index(db, today=today)`
    - For each extracted event, enforce invariants (source_id not None -> raise RuntimeError), skip with `skipped_no_location` / `skipped_no_occurrences` via `log_extracted_event`
    - Build `ExtractedEventInput`, call `select_matched_event_id` -> if match: `merge_into_existing_event` + log `merged`; else: `create_new_event` + log `created`; update in-memory index so within-batch dedup works
    - After processing, determine sources whose latest crawl was touched; call `archive_outdated_events` per source
    - `await db.commit()` at end (or rely on caller — match pattern in `event_processing.py`)
    - Return `MergeResult`
- `backend/tests/services/test_event_merging_orchestrator.py` [CREATE]: End-to-end async tests:
  - `test_merge_creates_new_event_and_logs_created`
  - `test_merge_merges_duplicate_and_logs_merged`
  - `test_merge_skips_missing_location`
  - `test_merge_skips_no_valid_occurrences`
  - `test_merge_raises_on_missing_source_id`
  - `test_merge_within_batch_dedup`
  - `test_merge_archives_event_not_seen_in_latest_crawl`
  - `test_merge_grace_period_preserves_future_event`

### Estimated lines
~240 (130 src + 110 test)

### Acceptance
- New event path: `Event` + `EventOccurrence` + `EventUrl` + `EventSource` + `ExtractedEventLog(status=created)` written.
- Merge path: existing event gets new URL + `EventSource(is_primary=False)` + `ExtractedEventLog(status=merged)`.
- Archive path: event whose only source no longer lists it in the latest crawl is archived, unless it has an occurrence >= today + 14 days.
- All 8 acceptance criteria from `ship-state.md` pass.
- `uv run mypy` strict passes over the full service file.

### Validation
- `cd backend && uv run ruff check .`
- `cd backend && uv run ruff format --check .`
- `cd backend && uv run mypy .`
- `cd backend && uv run pytest tests/services/test_event_merging_orchestrator.py tests/services/test_event_merging_*.py -v`
