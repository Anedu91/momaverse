"""Geoapify geocoding service for Buenos Aires venue resolution (synchronous).

Synchronous counterpart to backend/api/services/geocoding.py, designed for
the pipeline's non-async execution model.
"""

import logging
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Buenos Aires geographic bounds — same values as location_resolver.BA_BOUNDS
BA_BOUNDS = {"lat_min": -34.75, "lat_max": -34.50, "lng_min": -58.60, "lng_max": -58.28}
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


def _parse_first_result(data: dict[str, object], name: str) -> GeocodingResult | None:
    """Extract and validate the first geocoding result from a Geoapify response."""
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

    lat_f, lon_f = float(lat), float(lon)

    if not is_within_buenos_aires(lat_f, lon_f):
        logger.info(
            "Geocode result for %r is outside Buenos Aires: lat=%s, lon=%s",
            name,
            lat_f,
            lon_f,
        )
        return None

    rank = hit.get("rank", {})
    confidence_raw = rank.get("confidence", 0.0) if isinstance(rank, dict) else 0.0
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0

    return GeocodingResult(
        lat=lat_f,
        lng=lon_f,
        formatted_address=str(hit.get("formatted", "")),
        confidence=confidence,
    )


def geocode_location_name(
    name: str,
    api_key: str,
    *,
    address: str | None = None,
    client: httpx.Client | None = None,
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

    own_client = client is None
    http_client = httpx.Client(timeout=10.0) if own_client else client
    assert http_client is not None  # for mypy

    try:
        resp = http_client.get(GEOAPIFY_SEARCH_URL, params=params)
        resp.raise_for_status()
    except httpx.HTTPError:
        logger.warning("Geocoding failed for %r", name, exc_info=True)
        return None
    finally:
        if own_client:
            http_client.close()

    try:
        data = resp.json()
    except ValueError:
        logger.warning("Invalid JSON response for %r", name, exc_info=True)
        return None
    if not isinstance(data, dict):
        logger.warning(
            "Unexpected geocoding payload type for %r: %s",
            name,
            type(data).__name__,
        )
        return None

    return _parse_first_result(data, name)
