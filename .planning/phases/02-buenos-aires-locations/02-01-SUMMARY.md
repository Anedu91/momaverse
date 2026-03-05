---
phase: 02-buenos-aires-locations
plan: 01
subsystem: database
tags: [sql, seeds, geocoding, buenos-aires, locations]

# Dependency graph
requires:
  - phase: 01-map-swap-nyc-cleanup
    provides: CITY_BOUNDS coordinates, empty database cleared of NYC data
provides:
  - 40 BA cultural venue seed files (museums, cultural centers, galleries, theaters)
  - BA-biased geocoding script (region=ar, components=country:AR)
affects: [02-02 (website/pipeline seed data), 03 (pipeline needs location_id matching)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SQL seed file pattern (USE fomo, INSERT INTO locations, dynamic ID lookup for alternate names)
    - Argentine address format (street name first, CABA suffix)

key-files:
  created:
    - database/seeds/museos_ba.sql
    - database/seeds/centros_culturales_ba.sql
    - database/seeds/galerias_y_espacios_ba.sql
    - database/seeds/teatros_ba.sql
  modified:
    - scripts/geocode.php

key-decisions:
  - "Seed files only contain locations and alternate_names (no website/pipeline data) per Phase 3 boundary"
  - "40 venues across 4 categories gives broad coverage without duplicating CTBA theaters"

patterns-established:
  - "BA seed file naming: {category}_ba.sql in database/seeds/"
  - "Alternate names via dynamic ID lookup: SET @id = (SELECT id FROM locations WHERE name = '...' LIMIT 1)"

# Metrics
duration: 3min
completed: 2026-03-05
---

# Phase 2 Plan 1: BA Venue Data Population Summary

**40 Buenos Aires cultural venues seeded across 4 SQL files with BA-biased geocoding -- museums, cultural centers, galleries, and theaters**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-05T04:33:40Z
- **Completed:** 2026-03-05T04:36:36Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Updated geocode.php to bias toward Buenos Aires (BA_BOUNDS, region=ar, components=country:AR)
- Created 4 SQL seed files with 40 new venues (9 museums + 9 cultural centers + 12 galleries + 10 theaters)
- All 46 total BA locations (40 new + 6 CTBA) have coordinates within CITY_BOUNDS
- Alternate names created for venues with common abbreviations (MALBA, MNBA, CCK, CCR, etc.)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update geocode.php for Buenos Aires** - `f16319f` (feat)
2. **Task 2: Create BA venue seed SQL files** - `7f1db2f` (feat)

## Files Created/Modified
- `scripts/geocode.php` - Updated bounds, region, components for Buenos Aires geocoding bias
- `database/seeds/museos_ba.sql` - 9 museums (MALBA, MNBA, MAMBA, MACBA, etc.)
- `database/seeds/centros_culturales_ba.sql` - 9 cultural centers (CCK, CCR, Usina del Arte, etc.)
- `database/seeds/galerias_y_espacios_ba.sql` - 12 galleries and art spaces (Proa, Fortabat, Benzacar, etc.)
- `database/seeds/teatros_ba.sql` - 10 theaters (Colon, Konex, Cervantes, Gran Rex, etc.)

## Decisions Made
- Seed files only contain locations and location_alternate_names tables -- no website, instagram, or pipeline data (that belongs to Phase 3)
- 40 venues across 4 categories provides broad cultural coverage of CABA without overloading the map

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 46 total BA locations ready for map display
- Location data available for Phase 3 pipeline to link websites and extract events
- Geocode script ready for future venue additions with BA bias

---
*Phase: 02-buenos-aires-locations*
*Completed: 2026-03-05*
