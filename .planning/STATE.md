# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** People can see what's happening and where in the Buenos Aires art scene, right now, on a map.
**Current focus:** Phase 1 - Map Swap & NYC Cleanup

## Current Position

Phase: 1 of 3 (Map Swap & NYC Cleanup)
Plan: 1 of 2 in current phase
Status: In progress
Last activity: 2026-02-25 -- Completed 01-01-PLAN.md (Map Config & Bounds Swap)

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity:**
- Total plans completed: 1
- Average duration: 2min
- Total execution time: 2min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Map Swap & NYC Cleanup | 1/2 | 2min | 2min |

**Recent Trend:**
- Last 5 plans: 01-01 (2min)
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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 01-01-PLAN.md
Resume file: None
