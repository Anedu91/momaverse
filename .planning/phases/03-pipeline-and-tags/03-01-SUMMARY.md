---
phase: 03-pipeline-and-tags
plan: 01
subsystem: pipeline, database
tags: [python, gemini, sql, crawl, spanish, tags]

# Dependency graph
requires:
  - phase: 02-buenos-aires-locations
    provides: Location seed data (venues with names for FK links)
provides:
  - BA-adapted Gemini extraction prompts in pipeline
  - Spanish-to-English tag rewrite rules
  - 4 Argentine event source website configurations
affects: [future pipeline runs, future source additions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Spanish-language prompt adaptation pattern for Gemini extraction"
    - "SET @var pattern for website seed FK linking"

key-files:
  created:
    - database/seeds/tag_rules_ba.sql
    - database/seeds/websites_ba.sql
  modified:
    - pipeline/extractor.py
    - pipeline/processor.py

key-decisions:
  - "Generalized city-name regex in create_short_name (processor.py) to work for any city, not just NYC"
  - "4 initial sources: Alternativa Teatral, Plateanet, Teatro El Picadero, Microteatro"
  - "Alternativa Teatral complex API crawling deferred to future phase; basic HTML crawl included now"
  - "Plateanet geo-blocking noted; may need proxy from Indonesian server"
  - "Teatro El Picadero linked to Phase 2 location via website_locations FK"
  - "Microteatro not in Phase 2 seeds; no location FK (venue-only website entry)"

patterns-established:
  - "Website seed pattern: INSERT website -> SET @id -> INSERT urls/tags/locations"
  - "Tag rules: Spanish lowercase pattern -> English replacement"

# Metrics
duration: 5min
completed: 2026-03-05
---

# Phase 3 Plan 1: Pipeline & Tag Rules for Buenos Aires Summary

**BA-adapted Gemini prompts, 22 Spanish-to-English tag rewrites, and 4 Argentine event source websites configured for crawling**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T12:36:00Z
- **Completed:** 2026-03-05T12:41:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Pipeline prompts now reference Buenos Aires instead of NYC; tags instruction requires English output from Spanish content
- NYC borough normalization removed from processor.py; city-name regex generalized
- 22 Spanish-to-English tag rewrite rules and 5 BA-redundant exclusion rules seeded
- 4 Argentine event sources configured: Alternativa Teatral, Plateanet, Teatro El Picadero, Microteatro

## Task Commits

Each task was committed atomically:

1. **Task 1: Adapt pipeline Python files for Buenos Aires** - `f0a77c4` (feat)
2. **Task 2: Checkpoint decision** - user provided 4 Argentine event sources
3. **Task 3: Create SQL seed files for websites and tag rules** - `738b8aa` (feat)

## Files Created/Modified
- `pipeline/extractor.py` - Gemini prompts updated to Buenos Aires context; Spanish date format note added
- `pipeline/processor.py` - NYC borough lists emptied; city-name regex generalized
- `database/seeds/tag_rules_ba.sql` - 22 rewrite rules (musica->Music, etc.) + 5 exclude rules (buenosaires, caba, etc.)
- `database/seeds/websites_ba.sql` - 4 websites with URLs, tags, and location FK for Teatro El Picadero

## Decisions Made
- Generalized `r'\s+in\s+NYC\s*[-–].*$'` regex to `r'\s+in\s+\w+\s*[-–].*$'` so create_short_name works for any city
- Alternativa Teatral: included with basic HTML crawl; complex JSON API deferred to future phase per user preference
- Plateanet: included with geo-blocking warning for Indonesian server IPs
- Teatro El Picadero: matched to Phase 2 seed "Teatro El Picadero" and linked via website_locations FK
- Microteatro: no Phase 2 location match; added as standalone website entry

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Generalized city-name regex in create_short_name**
- **Found during:** Task 1 (pipeline adaptation)
- **Issue:** `r'\s+in\s+NYC\s*[-–].*$'` regex only stripped NYC suffixes, would fail for "in Buenos Aires" or any other city
- **Fix:** Changed to `r'\s+in\s+\w+\s*[-–].*$'` to match any city name
- **Files modified:** pipeline/processor.py
- **Verification:** grep confirms no NYC references remain
- **Committed in:** f0a77c4 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor improvement for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Pipeline is ready to crawl Argentine sources once seeds are loaded into the database
- Tag rules will automatically translate Spanish tags to English during processing
- Alternativa Teatral may need enhanced crawling in a future phase (JS rendering / API integration)
- Plateanet may need proxy configuration if geo-blocked

---
*Phase: 03-pipeline-and-tags*
*Completed: 2026-03-05*
