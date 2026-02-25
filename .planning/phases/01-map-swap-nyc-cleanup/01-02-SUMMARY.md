---
phase: 01-map-swap-nyc-cleanup
plan: 02
subsystem: data-and-content
tags: [geotags, barrios, map-styles, geojson, html, branding, nyc-cleanup]

requires:
  - phase: none
    provides: n/a
provides:
  - Buenos Aires barrio geotags replacing NYC neighborhoods
  - Inline barrio GeoJSON labels in both map style files
  - All user-facing text rebranded from Fomo NYC to Momaverse Buenos Aires
  - Empty related_tags.json ready for Phase 3 regeneration
affects:
  - Phase 3 (Pipeline & Tags) will regenerate related_tags.json with BA data

tech-stack:
  added: []
  patterns:
    - Inline GeoJSON source in MapLibre style files for custom label layers

key-files:
  created: []
  modified:
    - src/data/tags.json
    - src/data/related_tags.json
    - src/data/map-style-dark.json
    - src/data/map-style-light.json
    - src/index.html
    - src/about.html
    - src/admin/index.php
    - src/admin/history.php
    - src/admin/conflicts.php
    - database/schema.sql

key-decisions:
  - "Inline GeoJSON in style files (not separate barrios.geojson) for automatic theme-change resilience"
  - "Kept data-key='nyc2025' XOR encryption key in about.html unchanged (breaking it would break Discord link decryption)"
  - "Microcentro added as 49th geotag (not one of official 48 barrios, but commonly used area name)"

patterns-established:
  - "Barrio labels via inline GeoJSON source + symbol layer in MapLibre style JSON"

duration: 5min
completed: 2026-02-25
---

# Phase 1 Plan 02: NYC Data Removal & Buenos Aires Content Summary

**Replaced all NYC geotags, text, and branding with Buenos Aires content; added 48 barrio center-point labels inline in both map style files.**

## Performance
- **Duration:** 5 minutes
- **Started:** 2026-02-25T15:42:48Z
- **Completed:** 2026-02-25T15:47:29Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Replaced 220 NYC neighborhood geotags with 49 Buenos Aires barrios (48 official + Microcentro)
- Cleared related_tags.json from 2MB of NYC tag relationships to empty object `{}`
- Added inline barrios GeoJSON source (48 center points) to both dark and light map style files
- Added barrio-labels symbol layer (zoom 11-16, uppercase, Inter SemiBold) to both styles
- Renamed map styles from "Fomo NYC Dark/Light" to "Momaverse Buenos Aires Dark/Light"
- Updated all user-facing HTML text in index.html and about.html to reference Buenos Aires/Momaverse
- Updated admin page titles (3 PHP files) from "fomo.nyc Admin" to "Momaverse Admin"
- Updated database schema comment from "fomo.nyc" to "Momaverse"

## Task Commits
1. **Task 1: Replace geotags, clear related_tags, add barrio labels to map styles** - `e0285b4` (feat)
2. **Task 2: Update HTML text, admin titles, and database schema comment** - `ab3d60d` (feat)

## Files Created/Modified
- `src/data/tags.json` - 49 BA barrios replace 220 NYC neighborhoods
- `src/data/related_tags.json` - Cleared to empty object `{}`
- `src/data/map-style-dark.json` - Renamed, added barrios source + barrio-labels layer
- `src/data/map-style-light.json` - Renamed, added barrios source + barrio-labels layer
- `src/index.html` - Title, alt text, aria labels, modal text updated
- `src/about.html` - Title, description, logo, acknowledgements updated
- `src/admin/index.php` - Title updated
- `src/admin/history.php` - Title updated
- `src/admin/conflicts.php` - Title updated
- `database/schema.sql` - Header comment updated

## Decisions Made
- **Inline GeoJSON over separate file:** Embedded barrio center points directly in style JSON files rather than using a separate `barrios.geojson` file. This avoids the theme-change problem (setStyle destroys custom sources/layers) and eliminates an extra fetch request.
- **Kept XOR key unchanged:** The `data-key="nyc2025"` attribute in about.html is an encryption key for obfuscating the Discord URL, not user-facing text. Changing it would break the link decryption. This is the sole remaining "nyc" substring in modified files.
- **Removed Statue of Liberty emoji:** Removed the Statue of Liberty emoji from the feedback description and about page acknowledgements as NYC-specific symbolism.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Phase 1 is complete (both plans 01-01 and 01-02 finished). The map is recentered on Buenos Aires with correct bounds, barrio labels are embedded in style files, and all NYC references are removed from data and UI. Ready to proceed to Phase 2 (Buenos Aires Locations).
