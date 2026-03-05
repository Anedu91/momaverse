# Roadmap: Momaverse Buenos Aires

## Overview

Swap the existing NYC interactive event map to Buenos Aires in three phases: repoint the map and clear NYC data, populate BA location data, then wire up the pipeline and tags so real Argentine events flow through. The existing UI, search, filtering, and rendering remain untouched -- this is a city swap, not a rewrite.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Map Swap & NYC Cleanup** - Repoint the map to Buenos Aires and remove all NYC-specific data
- [ ] **Phase 2: Buenos Aires Locations** - Populate venue/gallery/space data with correct geocoding
- [ ] **Phase 3: Pipeline & Tags** - Configure crawlers for BA sources, adapt extraction for Spanish, define BA tag taxonomy

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
**Success Criteria** (what must be TRUE):
  1. Buenos Aires venues, galleries, and cultural spaces appear as locations in the database and JSON exports
  2. Clicking a location marker on the map shows it at the correct real-world position (geocoding is accurate)
  3. Location data uses the existing schema format -- no structural changes to the data model
**Plans**: TBD

Plans:
- [ ] 02-01: BA venue data population and geocoding

### Phase 3: Pipeline & Tags
**Goal**: The data pipeline crawls Argentine event sources, extracts Spanish-language events via Gemini, and the tag system supports BA cultural categories -- making the app fully functional with live Buenos Aires data
**Depends on**: Phase 2
**Requirements**: PIPE-01, PIPE-02, PIPE-03, TAG-01, TAG-02, TAG-03
**Success Criteria** (what must be TRUE):
  1. Running the pipeline crawls configured Argentine event source URLs and produces structured event data
  2. Spanish-language event content is correctly extracted by Gemini -- event titles, descriptions, dates, and venues are parsed accurately
  3. Pipeline output is valid JSON in the existing format, loadable by the frontend without changes
  4. Tag set reflects BA art scene categories (galleries, theater, dance, music, street art, etc.) and tag filtering/search works with the new tags
  5. Related tags system connects BA cultural categories meaningfully (e.g., selecting "Teatro" surfaces related performance tags)
**Plans**: TBD

Plans:
- [ ] 03-01: Pipeline configuration and Spanish extraction
- [ ] 03-02: BA tag taxonomy and related tags

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Map Swap & NYC Cleanup | 2/2 | Complete | 2026-02-25 |
| 2. Buenos Aires Locations | 0/1 | Not started | - |
| 3. Pipeline & Tags | 0/2 | Not started | - |
