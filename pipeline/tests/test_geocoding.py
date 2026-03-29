"""Tests for geocoding.py synchronous geocoding module."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from geocoding import GeocodingResult, geocode_location_name, is_within_buenos_aires


class TestIsWithinBuenosAires(unittest.TestCase):
    """Tests for is_within_buenos_aires bounds check."""

    def test_valid_ba_coordinates(self):
        self.assertTrue(is_within_buenos_aires(-34.61, -58.44))

    def test_out_of_bounds_north(self):
        self.assertFalse(is_within_buenos_aires(-34.40, -58.44))

    def test_out_of_bounds_south(self):
        self.assertFalse(is_within_buenos_aires(-34.80, -58.44))

    def test_out_of_bounds_east(self):
        self.assertFalse(is_within_buenos_aires(-34.61, -58.20))

    def test_out_of_bounds_west(self):
        self.assertFalse(is_within_buenos_aires(-34.61, -58.70))

    def test_edge_min(self):
        self.assertTrue(is_within_buenos_aires(-34.75, -58.60))

    def test_edge_max(self):
        self.assertTrue(is_within_buenos_aires(-34.50, -58.28))


class TestGeocodeLocationName(unittest.TestCase):
    """Tests for geocode_location_name function."""

    VALID_RESPONSE = {
        "results": [
            {
                "lat": -34.61,
                "lon": -58.44,
                "formatted": "Café Tortoni, Av. de Mayo 825, Buenos Aires",
                "rank": {"confidence": 0.9},
            }
        ]
    }

    def _mock_response(self, json_data, status_code=200):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.json.return_value = json_data
        resp.raise_for_status.return_value = None
        return resp

    @patch("geocoding.httpx.Client")
    def test_successful_geocode(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._mock_response(self.VALID_RESPONSE)

        result = geocode_location_name("Café Tortoni", api_key="test-key")

        self.assertIsNotNone(result)
        self.assertIsInstance(result, GeocodingResult)
        self.assertAlmostEqual(result.lat, -34.61)
        self.assertAlmostEqual(result.lng, -58.44)
        self.assertEqual(
            result.formatted_address, "Café Tortoni, Av. de Mayo 825, Buenos Aires"
        )
        self.assertAlmostEqual(result.confidence, 0.9)

    @patch("geocoding.httpx.Client")
    def test_returns_none_on_http_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        result = geocode_location_name("Some Venue", api_key="test-key")
        self.assertIsNone(result)

    @patch("geocoding.httpx.Client")
    def test_returns_none_on_empty_results(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._mock_response({"results": []})

        result = geocode_location_name("Nonexistent Place", api_key="test-key")
        self.assertIsNone(result)

    @patch("geocoding.httpx.Client")
    def test_returns_none_on_out_of_bounds(self, mock_client_cls):
        out_of_bounds_response = {
            "results": [
                {
                    "lat": 40.71,  # New York
                    "lon": -74.00,
                    "formatted": "New York, NY",
                    "rank": {"confidence": 0.8},
                }
            ]
        }
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._mock_response(out_of_bounds_response)

        result = geocode_location_name("Some Place", api_key="test-key")
        self.assertIsNone(result)

    @patch.dict(os.environ, {"GEOAPIFY_API_KEY": "env-key"})
    @patch("geocoding.httpx.Client")
    def test_uses_env_api_key(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._mock_response(self.VALID_RESPONSE)

        result = geocode_location_name("Café Tortoni")
        self.assertIsNotNone(result)

        # Verify API key was passed in params
        call_kwargs = mock_client.get.call_args
        params = (
            call_kwargs[1]["params"]
            if "params" in call_kwargs[1]
            else call_kwargs[0][1]
        )
        self.assertEqual(params["apiKey"], "env-key")

    def test_reuses_provided_client(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = self._mock_response(self.VALID_RESPONSE)

        result = geocode_location_name(
            "Café Tortoni", api_key="test-key", client=mock_client
        )

        self.assertIsNotNone(result)
        mock_client.get.assert_called_once()

    def test_returns_none_when_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            result = geocode_location_name("Some Venue")
        self.assertIsNone(result)

    @patch("geocoding.httpx.Client")
    def test_returns_none_on_missing_lat_lon(self, mock_client_cls):
        response = {
            "results": [{"formatted": "Some Place", "rank": {"confidence": 0.5}}]
        }
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._mock_response(response)

        result = geocode_location_name("Some Place", api_key="test-key")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
