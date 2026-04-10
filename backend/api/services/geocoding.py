"""Geoapify geocoding service for Buenos Aires venue resolution."""

import math
import re
from dataclasses import dataclass

import httpx

# Buenos Aires bounding box (ported from pipeline/location_resolver.py)
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


def normalize_location_name(name: str) -> str:
    """Normalize a location name for dedup matching.

    Ported from pipeline/processor.py::_normalize_location_name.
    """
    if not name:
        return ""
    normalized = re.sub(r"[^\w\s]", "", name.lower())
    return " ".join(normalized.split())


def is_within_buenos_aires(lat: float, lng: float) -> bool:
    """Check if coordinates fall within Buenos Aires bounds."""
    return (
        BA_BOUNDS["lat_min"] <= lat <= BA_BOUNDS["lat_max"]
        and BA_BOUNDS["lng_min"] <= lng <= BA_BOUNDS["lng_max"]
    )


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in meters between two lat/lng points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def geocode_location_name(
    name: str,
    api_key: str,
    *,
    address: str | None = None,
    client: httpx.AsyncClient | None = None,
    propagate_http_errors: bool = False,
) -> GeocodingResult | None:
    """Forward-geocode a venue name via Geoapify, biased to Buenos Aires.

    Returns None if no result found, API call fails, or result is outside BA.
    If *client* is provided it will be reused; otherwise a new one is created.
    """
    search_text = f"{name}, {address}" if address else f"{name}, Buenos Aires"
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
            resp = await client.get(GEOAPIFY_SEARCH_URL, params=params)
            resp.raise_for_status()
        else:
            async with httpx.AsyncClient(timeout=10.0) as _client:
                resp = await _client.get(GEOAPIFY_SEARCH_URL, params=params)
                resp.raise_for_status()
        data: dict[str, object] = resp.json()
    except httpx.HTTPError:
        if propagate_http_errors:
            raise
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
