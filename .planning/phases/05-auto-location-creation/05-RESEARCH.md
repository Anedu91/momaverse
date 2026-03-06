# Phase 5: Auto-Location Creation - Research

**Researched:** 2026-03-06
**Domain:** Pipeline location resolution from structured JSON API venue data
**Confidence:** HIGH

## Summary

This phase creates a `location_resolver.py` module that extracts unique venues from JSON API responses (structured data with name, address, lat/lng), deduplicates them against existing locations, and inserts new ones into the `locations` table. The module runs after crawl, before Gemini extraction, so that when `process_events()` calls `get_location_id()`, the newly created venues are already in the database and events match correctly.

The codebase is well-understood -- this is a self-contained addition that plugs into the existing pipeline between crawl and extraction. No external libraries are needed. The primary complexity is deduplication (name normalization + coordinate proximity) and the integration point in `main.py`.

**Primary recommendation:** Create a single `location_resolver.py` module with `resolve_locations(raw_json_data, website_id, cursor, connection)` that returns a count of created locations. Call it in `main.py` after `crawl_json_api()` succeeds but before extraction begins.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mysql.connector | (existing) | Database operations | Already used throughout pipeline |
| math | stdlib | Haversine distance for coordinate proximity | No external dependency needed |

### Supporting
No additional libraries required. All functionality uses Python stdlib + existing project patterns.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom Haversine | geopy.distance | Overkill for single-purpose ~100m proximity check; adds dependency |
| Direct SQL dedup | Python-side dedup | SQL could do it but Python gives more control over normalization logic |

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Project Structure
```
pipeline/
├── location_resolver.py  # NEW: venue extraction, dedup, creation
├── crawler.py             # Provides raw JSON data (crawl_json_api)
├── processor.py           # Consumes locations via get_location_id()
├── db.py                  # Add insert_location(), find_location_by_coords()
└── main.py                # Calls resolve_locations() between crawl and extract
```

### Pattern 1: Two-Phase Resolution (Extract then Dedup-Insert)

**What:** First extract all unique venues from the JSON response into a list of venue dicts. Then for each venue, check for duplicates (name match, coordinate proximity, alternate name) and only insert if no match found.

**When to use:** Always -- this is the core pattern for this module.

**Why two phases:** The JSON API response has venues nested inside events (`event > lugares > *`). Multiple events reference the same venue. Extracting unique venues first avoids redundant dedup checks.

```python
def resolve_locations(raw_json_data, website_id, cursor, connection):
    """Extract venues from JSON API data and create missing locations.

    Args:
        raw_json_data: Parsed JSON dict (post data_path navigation, pre-date-filter)
        website_id: Website ID for scoping alternate names
        cursor: Database cursor
        connection: Database connection

    Returns:
        Number of locations created
    """
    # Phase 1: Extract unique venues
    venues = extract_unique_venues(raw_json_data)

    # Phase 2: For each venue, dedup and insert
    created = 0
    for venue in venues:
        if not is_within_bounds(venue['lat'], venue['lng']):
            continue
        existing = find_existing_location(venue, cursor)
        if not existing:
            insert_location(venue, website_id, cursor, connection)
            created += 1

    return created
```

### Pattern 2: Dedup Cascade (Name -> Coords -> Alternate Names)

**What:** Three-tier deduplication strategy applied in order of cost/specificity.

**When to use:** For every venue being considered for insertion.

```python
def find_existing_location(venue, cursor):
    """Check if venue already exists using cascading dedup.

    Returns location dict if found, None otherwise.
    """
    normalized_name = normalize_venue_name(venue['name'])

    # Tier 1: Exact normalized name match
    # Reuse _normalize_location_name() from processor.py

    # Tier 2: Coordinate proximity (~100m)
    # Haversine distance check against all locations

    # Tier 3: Alternate name match (including website-scoped)

    return None  # No match found
```

### Pattern 3: Raw JSON Access (Before Date Filter)

**What:** The resolver needs the raw parsed JSON data before it gets filtered by date window and flattened to markdown. Venues exist in the full dataset, not just the date-filtered subset.

**When to use:** Always -- must process ALL venues from the API response, not just those with upcoming events.

**Critical insight:** `crawl_json_api()` currently parses JSON, navigates `data_path`, filters by date, and flattens to markdown. The resolver needs access to the data AFTER `data_path` navigation but BEFORE date filtering, because a venue might only appear on past events but still be valid for future events from other sources.

**Implementation approach:** Either:
- (A) Re-parse the raw JSON in the resolver (fetch from raw response text stored elsewhere) -- complex, duplicates work
- (B) Have `crawl_json_api()` return the raw parsed data alongside the crawl_result_id -- clean but changes return signature
- (C) Parse the JSON independently in the resolver by fetching the API URL again -- wasteful
- (D) Store raw JSON in a field on crawl_results, resolver reads it back -- adds DB column

**Recommended: Option B** -- have `crawl_json_api()` return `(crawl_result_id, raw_data_dict)` where `raw_data_dict` is the data after `data_path` navigation but before date filtering. The caller in `main.py` passes this to the resolver.

### Anti-Patterns to Avoid
- **Running resolver after Gemini extraction:** Gemini output has venue names as free text, not structured data. The whole point is to use structured JSON API data with coordinates.
- **Creating locations from ALL JSON API events, including those outside date window:** While venues should be extracted from the full dataset, this creates noise. However, a venue existing in the API but only for past events should still be created -- it may be needed for future events. Extract from full data, but filter by bounds.
- **Re-fetching the API URL:** The data is already fetched by `crawl_json_api()`. Don't make a second HTTP request.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Name normalization | New normalization function | `processor._normalize_location_name()` | Already handles lowercase, stripping "the", removing punctuation |
| Venue name title-casing | New title case function | `processor.normalize_event_name_caps()` | Already handles caps->title with smart rules (already exists, battle-tested) |
| Location querying | New SQL query | `db.get_all_locations()` | Already returns all locations with alternate names, website-scoped names |
| Bounds checking | New bounds logic | Reuse constants from ROADMAP (lat: -34.75 to -34.50, lng: -58.60 to -58.28) | Same bounds used in frontend `CITY_BOUNDS` |

**Key insight:** The existing `build_locations_map()` in processor.py creates a comprehensive lookup structure. The resolver should call this same function to build its dedup lookup, ensuring consistency with how `get_location_id()` later matches events.

## Common Pitfalls

### Pitfall 1: Venue Name Case Mismatch
**What goes wrong:** Alternativa Teatral API returns venue names in ALL CAPS (e.g., "TEATRO EL PICADERO") while the locations table stores title case ("Teatro El Picadero"). If not normalized, dedup fails and duplicates are created.
**Why it happens:** Different data sources use different casing conventions.
**How to avoid:** Normalize BOTH sides (API venue name AND existing location name) using `_normalize_location_name()` before comparing. Store the title-cased version in the DB (use `normalize_event_name_caps()` to convert from ALL CAPS).
**Warning signs:** Location count growing every crawl run; same venue appearing twice on map.

### Pitfall 2: Coordinate Precision and Proximity Threshold
**What goes wrong:** Two sources report slightly different coordinates for the same venue. A too-tight threshold misses matches; a too-loose threshold incorrectly merges distinct venues in the same building.
**Why it happens:** GPS coordinates vary by source. Multiple theaters can share the same building (e.g., same address, different floors).
**How to avoid:** Use ~100m (0.001 degrees latitude is ~111m at Buenos Aires latitude) as initial threshold. When coordinates match but names don't match at all, prefer name mismatch -- don't merge. Coordinate proximity should be a secondary signal, not a primary one.
**Warning signs:** Distinct venues merged into one; or same venue duplicated with slightly different coords.

### Pitfall 3: Running Resolver on Date-Filtered Data
**What goes wrong:** If resolver only sees venues from date-filtered events, venues that only appear on past events are missed. When a new event at that venue appears in a future crawl, the venue won't exist yet.
**Why it happens:** `crawl_json_api()` filters events by date window before flattening to markdown.
**How to avoid:** Resolver must access the FULL API data (post data_path, pre-date-filter). This is why Option B (return raw data from crawl_json_api) is recommended.
**Warning signs:** Events appearing without map positions on subsequent crawl runs.

### Pitfall 4: Race Condition with Existing Locations Map
**What goes wrong:** `process_events()` calls `build_locations_map()` which queries the DB. If the resolver creates locations but `build_locations_map()` was called before the resolver ran, the new locations won't be in the map.
**How to avoid:** The resolver MUST run before `process_events()`. The pipeline flow is: crawl -> resolve locations -> extract -> process. Since extract is async and process happens after, this naturally works if the resolver runs right after crawl and before extraction begins.
**Warning signs:** Events processed with `location_id = NULL` despite venue existing in locations table.

### Pitfall 5: Duplicate Alternate Names
**What goes wrong:** If the API venue name is already the canonical name in the locations table, inserting it as an alternate name creates redundancy. If the resolver runs multiple times (re-crawls), it might insert duplicate alternate names.
**How to avoid:** Check if the API venue name matches the canonical name before inserting as alternate name. Use `INSERT IGNORE` or check for existence before inserting alternate names.
**Warning signs:** `location_alternate_names` table growing with duplicate entries.

### Pitfall 6: Venues with NULL or Zero Coordinates
**What goes wrong:** Some API venues may have lat=0, lng=0 or NULL coordinates. These would fail bounds checking but could also cause errors if not explicitly handled.
**Why it happens:** Not all API venues have geocoded positions.
**How to avoid:** Skip venues where lat or lng is None, 0, or not a valid number. Log skipped venues for visibility.
**Warning signs:** Errors during float conversion; venues at (0,0) on the map.

## Code Examples

### Haversine Distance for Coordinate Proximity
```python
import math

def haversine_distance_meters(lat1, lng1, lat2, lng2):
    """Calculate distance between two points in meters using Haversine formula."""
    R = 6371000  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

PROXIMITY_THRESHOLD_METERS = 100
```

### Extracting Unique Venues from API Response
```python
def extract_unique_venues(events_dict):
    """Extract unique venues from Alternativa Teatral JSON response.

    API structure: events_dict[event_id]['lugares'][lugar_id] = {
        'nombre': 'TEATRO EL PICADERO',
        'direccion': 'Pasaje Enrique Santos Discepolo 1857',
        'zona': 'Abasto',
        'lat': '-34.602900',
        'lng': '-58.397700'
    }

    Returns list of venue dicts with normalized fields.
    """
    seen_lugar_ids = set()
    venues = []

    for event_id, event in events_dict.items():
        lugares = event.get('lugares', {})
        if not isinstance(lugares, dict):
            continue
        for lugar_id, lugar in lugares.items():
            if lugar_id in seen_lugar_ids:
                continue
            seen_lugar_ids.add(lugar_id)

            nombre = lugar.get('nombre', '').strip()
            if not nombre:
                continue

            try:
                lat = float(lugar.get('lat', 0))
                lng = float(lugar.get('lng', 0))
            except (ValueError, TypeError):
                continue

            if lat == 0 or lng == 0:
                continue

            venues.append({
                'api_id': lugar_id,
                'name': nombre,
                'address': lugar.get('direccion', '').strip(),
                'zona': lugar.get('zona', '').strip(),
                'lat': lat,
                'lng': lng,
            })

    return venues
```

### Bounds Checking
```python
# Buenos Aires map bounds (from src/js/script.js CITY_BOUNDS)
BA_BOUNDS = {
    'lat_min': -34.75,
    'lat_max': -34.50,
    'lng_min': -58.60,
    'lng_max': -58.28,
}

def is_within_bounds(lat, lng):
    """Check if coordinates fall within Buenos Aires map bounds."""
    return (BA_BOUNDS['lat_min'] <= lat <= BA_BOUNDS['lat_max'] and
            BA_BOUNDS['lng_min'] <= lng <= BA_BOUNDS['lng_max'])
```

### Insert Location with Alternate Name
```python
def insert_location(venue, website_id, cursor, connection):
    """Insert a new location and optionally a website-scoped alternate name.

    Stores title-cased name from API. If the API name differs from the
    title-cased version, stores original as website-scoped alternate name.
    """
    # Title-case the ALL CAPS name from API
    display_name = normalize_venue_name_for_display(venue['name'])

    # Build address: "direccion, zona" if zona exists
    address_parts = [venue['address']]
    if venue.get('zona'):
        address_parts.append(venue['zona'])
    address = ', '.join(p for p in address_parts if p)

    cursor.execute(
        """INSERT INTO locations (name, address, lat, lng, emoji)
           VALUES (%s, %s, %s, %s, %s)""",
        (display_name, address, venue['lat'], venue['lng'], '📍')
    )
    location_id = cursor.lastrowid

    # Add website-scoped alternate name if API name differs from display name
    api_name_lower = venue['name'].lower().strip()
    display_lower = display_name.lower().strip()
    if api_name_lower != display_lower:
        cursor.execute(
            """INSERT INTO location_alternate_names
               (location_id, alternate_name, website_id)
               VALUES (%s, %s, %s)""",
            (location_id, venue['name'], website_id)
        )

    connection.commit()
    return location_id
```

### Integration Point in main.py
```python
# In main.py, after JSON API crawl, before extraction:

# Crawl JSON API websites (fast, no browser needed)
if json_api_websites:
    for website in json_api_websites:
        # crawl_json_api returns (crawl_result_id, raw_data)
        result_id, raw_data = await crawler.crawl_json_api(website, cur, conn, crawl_run_id)
        if result_id and raw_data:
            # Resolve locations BEFORE extraction
            import location_resolver
            created = location_resolver.resolve_locations(
                raw_data, website['id'], cur, conn
            )
            if created > 0:
                print(f"    - Created {created} new location(s)")
            crawl_results.append((result_id, website))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual location seeding via SQL files | Auto-creation from structured API data | Phase 5 (this phase) | 53+ venues auto-created instead of manual SQL |
| All venue matching at process time | Pre-create venues at crawl time | Phase 5 (this phase) | Higher match rate in processor |

**Key fields in Alternativa Teatral API venue data:**
- `nombre` -- venue name (ALL CAPS)
- `direccion` -- street address
- `zona` -- neighborhood/zone
- `lat` -- latitude as string
- `lng` -- longitude as string
- `funciones` -- nested dict of showtimes (not needed for location creation)

## Open Questions

1. **Default emoji for auto-created locations**
   - What we know: Existing seed files use category-specific emojis (theaters: `🎭`, museums: `🏛️`, etc.)
   - What's unclear: Should auto-created venues default to `🎭` (since Alternativa Teatral is theater-focused) or a generic marker `📍`?
   - Recommendation: Use `🎭` for Alternativa Teatral (the source is exclusively theater). Could add `default_emoji` to `json_api_config` for future sources.

2. **Should resolver create short_name and very_short_name?**
   - What we know: Existing locations have `short_name` and `very_short_name` fields. Seed files set these manually.
   - What's unclear: Whether auto-created locations need these or can leave them NULL.
   - Recommendation: Leave NULL initially. These are display optimization fields that can be populated later. The core matching uses `name` and `alternate_names`.

3. **Re-crawl behavior: update existing location coordinates?**
   - What we know: API coordinates might change slightly between crawls. Locations are identified by name match.
   - What's unclear: Should we update lat/lng on re-crawl if coordinates differ?
   - Recommendation: Don't update on re-crawl. Once created, coordinates are fixed. Manual corrections via admin should persist.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `pipeline/crawler.py` lines 60-158 (JSON API response structure, venue fields: nombre, direccion, zona, lat, lng)
- Codebase analysis: `pipeline/processor.py` lines 418-747 (location matching: _normalize_location_name, build_locations_map, get_location_id)
- Codebase analysis: `pipeline/db.py` lines 514-557 (get_all_locations query structure)
- Codebase analysis: `database/schema.sql` lines 14-31 (locations table schema)
- Codebase analysis: `database/schema.sql` lines 104-115 (location_alternate_names schema)
- Codebase analysis: `database/seeds/teatros_ba.sql` (seed file format with INSERT INTO locations)
- Codebase analysis: `src/js/script.js` lines 128-132 (CITY_BOUNDS: lat -34.75 to -34.50, lng -58.60 to -58.28)
- Codebase analysis: `pipeline/main.py` lines 140-156 (JSON API crawl integration point)

### Secondary (MEDIUM confidence)
- ROADMAP.md Phase 5 description (design intent, dedup strategy, success criteria)

### Tertiary (LOW confidence)
- None -- this is entirely an internal codebase integration

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no external libraries needed, all patterns exist in codebase
- Architecture: HIGH -- pipeline flow, DB schema, and API data structure fully analyzed
- Pitfalls: HIGH -- derived from concrete code analysis (name casing, coordinate precision, pipeline ordering)

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable -- internal codebase, no external API changes expected)
