# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** People can see what's happening and where in the Buenos Aires art scene, right now, on a map.
**Current focus:** Phase 2 - Buenos Aires Locations -- COMPLETE

## Current Position

Phase: 2 of 3 (Buenos Aires Locations) -- COMPLETE
Plan: 1 of 1 in current phase
Status: Phase complete
Last activity: 2026-03-05 -- Completed 02-01-PLAN.md (BA Venue Data Population)

Progress: [██████░░░░] 60%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 3min
- Total execution time: 10min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Map Swap & NYC Cleanup | 2/2 | 7min | 4min |
| 2. Buenos Aires Locations | 1/1 | 3min | 3min |

**Recent Trend:**
- Last 5 plans: 01-01 (2min), 01-02 (5min), 02-01 (3min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: PIPE-04 (remove NYC data) grouped with Phase 1 map swap rather than Phase 3 pipeline -- cleaning old data is part of repointing the map, not part of building the new pipeline.
- Roadmap: Tags grouped with pipeline (Phase 3) because tag definitions and pipeline extraction are tightly coupled -- the pipeline needs to know what tags to assign.
- 01-01: CITY_BOUNDS used for both geolocation validation and MapLibre maxBounds (single source of truth)
- 01-01: City-agnostic naming pattern (CITY_BOUNDS, isWithinCityBounds) supports future multi-city if needed
- 01-02: Inline GeoJSON in style files (not separate barrios.geojson) for automatic theme-change resilience
- 01-02: Kept data-key XOR encryption key unchanged to preserve Discord link decryption
- 02-01: Seed files only contain locations and alternate_names (no website/pipeline data) per Phase 3 boundary
- 02-01: 40 venues across 4 categories gives broad coverage without duplicating CTBA theaters

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-03-05
Stopped at: Completed Phase 2 (02-01-PLAN.md)
Resume file: None
