"""
Location Resolver Module

Extracts unique venues from JSON API structured data, deduplicates against
existing locations, and auto-creates missing venues in the locations table.

Runs after JSON API crawl, before Gemini extraction, so that get_location_id()
can match events to the newly created locations via website-scoped alternate names.
"""

import math

import db
from processor import _normalize_location_name, normalize_event_name_caps

# Buenos Aires geographic bounds -- venues outside these are skipped
BA_BOUNDS = {"lat_min": -34.75, "lat_max": -34.50, "lng_min": -58.60, "lng_max": -58.28}

# Proximity threshold for coordinate-based deduplication
PROXIMITY_THRESHOLD_METERS = 100


def _haversine_meters(lat1, lng1, lat2, lng2):
    """Calculate distance in meters between two lat/lng points using haversine formula."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def resolve_locations(raw_json_data, website_id, cursor, connection):
    """Resolve and auto-create missing venue locations from JSON API data.

    Extracts unique venues from the raw API response, checks for duplicates
    against existing locations (by normalized name and coordinate proximity),
    and inserts new locations with website-scoped alternate names.

    Args:
        raw_json_data: Parsed JSON dict -- events keyed by event ID, each with
                       lugares > lugar_id > {nombre, direccion, zona, lat, lng}
        website_id: Website ID for scoping alternate names
        cursor: Database cursor
        connection: Database connection

    Returns:
        int: Count of locations created
    """
    if not isinstance(raw_json_data, dict):
        return 0

    # Step 1: Extract unique venues from raw JSON data
    unique_venues = {}
    for event_id, event in raw_json_data.items():
        lugares = event.get("lugares", {})
        if not isinstance(lugares, dict):
            continue
        for lugar_id, lugar in lugares.items():
            if lugar_id in unique_venues:
                continue

            nombre = lugar.get("nombre", "").strip()
            if not nombre:
                continue

            # Parse lat/lng, skip if missing or zero
            try:
                lat = float(lugar.get("lat", 0))
                lng = float(lugar.get("lng", 0))
            except TypeError, ValueError:
                continue

            if lat == 0.0 or lng == 0.0:
                continue

            unique_venues[lugar_id] = {
                "nombre": nombre,
                "direccion": lugar.get("direccion", "").strip(),
                "zona": lugar.get("zona", "").strip(),
                "lat": lat,
                "lng": lng,
            }

    if not unique_venues:
        return 0

    print(f"  Resolving locations from {len(unique_venues)} unique venues...")

    # Step 2: Load existing locations for dedup
    existing_locations = db.get_all_locations(cursor)

    existing_names = set()
    for loc in existing_locations:
        loc_name = loc.get("name", "")
        normalized = _normalize_location_name(loc_name)
        if normalized:
            existing_names.add(normalized)
        # Also add alternate names
        for alt_name in loc.get("alternate_names", []):
            normalized_alt = _normalize_location_name(alt_name)
            if normalized_alt:
                existing_names.add(normalized_alt)
        # And website-scoped alternate names
        for ws_id, scoped_names in loc.get("website_scoped_names", {}).items():
            for alt_name in scoped_names:
                normalized_alt = _normalize_location_name(alt_name)
                if normalized_alt:
                    existing_names.add(normalized_alt)

    existing_coords = [
        (loc.get("lat"), loc.get("lng"))
        for loc in existing_locations
        if loc.get("lat") is not None and loc.get("lng") is not None
    ]

    # Step 3: Process each venue
    created_count = 0
    skipped_bounds = 0
    skipped_existing = 0

    for lugar_id, venue in unique_venues.items():
        lat, lng = venue["lat"], venue["lng"]

        # Buenos Aires bounds check
        if not (
            BA_BOUNDS["lat_min"] <= lat <= BA_BOUNDS["lat_max"]
            and BA_BOUNDS["lng_min"] <= lng <= BA_BOUNDS["lng_max"]
        ):
            skipped_bounds += 1
            continue

        # Name normalization
        display_name = normalize_event_name_caps(venue["nombre"])
        normalized_name = _normalize_location_name(display_name)

        # Dedup: normalized name match
        if normalized_name and normalized_name in existing_names:
            skipped_existing += 1
            continue

        # Dedup: coordinate proximity (100m)
        too_close = False
        for existing_lat, existing_lng in existing_coords:
            if (
                _haversine_meters(lat, lng, existing_lat, existing_lng)
                < PROXIMITY_THRESHOLD_METERS
            ):
                too_close = True
                skipped_existing += 1
                break
        if too_close:
            continue

        # Build address string
        address_parts = [venue["direccion"]]
        if venue["zona"]:
            address_parts.append(venue["zona"])
        address = ", ".join(p for p in address_parts if p)

        # Insert new location
        cursor.execute(
            """INSERT INTO locations (name, address, lat, lng, emoji)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id""",
            (display_name, address, lat, lng, "\U0001f3ad"),
        )
        new_location_id = cursor.fetchone()[0]

        # Insert website-scoped alternate name (original API name for processor matching)
        cursor.execute(
            """INSERT INTO location_alternate_names (location_id, alternate_name, website_id)
               VALUES (%s, %s, %s)""",
            (new_location_id, venue["nombre"], website_id),
        )

        # Update tracking sets for batch dedup
        if normalized_name:
            existing_names.add(normalized_name)
        existing_coords.append((lat, lng))

        created_count += 1

    # Commit all inserts at once
    connection.commit()

    print(
        f"    - Created {created_count} new location(s), skipped {skipped_existing} existing, {skipped_bounds} outside BA bounds"
    )

    return created_count
