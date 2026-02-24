# Requirements: Momaverse Buenos Aires

**Defined:** 2026-02-24
**Core Value:** People can see what's happening and where in the Buenos Aires art scene, right now, on a map.

## v1 Requirements

### Map Configuration

- [ ] **MAP-01**: Map default view centered on Buenos Aires (-34.60, -58.38)
- [ ] **MAP-02**: Map zoom/pan bounds constrained to Buenos Aires metro area
- [ ] **MAP-03**: Buenos Aires barrio labels visible on map (Palermo, San Telmo, La Boca, etc.)

### Data Pipeline

- [ ] **PIPE-01**: Crawler configured with Argentine event source URLs
- [ ] **PIPE-02**: Gemini extraction prompts adapted for Spanish-language event content
- [ ] **PIPE-03**: Pipeline outputs Buenos Aires events in existing JSON format
- [ ] **PIPE-04**: NYC events and locations removed from dataset entirely

### Location Data

- [ ] **LOC-01**: Buenos Aires venues, galleries, and cultural spaces added to location database
- [ ] **LOC-02**: BA venue addresses geocoded with correct lat/lng coordinates
- [ ] **LOC-03**: Location data structure matches existing format (no schema changes)

### Tags & Categories

- [ ] **TAG-01**: Tag set updated with categories relevant to BA art scene (in English)
- [ ] **TAG-02**: Related tags system updated for BA cultural categories
- [ ] **TAG-03**: Existing tag filtering/search works with new BA tag set

## v2 Requirements

### Multi-City

- **CITY-01**: City-agnostic architecture supporting multiple cities
- **CITY-02**: City switcher UI for selecting between cities
- **CITY-03**: Per-city pipeline configuration

### UX Enhancements

- **UX-01**: Enhanced ticket link display in event details
- **UX-02**: User accounts and personalization

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-city architecture | Future milestone -- hard-code BA for now |
| City switcher UI | Requires multi-city architecture first |
| New UI features | Maintain existing functionality, focus on city swap |
| Ticket link enhancements | Future milestone |
| User accounts | Not needed for v1 |
| Mobile app | Web only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MAP-01 | Phase 1 | Pending |
| MAP-02 | Phase 1 | Pending |
| MAP-03 | Phase 1 | Pending |
| PIPE-01 | Phase 3 | Pending |
| PIPE-02 | Phase 3 | Pending |
| PIPE-03 | Phase 3 | Pending |
| PIPE-04 | Phase 1 | Pending |
| LOC-01 | Phase 2 | Pending |
| LOC-02 | Phase 2 | Pending |
| LOC-03 | Phase 2 | Pending |
| TAG-01 | Phase 3 | Pending |
| TAG-02 | Phase 3 | Pending |
| TAG-03 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-24 after roadmap creation*
