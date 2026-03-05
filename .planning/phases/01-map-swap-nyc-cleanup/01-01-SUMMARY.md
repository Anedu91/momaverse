---
phase: 01-map-swap-nyc-cleanup
plan: 01
subsystem: map-config
tags: [maplibre, coordinates, buenos-aires, geolocation, bounds, pipeline-exporter]

requires:
  - phase: none
    provides: first plan in project
provides:
  - Buenos Aires map configuration (center, zoom, bounds)
  - City-agnostic geolocation validation (isWithinCityBounds)
  - MapLibre maxBounds constraining panning to BA metro area
  - Pipeline exporter bounding box targeting BA core area
affects:
  - 01-02 (style cache-bust version bumped to v=8)
  - Phase 2 (locations must fall within CITY_BOUNDS)
  - Phase 3 (pipeline exporter uses updated INIT_LAT/LNG_RANGE)

tech-stack:
  added: []
  patterns:
    - "CITY_BOUNDS config drives both geolocation validation and map maxBounds"

key-files:
  created: []
  modified:
    - src/js/script.js
    - pipeline/exporter.py

key-decisions:
  - "CITY_BOUNDS used for maxBounds (plan specifies using config values rather than separate hardcoded bounds)"
  - "Zoom level 13 for BA (more compact urban core than NYC's zoom 12)"

patterns-established:
  - "City-agnostic naming: CITY_BOUNDS and isWithinCityBounds instead of city-specific names"

duration: 2min
completed: 2026-02-25
---

# Phase 1 Plan 01: Map Config & Bounds Swap Summary

**Repointed map from NYC to Buenos Aires: center coordinates, zoom level, city bounds, geolocation validation, maxBounds panning constraint, and pipeline exporter bounding box.**

## Performance
- **Duration:** 2 minutes
- **Started:** 2026-02-25T15:40:45Z
- **Completed:** 2026-02-25T15:42:50Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments
- MAP_INITIAL_VIEW changed from NYC (40.70, -73.97) to Buenos Aires (-34.6083, -58.4000)
- MAP_INITIAL_ZOOM changed from 12 to 13 for BA's more compact core
- NYC_BOUNDS renamed to CITY_BOUNDS with BA metro area coordinates (lat: -34.75 to -34.50, lng: -58.60 to -58.28)
- isWithinNYC renamed to isWithinCityBounds with all references updated
- maxBounds added to MapLibre Map constructor using CITY_BOUNDS values to constrain panning
- Style URL cache-bust bumped from v=7 to v=8
- Pipeline exporter INIT_LAT_RANGE and INIT_LNG_RANGE updated to BA core area
- Zero NYC references remain in either modified file

## Task Commits
1. **Task 1: Update App.config and geolocation in script.js** - `31e5fc1` (feat)
2. **Task 2: Update pipeline exporter bounding box** - `6e5fcbe` (feat)

## Files Created/Modified
- `src/js/script.js` - Updated MAP_INITIAL_VIEW, MAP_INITIAL_ZOOM, renamed NYC_BOUNDS to CITY_BOUNDS, renamed isWithinNYC to isWithinCityBounds, added maxBounds to Map constructor, bumped style version, updated all comments
- `pipeline/exporter.py` - Updated INIT_LAT_RANGE and INIT_LNG_RANGE to BA coordinates, updated comments

## Decisions Made
- Used CITY_BOUNDS config values for maxBounds rather than separate hardcoded coordinates -- keeps a single source of truth for the city boundary
- Plan specified zoom 13 for BA (NYC was 12) due to more compact urban core

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Build verification (`npm run build`) failed due to missing `node_modules/esbuild` in the local environment. This is an environment setup issue unrelated to the code changes. The changes are purely config value swaps with no syntax impact.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 01-02 (NYC data removal) can execute independently -- it modifies different files (HTML, style JSON, tags, related_tags, admin PHP)
- The v=8 cache-bust on style URLs will align with plan 01-02's style name changes
- Phase 2 (Buenos Aires Locations) can begin after Phase 1 completes -- location coordinates should fall within the new CITY_BOUNDS
