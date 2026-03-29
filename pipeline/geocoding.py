"""Synchronous Geoapify geocoding for Buenos Aires venue resolution.

Ported from backend/api/services/geocoding.py (async) to synchronous
for use in the pipeline's event processor.
"""

import os
from dataclasses import dataclass

import httpx

# Buenos Aires bounding box
BA_BOUNDS = {
    "lat_min": -34.75,
    "lat_max": -34.50,
    "lng_min": -58.60,
    "lng_max": -58.28,
}

BA_CENTER = {"lat": -34.61, "lng": -58.44}

GEOAPIFY_SEARCH_URL = "https://api.geoapify.com/v1/geocode/search"


@dataclass
class GeocodingResult:
    lat: float
    lng: float
    formatted_address: str
    confidence: float


def is_within_buenos_aires(lat: float, lng: float) -> bool:
    """Check if coordinates fall within Buenos Aires bounds."""
    return (
        BA_BOUNDS["lat_min"] <= lat <= BA_BOUNDS["lat_max"]
        and BA_BOUNDS["lng_min"] <= lng <= BA_BOUNDS["lng_max"]
    )


def geocode_location_name(
    name: str,
    api_key: str | None = None,
    *,
    client: httpx.Client | None = None,
) -> GeocodingResult | None:
    """Forward-geocode a venue name via Geoapify, biased to Buenos Aires.

    Returns None if no result found, API call fails, or result is outside BA.
    If *client* is provided it will be reused; otherwise a new one is created.
    If *api_key* is None, reads from GEOAPIFY_API_KEY environment variable.
    """
    if api_key is None:
        api_key = os.environ.get("GEOAPIFY_API_KEY")
    if not api_key:
        return None

    search_text = f"{name}, Buenos Aires"
    params: dict[str, str | int] = {
        "text": search_text,
        "filter": (
            f"rect:{BA_BOUNDS['lng_min']},{BA_BOUNDS['lat_min']},"
            f"{BA_BOUNDS['lng_max']},{BA_BOUNDS['lat_max']}"
        ),
        "bias": f"proximity:{BA_CENTER['lng']},{BA_CENTER['lat']}",
        "type": "amenity",
        "format": "json",
        "limit": 1,
        "apiKey": api_key,
    }

    try:
        if client is not None:
            resp = client.get(GEOAPIFY_SEARCH_URL, params=params)
            resp.raise_for_status()
        else:
            with httpx.Client(timeout=10.0) as _client:
                resp = _client.get(GEOAPIFY_SEARCH_URL, params=params)
                resp.raise_for_status()
        data: dict[str, object] = resp.json()
    except httpx.HTTPError:
        return None

    results = data.get("results")
    if not isinstance(results, list) or not results:
        return None

    hit = results[0]
    if not isinstance(hit, dict):
        return None

    lat = hit.get("lat")
    lon = hit.get("lon")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return None

    if not is_within_buenos_aires(float(lat), float(lon)):
        return None

    rank = hit.get("rank", {})
    confidence = rank.get("confidence", 0.0) if isinstance(rank, dict) else 0.0
    formatted = hit.get("formatted", "")

    return GeocodingResult(
        lat=float(lat),
        lng=float(lon),
        formatted_address=str(formatted),
        confidence=float(confidence),
    )
