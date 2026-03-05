# Roadmap: Momaverse Buenos Aires

## Overview

Swap the existing NYC interactive event map to Buenos Aires in three phases: repoint the map and clear NYC data, populate BA location data, then wire up the pipeline and tags so real Argentine events flow through. Phase 4 adds lightweight JSON API crawling to bypass the browser for sources with structured endpoints. The existing UI, search, filtering, and rendering remain untouched.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Map Swap & NYC Cleanup** - Repoint the map to Buenos Aires and remove all NYC-specific data
- [x] **Phase 2: Buenos Aires Locations** - Populate venue/gallery/space data with correct geocoding
- [x] **Phase 3: Pipeline & Tags** - Configure crawlers for BA sources, adapt extraction for Spanish, define BA tag taxonomy
- [ ] **Phase 4: JSON API Crawling** - Add lightweight HTTP-based crawling for sites with JSON/JSONP endpoints, starting with Alternativa Teatral

## Phase Details

### Phase 1: Map Swap & NYC Cleanup
**Goal**: The map shows Buenos Aires, not New York -- with correct center, bounds, barrio labels, and no leftover NYC data
**Depends on**: Nothing (first phase)
**Requirements**: MAP-01, MAP-02, MAP-03, PIPE-04
**Plans:** 2 plans
**Success Criteria** (what must be TRUE):
  1. Opening the app shows a map centered on Buenos Aires with the city clearly visible at default zoom
  2. Panning and zooming are constrained to the Buenos Aires metro area -- user cannot scroll to NYC or beyond reasonable BA bounds
  3. Barrio names (Palermo, San Telmo, La Boca, Recoleta, etc.) are visible as labels on the map at appropriate zoom levels
  4. No NYC events, locations, or references remain in the dataset or display

Plans:
- [x] 01-01-PLAN.md -- Map configuration, bounds, maxBounds, geolocation rename, pipeline exporter
- [x] 01-02-PLAN.md -- NYC data removal: geotags, related_tags, HTML text, map style names, admin titles

### Phase 2: Buenos Aires Locations
**Goal**: The app has a complete set of Buenos Aires cultural venues, galleries, and spaces with correct coordinates on the map
**Depends on**: Phase 1
**Requirements**: LOC-01, LOC-02, LOC-03
**Plans:** 1 plan
**Success Criteria** (what must be TRUE):
  1. Buenos Aires venues, galleries, and cultural spaces appear as locations in the database and JSON exports
  2. Clicking a location marker on the map shows it at the correct real-world position (geocoding is accurate)
  3. Location data uses the existing schema format -- no structural changes to the data model

Plans:
- [x] 02-01-PLAN.md -- Update geocode.php for BA, create seed SQL files for ~40 venues across museums, cultural centers, galleries, and theaters

### Phase 3: Pipeline & Tags
**Goal**: The data pipeline crawls Argentine event sources, extracts Spanish-language events via Gemini, and the tag system supports BA cultural categories -- making the app fully functional with live Buenos Aires data
**Depends on**: Phase 2
**Requirements**: PIPE-01, PIPE-02, PIPE-03, TAG-01, TAG-02, TAG-03
**Plans:** 2 plans
**Success Criteria** (what must be TRUE):
  1. Running the pipeline crawls configured Argentine event source URLs and produces structured event data
  2. Spanish-language event content is correctly extracted by Gemini -- event titles, descriptions, dates, and venues are parsed accurately
  3. Pipeline output is valid JSON in the existing format, loadable by the frontend without changes
  4. Tag set reflects BA art scene categories (galleries, theater, dance, music, street art, etc.) and tag filtering/search works with the new tags
  5. Related tags system connects BA cultural categories meaningfully (e.g., selecting "Teatro" surfaces related performance tags)

Plans:
- [x] 03-01-PLAN.md -- Pipeline prompt adaptation for BA/Spanish, processor NYC cleanup, website seed SQL, tag rules
- [x] 03-02-PLAN.md -- BA cultural category relationships in related_tags.json

### Phase 4: JSON API Crawling
**Goal**: Add lightweight HTTP-based crawling for sites that expose JSON/JSONP API endpoints, bypassing the browser entirely. First target: Alternativa Teatral (920 events via JSONP).
**Depends on**: Phase 3
**Plans:** 1 plan

**Context:**
- Alternativa Teatral endpoint: `get-json.php?t=novedades&r=cartelera` returns JSONP with 920 events (~732KB)
- Each event includes: titulo, clasificaciones (tags), lugares (venue, address, zone, lat/lng, showtimes with proxima_fecha), url, url_entradas
- JSON-to-markdown replaces the browser step, not the AI -- Gemini still needed for venue matching, dedup, tag normalization, description generation, date expansion
- Existing merger dedup (location + overlapping dates + similar name) handles re-crawls; token cost is the main concern

**Implementation:**
- DB: `crawl_mode ENUM('browser','json_api')` and `json_api_config JSON` columns on websites table (already migrated locally)
- `json_api_config` stores per-source settings: JSONP callback, encoding, data_path, fields_include, date filter window
- Token reduction (3 layers): fields_include strips useless fields (~500→~200 chars/event), date window filter (920→~200-300 events), auto-flatten to markdown

**Files to modify:**
- `crawler.py` -- Add `crawl_json_api()`: HTTP GET via httpx, strip JSONP wrapper, decode, navigate data_path, filter by date window, select fields, flatten to markdown
- `db.py` -- Add crawl_mode and json_api_config to `get_websites_due_for_crawling()` SELECT/dict
- `main.py` -- Split crawl routing: JSON API via HTTP (no browser), browser via existing AsyncWebCrawler; both feed into same extraction step

**Success Criteria** (what must be TRUE):
  1. Websites with crawl_mode='json_api' are crawled via simple HTTP request, not browser
  2. JSONP response is correctly unwrapped, decoded, filtered by date window, and flattened to markdown
  3. Markdown output feeds into existing Gemini extraction step identically to browser-crawled content
  4. Alternativa Teatral events appear in pipeline output with correct titles, venues, dates, and tags
  5. Token usage is significantly reduced compared to sending raw 732KB response

**Blockers/Concerns:**
- Plateanet may be geo-blocked from Indonesian server IPs -- may need proxy configuration
- Alternativa Teatral heavy JS/infinite scroll may limit basic HTML crawl effectiveness (hence this JSON API approach)

Plans:
- [ ] 04-01-PLAN.md -- Schema columns, db.py query update, crawl_json_api() function, main.py routing

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Map Swap & NYC Cleanup | 2/2 | Complete | 2026-02-25 |
| 2. Buenos Aires Locations | 1/1 | Complete | 2026-03-05 |
| 3. Pipeline & Tags | 2/2 | Complete | 2026-03-05 |
| 4. JSON API Crawling | 0/1 | Not started | - |
