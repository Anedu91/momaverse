"""Tests for the geocoding service."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from api.services.geocoding import (
    GeocodingResult,
    geocode_location_name,
    haversine_meters,
    is_within_buenos_aires,
)

# -- Unit tests for pure functions --


class TestIsWithinBuenosAires:
    def test_inside(self):
        assert is_within_buenos_aires(-34.61, -58.44) is True

    def test_outside_north(self):
        assert is_within_buenos_aires(-34.40, -58.44) is False

    def test_outside_east(self):
        assert is_within_buenos_aires(-34.61, -58.20) is False

    def test_on_boundary(self):
        assert is_within_buenos_aires(-34.75, -58.60) is True


class TestHaversineMeters:
    def test_same_point(self):
        assert haversine_meters(-34.61, -58.44, -34.61, -58.44) == pytest.approx(
            0.0, abs=0.01
        )

    def test_known_distance(self):
        # Obelisco (-34.6037, -58.3816) to Teatro Colón (-34.6011, -58.3830)
        dist = haversine_meters(-34.6037, -58.3816, -34.6011, -58.3830)
        assert 200 < dist < 400  # ~310m


# -- Async tests for geocode_location_name --


def _mock_geoapify_response(
    lat: float = -34.6037,
    lon: float = -58.3816,
    formatted: str = "Obelisco, Buenos Aires",
    confidence: float = 0.9,
) -> dict[str, object]:
    return {
        "results": [
            {
                "lat": lat,
                "lon": lon,
                "formatted": formatted,
                "rank": {"confidence": confidence},
            }
        ]
    }


@pytest.mark.asyncio
class TestGeocodeLocationName:
    async def test_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = _mock_geoapify_response()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "api.services.geocoding.httpx.AsyncClient", return_value=mock_client
        ):
            result = await geocode_location_name("Obelisco", "fake-key")

        assert result is not None
        assert isinstance(result, GeocodingResult)
        assert result.lat == pytest.approx(-34.6037)
        assert result.lng == pytest.approx(-58.3816)
        assert result.formatted_address == "Obelisco, Buenos Aires"
        assert result.confidence == pytest.approx(0.9)

    async def test_no_results(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "api.services.geocoding.httpx.AsyncClient", return_value=mock_client
        ):
            result = await geocode_location_name("Nonexistent Place", "fake-key")

        assert result is None

    async def test_http_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "api.services.geocoding.httpx.AsyncClient", return_value=mock_client
        ):
            result = await geocode_location_name("Some Place", "fake-key")

        assert result is None

    async def test_outside_buenos_aires(self):
        mock_response = MagicMock()
        mock_response.json.return_value = _mock_geoapify_response(
            lat=40.7128,
            lon=-74.0060,  # New York
        )
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "api.services.geocoding.httpx.AsyncClient", return_value=mock_client
        ):
            result = await geocode_location_name("Statue of Liberty", "fake-key")

        assert result is None

    async def test_with_address(self):
        mock_response = MagicMock()
        mock_response.json.return_value = _mock_geoapify_response()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "api.services.geocoding.httpx.AsyncClient", return_value=mock_client
        ):
            result = await geocode_location_name(
                "Teatro Colón", "fake-key", address="Cerrito 628, CABA"
            )

        assert result is not None
        # Verify the search text used the address
        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert "Cerrito 628" in params["text"]
