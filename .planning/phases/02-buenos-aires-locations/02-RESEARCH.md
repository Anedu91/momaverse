# Phase 2: Buenos Aires Locations - Research

**Researched:** 2026-03-05
**Domain:** Location data population, geocoding, SQL seed files
**Confidence:** HIGH

## Summary

This phase is primarily a data population task, not a code-building task. The codebase already has all the infrastructure needed: a `locations` table with a well-defined schema, a `scripts/add_locations.php` tool for inserting locations (with tag support, duplicate checking, and both local/production modes), a `scripts/geocode.php` script for geocoding via Google Maps API, and a pipeline exporter that generates JSON for the frontend. Phase 1 has already cleared NYC data and configured `CITY_BOUNDS` for Buenos Aires (lat: -34.75 to -34.50, lng: -58.60 to -58.28).

The work is: (1) curate a list of Buenos Aires cultural venues with addresses, (2) geocode them accurately using the existing geocode script (updated to bias for Buenos Aires instead of NYC), (3) write SQL seed files following the established pattern from `complejo_teatral_ba.sql`, and (4) run the pipeline exporter to generate updated JSON files.

**Primary recommendation:** Use SQL seed files (like `complejo_teatral_ba.sql`) as the primary method for populating locations, with the geocode script updated to use Buenos Aires bounds instead of NYC bounds. No schema changes needed.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Tool | Purpose | Why Standard |
|------|---------|--------------|
| `database/seeds/*.sql` | SQL seed files for location data | Already established pattern (complejo_teatral_ba.sql exists) |
| `scripts/geocode.php` | Google Maps Geocoding API wrapper | Already exists, needs BA bounds update |
| `scripts/add_locations.php` | Location insertion with tag/duplicate handling | Already exists, proven at scale (1400+ NYC locations) |
| `pipeline/exporter.py` | Export locations to JSON for frontend | Already exists, already configured for BA bounding box |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| Google Maps Geocoding API | Address-to-coordinate conversion | When venues need lat/lng from address strings |
| `scripts/merge_locations.php` | Dedup locations | If duplicate venues appear from multiple seeds |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQL seed files | `add_locations.php` with hardcoded array | Seed files are version-controllable and rerunnable; add_locations.php is better for one-off additions |
| Google Geocoding API | Nominatim (OpenStreetMap) | Google has better coverage of Argentine venues/POIs; existing script already uses Google |

## Architecture Patterns

### Recommended Seed File Structure
```
database/seeds/
├── complejo_teatral_ba.sql          # Already exists (6 theaters)
├── museos_ba.sql                    # Major museums (MALBA, MNBA, Moderno, etc.)
├── centros_culturales_ba.sql        # Cultural centers (CCR, Usina del Arte, CC Kirchner, etc.)
├── galerias_ba.sql                  # Art galleries
├── teatros_independientes_ba.sql    # Independent theaters
└── espacios_alternativos_ba.sql     # Alternative/experimental spaces
```

### Pattern 1: SQL Seed File Format
**What:** Each seed file is a self-contained SQL script that inserts locations, alternate names, and related data
**When to use:** For batches of related venues
**Example:**
```sql
-- Source: existing complejo_teatral_ba.sql pattern
USE fomo;

INSERT INTO locations (name, short_name, very_short_name, address, description, lat, lng, emoji) VALUES
('MALBA', 'MALBA', 'MALBA', 'Av. Pres. Figueroa Alcorta 3415, CABA', 'Museo de Arte Latinoamericano de Buenos Aires.', -34.577400, -58.403900, '🏛️');
```

### Pattern 2: Geocode Script with BA Bias
**What:** Update `geocode.php` to use Buenos Aires bounds instead of NYC
**When to use:** When geocoding venue names or addresses for Buenos Aires
**Key change:** Replace `NYC_BOUNDS` constant with Buenos Aires bounds
```php
// Current (NYC):
define('NYC_BOUNDS', '40.4774,-74.2591|41.2919,-73.4809');

// Updated (Buenos Aires):
define('BA_BOUNDS', '-34.75,-58.60|-34.50,-58.28');
// Also change 'region' => 'us' to 'region' => 'ar'
```

### Pattern 3: Location Data Structure
**What:** Each location entry must include all required fields per schema
**Required fields:** name, lat, lng
**Recommended fields:** short_name, address, description, emoji
**Optional fields:** very_short_name, alt_emoji

### Anti-Patterns to Avoid
- **Inserting without geocode verification:** Every lat/lng must be validated against CITY_BOUNDS before insertion
- **Using full street addresses as names:** Use venue name as `name`, full address in `address` field
- **Forgetting alternate names:** Major venues often have multiple names (e.g., "MALBA" vs "Museo de Arte Latinoamericano de Buenos Aires")
- **Hardcoding IDs:** Use `SELECT id FROM locations WHERE name = ...` for foreign key references, never hardcode auto-increment IDs

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Geocoding | Custom geocoder | `scripts/geocode.php` (with BA update) | Already wraps Google API, handles errors, supports batch mode |
| Location insertion | Raw SQL by hand | `scripts/add_locations.php` or seed SQL files | Handles duplicate checking, tag creation, edit logging |
| Location export | Custom JSON builder | `pipeline/exporter.py` | Already handles init/full split, coordinate filtering, compact JSON |
| Duplicate detection | Manual name matching | `scripts/merge_locations.php` | Already handles reference updates, alternate names, tag merging |
| Coordinate validation | Manual range checking | `CITY_BOUNDS` in `script.js` and exporter `INIT_LAT_RANGE`/`INIT_LNG_RANGE` | Already defined for Buenos Aires |

**Key insight:** All the tooling exists from the NYC era. The task is data curation and geocoding, not building infrastructure.

## Common Pitfalls

### Pitfall 1: Geocoding Returns Wrong Location
**What goes wrong:** Searching "Teatro Colon" returns a result in Spain instead of Buenos Aires
**Why it happens:** Google Geocoding API biases by the `bounds` and `region` parameters but doesn't restrict to them. Ambiguous venue names may match other countries.
**How to avoid:** (1) Always include "CABA" or "Buenos Aires" in the address field, (2) Update geocode.php to use `region=ar` and BA bounds, (3) Use the `components=country:AR` parameter for strict country filtering, (4) Validate every result falls within CITY_BOUNDS
**Warning signs:** lat/lng outside the range -34.75 to -34.50, -58.60 to -58.28

### Pitfall 2: Address Format Inconsistency
**What goes wrong:** Argentine addresses have a different format than US addresses (e.g., "Av. Corrientes 1530, CABA" not "1530 Corrientes Ave")
**Why it happens:** The existing seed file uses Argentine address format. Must be consistent.
**How to avoid:** Use Argentine address conventions: street name first, then number. Include "CABA" (Ciudad Autonoma de Buenos Aires) as the city suffix. Use "Av." for Avenida.
**Warning signs:** Addresses that look like US format or use English street type abbreviations

### Pitfall 3: INIT_LAT_RANGE / INIT_LNG_RANGE Mismatch
**What goes wrong:** Locations exist in the database but don't appear in `locations.init.json`
**Why it happens:** The exporter uses `INIT_LAT_RANGE = (-34.63, -34.57)` and `INIT_LNG_RANGE = (-58.44, -58.36)` to decide which locations go in the "init" set. This is a smaller bbox than CITY_BOUNDS.
**How to avoid:** Understand that init covers roughly the core BA area (Palermo/Recoleta/San Telmo/La Boca). Locations outside this box will only appear in `locations.full.json`. This is by design, not a bug.
**Warning signs:** Popular venues in outer barrios (e.g., Mataderos, Belgrano) not appearing in initial load

### Pitfall 4: Emoji Encoding Issues
**What goes wrong:** Emoji characters get mangled in the database
**Why it happens:** MySQL needs utf8mb4 charset for emoji (4-byte Unicode)
**How to avoid:** The schema already uses `utf8mb4`. Ensure SQL seed files are saved as UTF-8 and the MySQL connection uses `utf8mb4`. The existing seed file shows this works.
**Warning signs:** Garbled characters where emoji should be

### Pitfall 5: Missing Venue Research
**What goes wrong:** Incomplete venue list misses major cultural spaces
**Why it happens:** Buenos Aires has hundreds of cultural venues across many barrios. Easy to miss important ones.
**How to avoid:** Use multiple source categories: (1) Major museums (MALBA, MNBA, Moderno, MACBA), (2) Government cultural centers (CC Kirchner, CC Recoleta, Usina del Arte), (3) CTBA theaters (already seeded), (4) Independent theaters, (5) Art galleries, (6) Alternative/experimental spaces
**Warning signs:** Large barrios with zero venue coverage

## Code Examples

### Updating geocode.php for Buenos Aires
```php
// Replace NYC_BOUNDS with BA_BOUNDS
// Buenos Aires CABA bounding box (SW corner to NE corner)
define('BA_BOUNDS', '-34.75,-58.60|-34.50,-58.28');

// In geocode_address function, update the API call:
$url = 'https://maps.googleapis.com/maps/api/geocode/json?' . http_build_query([
    'address' => $query,
    'bounds' => BA_BOUNDS,       // Bias results toward Buenos Aires
    'region' => 'ar',            // Prefer Argentine results
    'components' => 'country:AR', // Restrict to Argentina
    'key' => $api_key,
]);
```

### SQL Seed File Template
```sql
-- Seed: [Category Name]
-- Source: [URL or data source]

USE fomo;

-- ============================================================================
-- LOCATIONS
-- ============================================================================

INSERT INTO locations (name, short_name, very_short_name, address, description, lat, lng, emoji) VALUES
('Venue Name', 'Short', 'VS', 'Address, CABA', 'Description in Spanish.', -34.XXXXXX, -58.XXXXXX, '🏛️');

-- ============================================================================
-- LOCATION ALTERNATE NAMES (if applicable)
-- ============================================================================

SET @venue_id = (SELECT id FROM locations WHERE name = 'Venue Name' LIMIT 1);

INSERT INTO location_alternate_names (location_id, alternate_name) VALUES
(@venue_id, 'Alternate Name');
```

### Coordinate Validation Check
```sql
-- Verify all locations fall within CITY_BOUNDS
SELECT name, lat, lng
FROM locations
WHERE lat < -34.75 OR lat > -34.50
   OR lng < -58.60 OR lng > -58.28;
-- Should return zero rows
```

### Running the Pipeline Export
```bash
# After inserting locations, regenerate JSON files
cd pipeline && python exporter.py
# Verify output
ls -la ../src/data/locations.*.json
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| NYC bounds in geocode.php | Needs update to BA bounds | Phase 2 task | geocode.php still has NYC_BOUNDS hardcoded |
| NYC venue data in DB | Cleared in Phase 1 | Phase 1 01-02 | Database is empty, ready for BA data |
| `add_locations.php` with hardcoded array | SQL seed files | Phase 2 pattern | Seed files are version-controllable and self-documenting |

**Note:** The `grantees` table is NYC-specific (NYSCA grants) and should be ignored for Phase 2. It may need cleanup in a future phase.

## Key Buenos Aires Venue Categories

Based on research, the following categories should be covered:

### Major Museums (HIGH priority)
- MALBA (Museo de Arte Latinoamericano de Buenos Aires)
- MNBA (Museo Nacional de Bellas Artes)
- Museo de Arte Moderno de Buenos Aires
- MACBA (Museo de Arte Contemporaneo de Buenos Aires)
- Museo Evita
- Casa Rosada Museum
- Museo Nacional de Arte Decorativo

### Government Cultural Centers (HIGH priority)
- Centro Cultural Kirchner (CCK)
- Centro Cultural Recoleta (CCR)
- Usina del Arte
- Centro Cultural San Martin (associated with Teatro San Martin, already seeded)

### Art Foundations (MEDIUM priority)
- Fundacion PROA
- Coleccion Fortabat (Amalia Lacroze de Fortabat)
- Fundacion Klemm

### Major Independent Theaters (MEDIUM priority)
- Teatro Colon (the opera house, distinct from CTBA)
- Teatro Metropolitan
- Teatro Gran Rex
- Teatro Maipo

### Gallery Districts (LOW priority - many small venues)
- Palermo galleries
- San Telmo galleries
- La Boca galleries

## Open Questions

1. **How many locations is the target?**
   - What we know: NYC had 1400+ locations built over time. Phase 2 is the initial seed.
   - What's unclear: Whether to aim for 30-50 key venues or try for comprehensive coverage
   - Recommendation: Start with 40-60 high-priority venues (museums, cultural centers, major theaters) and expand later. The existing seed has 6 (CTBA theaters).

2. **Should geocode.php be permanently updated or should it support city switching?**
   - What we know: The current script hardcodes NYC_BOUNDS. Phase 1 used city-agnostic naming (CITY_BOUNDS).
   - What's unclear: Whether to hardcode BA bounds or make it configurable
   - Recommendation: Simply replace NYC with BA bounds for now. The script is a utility, not production code. Add a `--region` flag if multi-city support is needed later.

3. **Where does the venue list come from?**
   - What we know: The user "has Buenos Aires event sources identified" (from additional context)
   - What's unclear: Whether venues should be researched by Claude or provided by the user
   - Recommendation: Plan should include a curated list of ~50 key venues based on public sources (official tourism sites, cultural directories). User can adjust.

4. **Should website_locations links be created in Phase 2?**
   - What we know: The CTBA seed file creates both locations AND website entries with website_locations links
   - What's unclear: Whether Phase 2 should only create locations, or also create website entries (which are needed for the crawl pipeline in Phase 3)
   - Recommendation: Phase 2 should focus on locations only (per requirements LOC-01, LOC-02, LOC-03). Website entries belong in Phase 3 (pipeline). However, if a venue's website URL is known, storing it via website_locations is harmless and saves Phase 3 effort.

## Sources

### Primary (HIGH confidence)
- `database/seeds/complejo_teatral_ba.sql` - Existing seed file pattern for BA venues
- `database/schema.sql` - Full database schema with all table definitions
- `scripts/geocode.php` - Existing geocoding script (NYC-biased)
- `scripts/add_locations.php` - Existing location insertion tool with ~1400 historical entries
- `pipeline/exporter.py` - Export logic with INIT_LAT_RANGE/INIT_LNG_RANGE for BA
- `src/js/script.js` lines 128-133 - CITY_BOUNDS configuration for BA

### Secondary (MEDIUM confidence)
- [Google Maps Geocoding API docs](https://developers.google.com/maps/documentation/geocoding/requests-geocoding) - bounds, region, components parameters
- [Buenos Aires Official Tourism - Museums & Cultural Centers](https://turismo.buenosaires.gob.ar/en/article/museums-art-galleries-and-cultural-centres) - Venue listing with addresses

### Tertiary (LOW confidence)
- [TripAdvisor BA Art Museums](https://www.tripadvisor.com/Attractions-g312741-Activities-c49-t28-Buenos_Aires_Capital_Federal_District.html) - Venue discovery (not verified individually)
- [Artforum Buenos Aires Guide](https://artguide.artforum.com/artguide/place/buenos-aires) - Gallery listings

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools already exist in codebase, just need BA-specific updates
- Architecture: HIGH - Seed file pattern is established, schema is locked (no changes per LOC-03)
- Pitfalls: HIGH - Geocoding and address format issues are well-documented; exporter bbox ranges are visible in code
- Venue list: MEDIUM - Major venues are well-known, but completeness depends on user's target scope

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain - venue data changes slowly)
