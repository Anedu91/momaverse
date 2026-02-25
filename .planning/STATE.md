# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** People can see what's happening and where in the Buenos Aires art scene, right now, on a map.
**Current focus:** Phase 2 - Buenos Aires Locations

## Current Position

Phase: 1 of 3 (Map Swap & NYC Cleanup) -- COMPLETE
Plan: 2 of 2 in current phase
Status: Phase complete
Last activity: 2026-02-25 -- Completed 01-02-PLAN.md (NYC Data Removal & Buenos Aires Content)

Progress: [████░░░░░░] 40%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 4min
- Total execution time: 7min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Map Swap & NYC Cleanup | 2/2 | 7min | 4min |

**Recent Trend:**
- Last 5 plans: 01-01 (2min), 01-02 (5min)
- Trend: -

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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed Phase 1 (01-02-PLAN.md)
Resume file: None
