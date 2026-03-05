---
phase: 04-json-api-crawling
plan: 01
subsystem: pipeline
tags: [crawling, json-api, jsonp, httpx, alternativa-teatral]
dependency-graph:
  requires: [03-01]
  provides: [json-api-crawl-path, alternativa-teatral-config]
  affects: []
tech-stack:
  added: [httpx]
  patterns: [crawl-mode-routing, jsonp-unwrapping, json-to-markdown]
key-files:
  created: []
  modified:
    - database/schema.sql
    - database/seeds/websites_ba.sql
    - pipeline/db.py
    - pipeline/crawler.py
    - pipeline/main.py
decisions:
  - id: 04-01-a
    decision: "httpx for async HTTP in crawler.py (lightweight, async-native, no browser overhead)"
  - id: 04-01-b
    decision: "Events with no dates pass through filter (let Gemini decide relevance)"
  - id: 04-01-c
    decision: "JSON API websites skip HAVING urls IS NOT NULL since API URL is in json_api_config"
metrics:
  duration: 7min
  completed: 2026-03-05
---

# Phase 04 Plan 01: JSON API Crawl Path Summary

**One-liner:** HTTP GET crawl path with JSONP unwrapping, date filtering, and markdown flattening for Alternativa Teatral's JSON endpoint

## What Was Done

### Task 1: Schema + DB Layer
- Added `crawl_mode ENUM('browser','json_api')` and `json_api_config JSON` columns to `websites` table in schema.sql
- Updated both SELECT queries in `db.get_websites_due_for_crawling()` to include new columns (indices 21, 22) and shifted urls to index 23
- Updated HAVING clauses to allow json_api websites without website_urls rows (`HAVING urls IS NOT NULL OR w.crawl_mode = 'json_api'`)
- Added UPDATE statement in seeds to configure Alternativa Teatral with jsonp_callback, data_path, fields_include, date_window_days, and base_url

### Task 2: JSON API Crawl Functions
- `strip_jsonp()` -- Unwraps JSONP callback by exact name or generic regex, returns unchanged if already plain JSON
- `filter_by_date_window()` -- Traverses `event > lugares > * > funciones > * > proxima_fecha`, keeps events with at least one date in window or no dates at all
- `flatten_events_to_markdown()` -- Converts event dicts to markdown with title, tags, venues, addresses, showtimes, URLs, ticket links
- `crawl_json_api()` -- Async function: HTTP GET via httpx, JSONP strip, JSON parse, data_path navigation, date filter, markdown flatten, store via `db.update_crawl_result_crawled()`

### Task 3: Pipeline Routing
- Split websites into `json_api_websites` and `browser_websites` after fetching
- JSON API websites crawled first in a simple loop (fast, no browser instance needed)
- Browser batching loop uses only `browser_websites`
- Both paths append to same `crawl_results` list -- downstream extraction, processing, merge, export, upload unchanged

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | c105167 | Schema + DB layer: crawl_mode, json_api_config columns and seed config |
| 2 | b09b4e9 | JSON API crawl functions in crawler.py |
| 3 | 13be2f8 | Pipeline routing: json_api vs browser split in main.py |

## Deviations from Plan

None -- plan executed exactly as written.

## Key Integration Points

- `crawler.crawl_json_api()` stores markdown via `db.update_crawl_result_crawled()` -- same function as browser path
- `main.py` appends json_api results to same `crawl_results` list -- Gemini extraction sees identical markdown input
- No changes to extraction, processing, merge, export, or upload steps

## Next Phase Readiness

- JSON API crawl path is ready for production use with Alternativa Teatral
- Additional JSON API sources can be added by setting `crawl_mode='json_api'` and providing `json_api_config` on any website row
- The `fields_include` parameter in config is prepared but not yet filtering (optimization for future sources with different field sets)
