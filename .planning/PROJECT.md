# Momaverse Buenos Aires

## What This Is

An interactive map showing the Buenos Aires creative and artist scene — gallery openings, live performances, underground events, and everything cultural happening across the city. Built on an existing NYC-focused map application (MapLibre GL, vanilla JS frontend, Python crawl pipeline, PHP/MySQL backend), this milestone replaces NYC with Buenos Aires and gets the data pipeline crawling Argentine event sources.

## Core Value

People can see what's happening and where in the Buenos Aires art scene, right now, on a map.

## Requirements

### Validated

- ✓ Interactive map with event markers (WebGL/MapLibre) — existing
- ✓ Tag-based filtering with multi-state selection (selected/required/forbidden) — existing
- ✓ Search with relevance scoring — existing
- ✓ Date range picker for filtering events by time — existing
- ✓ Event detail popups on marker click — existing
- ✓ Two-phase data loading for fast initial render — existing
- ✓ Responsive design (mobile bottom sheet, desktop sidebar) — existing
- ✓ Data pipeline: crawl sites, AI-extract events with Gemini, store in MySQL — existing
- ✓ Build system with esbuild bundling and content-hashed production output — existing

### Active

- [ ] Map centered on Buenos Aires instead of NYC
- [ ] Pipeline configured with Argentine event source URLs
- [ ] Crawlers adapted for BA site structures
- [ ] Location data (venues, galleries, spaces) for Buenos Aires
- [ ] Events extracted and geocoded for Buenos Aires locations
- [ ] Tags/categories relevant to BA art scene (Spanish-language support in tags)
- [ ] Map style/bounds appropriate for Buenos Aires geography

### Out of Scope

- Multi-city architecture / city switcher — future milestone, hard-code BA for now
- New UI features or UX improvements — maintain existing functionality
- Ticket link enhancements — future milestone
- User accounts or personalization — not needed
- Mobile app — web only

## Context

- Existing codebase is a working NYC interactive event map
- Architecture: vanilla JS modular frontend, PHP API, MySQL DB, Python pipeline with crawl4ai + Gemini AI extraction
- Pipeline crawls event websites, extracts structured data via Gemini, stores in MySQL, exports to JSON for frontend
- User has Buenos Aires event sources identified and ready to configure
- The BA art scene spans galleries, theater, dance, music, street art, pop-ups, and underground events
- Spanish-language content will need to be handled in crawling and extraction

## Constraints

- **Stack**: Keep existing tech stack (JS/PHP/MySQL/Python) — working and deployed
- **Approach**: Minimal changes to existing code — swap city-specific config, don't rewrite
- **Data sources**: User provides BA source URLs — pipeline adapts to their structure
- **Language**: BA event data is primarily in Spanish — extraction and tags must handle this

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Replace NYC rather than add alongside | Keep it simple, multi-city is a future milestone | — Pending |
| Hard-code Buenos Aires, no city abstraction | Avoid premature architecture, ship BA first | — Pending |
| Keep all existing UI/UX as-is | Focus effort on data pipeline and city swap, not new features | — Pending |

---
*Last updated: 2026-02-24 after initialization*
