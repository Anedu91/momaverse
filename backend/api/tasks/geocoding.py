"""Celery task for async geocoding of locations."""

import asyncio
import logging
from typing import Any

import httpx
from sqlalchemy import select

from api.celery_app import celery
from api.config import get_settings
from api.database import AsyncSessionLocal
from api.models.location import Location
from api.services.geocoding import geocode_location_name
from api.task_names import GEOCODE_LOCATION

logger = logging.getLogger(__name__)


async def _geocode_location(location_id: int) -> None:
    """Fetch location, geocode it, and persist coordinates."""
    settings = get_settings()
    api_key = settings.geoapify_api_key
    if not api_key:
        logger.warning("Geoapify API key not configured, skipping geocoding")
        return

    async with AsyncSessionLocal() as session:
        location = await session.scalar(
            select(Location).where(Location.id == location_id)
        )
        if location is None:
            logger.warning("Location %d not found, skipping geocoding", location_id)
            return

        if location.lat is not None and location.lng is not None:
            logger.info("Location %d already has coordinates, skipping", location_id)
            return

        result = await geocode_location_name(
            location.name, api_key, address=location.address
        )

        if result is None:
            logger.info(
                "No geocoding result for location %d (%s)", location_id, location.name
            )
            return

        location.lat = result.lat
        location.lng = result.lng
        await session.commit()
        logger.info(
            "Geocoded location %d (%s) -> (%f, %f)",
            location_id,
            location.name,
            result.lat,
            result.lng,
        )


@celery.task(bind=True, name=GEOCODE_LOCATION, queue="geocoding")
def geocode_location(self: Any, location_id: int) -> None:
    """Geocode a location by ID. Retries on API errors with exponential backoff."""
    try:
        asyncio.run(_geocode_location(location_id))
    except httpx.HTTPError as exc:
        countdown = 2**self.request.retries * 30
        logger.warning(
            "Geocoding API error for location %d, retrying in %ds: %s",
            location_id,
            countdown,
            exc,
        )
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)
