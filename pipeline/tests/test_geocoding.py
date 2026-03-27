"""Tests for pipeline geocoding module."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import httpx

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geocoding import GeocodingResult, geocode_location_name, is_within_buenos_aires


class TestIsWithinBuenosAires(unittest.TestCase):
    """Tests for the BA bounds check."""

    def test_inside_ba(self):
        # Palermo, Buenos Aires
        self.assertTrue(is_within_buenos_aires(-34.58, -58.43))

    def test_outside_ba_north(self):
        # Too far north
        self.assertFalse(is_within_buenos_aires(-34.40, -58.43))

    def test_outside_ba_south(self):
        # Too far south
        self.assertFalse(is_within_buenos_aires(-34.80, -58.43))

    def test_outside_ba_east(self):
        # Too far east
        self.assertFalse(is_within_buenos_aires(-34.60, -58.20))

    def test_outside_ba_west(self):
        # Too far west
        self.assertFalse(is_within_buenos_aires(-34.60, -58.70))

    def test_on_boundary(self):
        # Exact boundary should be included
        self.assertTrue(is_within_buenos_aires(-34.75, -58.60))
        self.assertTrue(is_within_buenos_aires(-34.50, -58.28))

    def test_nyc_coordinates(self):
        self.assertFalse(is_within_buenos_aires(40.73, -74.0))


class TestGeocodeLocationName(unittest.TestCase):
    """Tests for the synchronous geocoding function."""

    VALID_BA_RESPONSE = {
        "results": [
            {
                "lat": -34.60,
                "lon": -58.40,
                "formatted": "Av. Corrientes 1234, Buenos Aires",
                "rank": {"confidence": 0.85},
            }
        ]
    }

    def _mock_response(self, json_data, status_code=200):
        """Create a mock httpx.Response."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.json.return_value = json_data
        resp.raise_for_status.return_value = None
        if status_code >= 400:
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "error", request=MagicMock(), response=resp
            )
        return resp

    def test_geocode_success(self):
        """Valid BA result returns GeocodingResult with correct fields."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = self._mock_response(self.VALID_BA_RESPONSE)

        result = geocode_location_name("Teatro Colón", "test-key", client=client)

        self.assertIsNotNone(result)
        assert result is not None  # for mypy
        self.assertAlmostEqual(result.lat, -34.60)
        self.assertAlmostEqual(result.lng, -58.40)
        self.assertEqual(result.formatted_address, "Av. Corrientes 1234, Buenos Aires")
        self.assertAlmostEqual(result.confidence, 0.85)

    def test_geocode_uses_address_in_search_text(self):
        """When address is provided, search text includes it instead of 'Buenos Aires'."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = self._mock_response(self.VALID_BA_RESPONSE)

        geocode_location_name(
            "Teatro Colón", "test-key", address="Av. Corrientes 1234", client=client
        )

        call_args = client.get.call_args
        params = call_args[1]["params"]
        self.assertEqual(params["text"], "Teatro Colón, Av. Corrientes 1234")

    def test_geocode_default_search_text(self):
        """Without address, search text appends 'Buenos Aires'."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = self._mock_response(self.VALID_BA_RESPONSE)

        geocode_location_name("Teatro Colón", "test-key", client=client)

        call_args = client.get.call_args
        params = call_args[1]["params"]
        self.assertEqual(params["text"], "Teatro Colón, Buenos Aires")

    def test_geocode_no_results(self):
        """Empty results list returns None."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = self._mock_response({"results": []})

        result = geocode_location_name("Nonexistent Place", "test-key", client=client)
        self.assertIsNone(result)

    def test_geocode_http_error(self):
        """HTTP error returns None without raising."""
        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = httpx.ConnectError("connection refused")

        result = geocode_location_name("Some Venue", "test-key", client=client)
        self.assertIsNone(result)

    def test_geocode_timeout(self):
        """Timeout returns None without raising."""
        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = httpx.TimeoutException("timed out")

        result = geocode_location_name("Some Venue", "test-key", client=client)
        self.assertIsNone(result)

    def test_geocode_http_status_error(self):
        """Non-200 status returns None."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = self._mock_response({}, status_code=500)

        result = geocode_location_name("Some Venue", "test-key", client=client)
        self.assertIsNone(result)

    def test_geocode_outside_ba(self):
        """Result outside BA bounds returns None."""
        response_data = {
            "results": [
                {
                    "lat": 40.73,
                    "lon": -74.0,
                    "formatted": "New York, NY",
                    "rank": {"confidence": 0.9},
                }
            ]
        }
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = self._mock_response(response_data)

        result = geocode_location_name("Some NYC Venue", "test-key", client=client)
        self.assertIsNone(result)

    def test_geocode_missing_lat_lon(self):
        """Response with missing lat/lon returns None."""
        response_data = {
            "results": [
                {
                    "formatted": "Some address",
                    "rank": {"confidence": 0.5},
                }
            ]
        }
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = self._mock_response(response_data)

        result = geocode_location_name("Some Venue", "test-key", client=client)
        self.assertIsNone(result)

    def test_geocode_malformed_json(self):
        """Malformed JSON response returns None."""
        client = MagicMock(spec=httpx.Client)
        resp = MagicMock(spec=httpx.Response)
        resp.raise_for_status.return_value = None
        resp.json.side_effect = ValueError("invalid json")
        client.get.return_value = resp

        result = geocode_location_name("Some Venue", "test-key", client=client)
        self.assertIsNone(result)

    def test_geocode_no_rank(self):
        """Missing rank defaults confidence to 0.0."""
        response_data = {
            "results": [
                {
                    "lat": -34.60,
                    "lon": -58.40,
                    "formatted": "Some address",
                }
            ]
        }
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = self._mock_response(response_data)

        result = geocode_location_name("Some Venue", "test-key", client=client)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.confidence, 0.0)

    def test_geocode_creates_client_when_none(self):
        """When no client is passed, creates one internally."""
        response_data = self.VALID_BA_RESPONSE

        with patch("geocoding.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = self._mock_response(response_data)
            mock_client_cls.return_value = mock_client

            result = geocode_location_name("Teatro Colón", "test-key")

            mock_client_cls.assert_called_once_with(timeout=10.0)
            self.assertIsNotNone(result)

    def test_geocode_result_not_dict(self):
        """Non-dict first result returns None."""
        response_data = {"results": ["not a dict"]}
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = self._mock_response(response_data)

        result = geocode_location_name("Some Venue", "test-key", client=client)
        self.assertIsNone(result)


class TestProcessorGeocodingIntegration(unittest.TestCase):
    """Tests for geocoding integration in processor.py process_events."""

    def _make_extracted_json(self, events):
        import json

        return json.dumps({"events": events})

    def _make_event(self, name="Test Event", location="New Venue"):
        from datetime import datetime, timedelta

        # Use a date 7 days in the future to avoid filter_by_date rejection
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        return {
            "name": name,
            "location": location,
            "sublocation": "",
            "description": "",
            "url": "",
            "hashtags": [],
            "emoji": "",
            "occurrences": [{"start_date": future_date}],
        }

    @patch.dict(os.environ, {"GEOAPIFY_API_KEY": "test-key"})
    @patch("processor.geocode_location_name")
    @patch("processor.db")
    @patch("processor.create_safe_filename", return_value="test_source")
    def test_new_location_geocoded(self, mock_filename, mock_db, mock_geocode):
        """When a new location is created and geocoding succeeds, UPDATE is executed."""
        from processor import process_events

        event_json = self._make_extracted_json([self._make_event()])
        mock_db.get_extracted_content.return_value = (event_json, 1)
        mock_db.get_crawled_content.return_value = None
        mock_db.get_all_locations.return_value = []
        mock_db.get_source_default_tags.return_value = {}
        mock_db.get_tag_rules.return_value = {
            "rewrite": {},
            "exclude": [],
            "remove": [],
        }

        mock_geocode.return_value = GeocodingResult(
            lat=-34.60,
            lng=-58.40,
            formatted_address="Av. Corrientes 1234",
            confidence=0.85,
        )

        cursor = MagicMock()
        cursor.fetchone.return_value = [77]
        connection = MagicMock()

        process_events(cursor, connection, 100, "Test", "2026-03-22")

        # Verify geocode was called
        mock_geocode.assert_called_once_with("New Venue", "test-key")

        # Verify UPDATE was executed with geocoded values
        update_calls = [
            c for c in cursor.execute.call_args_list if "UPDATE locations" in str(c)
        ]
        self.assertEqual(len(update_calls), 1)
        update_args = update_calls[0][0][1]
        self.assertAlmostEqual(update_args[0], -34.60)
        self.assertAlmostEqual(update_args[1], -58.40)
        self.assertEqual(update_args[2], "Av. Corrientes 1234")
        self.assertEqual(update_args[3], 77)

    @patch.dict(os.environ, {"GEOAPIFY_API_KEY": "test-key"})
    @patch("processor.geocode_location_name")
    @patch("processor.db")
    @patch("processor.create_safe_filename", return_value="test_source")
    def test_new_location_geocoding_fails_gracefully(
        self, mock_filename, mock_db, mock_geocode
    ):
        """When geocoding returns None, no UPDATE, location still created."""
        from processor import process_events

        event_json = self._make_extracted_json([self._make_event()])
        mock_db.get_extracted_content.return_value = (event_json, 1)
        mock_db.get_crawled_content.return_value = None
        mock_db.get_all_locations.return_value = []
        mock_db.get_source_default_tags.return_value = {}
        mock_db.get_tag_rules.return_value = {
            "rewrite": {},
            "exclude": [],
            "remove": [],
        }

        mock_geocode.return_value = None

        cursor = MagicMock()
        cursor.fetchone.return_value = [77]
        connection = MagicMock()

        result = process_events(cursor, connection, 100, "Test", "2026-03-22")

        self.assertEqual(result, 1)

        # No UPDATE should have been executed
        update_calls = [
            c for c in cursor.execute.call_args_list if "UPDATE locations" in str(c)
        ]
        self.assertEqual(len(update_calls), 0)

        # Location INSERT should still have happened
        location_inserts = [
            c
            for c in cursor.execute.call_args_list
            if "INSERT INTO locations" in str(c) and "alternate" not in str(c)
        ]
        self.assertTrue(len(location_inserts) >= 1)

    @patch.dict(os.environ, {"GEOAPIFY_API_KEY": "test-key"})
    @patch("processor.geocode_location_name")
    @patch("processor.db")
    @patch("processor.create_safe_filename", return_value="test_source")
    def test_new_location_geocoding_exception_non_blocking(
        self, mock_filename, mock_db, mock_geocode
    ):
        """When geocoding raises, event processing still completes."""
        from processor import process_events

        event_json = self._make_extracted_json([self._make_event()])
        mock_db.get_extracted_content.return_value = (event_json, 1)
        mock_db.get_crawled_content.return_value = None
        mock_db.get_all_locations.return_value = []
        mock_db.get_source_default_tags.return_value = {}
        mock_db.get_tag_rules.return_value = {
            "rewrite": {},
            "exclude": [],
            "remove": [],
        }

        mock_geocode.side_effect = RuntimeError("unexpected geocoding error")

        cursor = MagicMock()
        cursor.fetchone.return_value = [77]
        connection = MagicMock()

        result = process_events(cursor, connection, 100, "Test", "2026-03-22")

        # Event still processed despite geocoding exception
        self.assertEqual(result, 1)

        # Location INSERT still happened
        location_inserts = [
            c
            for c in cursor.execute.call_args_list
            if "INSERT INTO locations" in str(c) and "alternate" not in str(c)
        ]
        self.assertTrue(len(location_inserts) >= 1)

    @patch.dict(os.environ, {}, clear=False)
    @patch("processor.geocode_location_name")
    @patch("processor.db")
    @patch("processor.create_safe_filename", return_value="test_source")
    def test_no_geocoding_without_api_key(self, mock_filename, mock_db, mock_geocode):
        """When GEOAPIFY_API_KEY is missing, geocoding is skipped."""
        from processor import process_events

        # Remove the key if present
        os.environ.pop("GEOAPIFY_API_KEY", None)

        event_json = self._make_extracted_json([self._make_event()])
        mock_db.get_extracted_content.return_value = (event_json, 1)
        mock_db.get_crawled_content.return_value = None
        mock_db.get_all_locations.return_value = []
        mock_db.get_source_default_tags.return_value = {}
        mock_db.get_tag_rules.return_value = {
            "rewrite": {},
            "exclude": [],
            "remove": [],
        }

        cursor = MagicMock()
        cursor.fetchone.return_value = [77]
        connection = MagicMock()

        result = process_events(cursor, connection, 100, "Test", "2026-03-22")

        self.assertEqual(result, 1)
        mock_geocode.assert_not_called()

    @patch.dict(os.environ, {"GEOAPIFY_API_KEY": "test-key"})
    @patch("processor.geocode_location_name")
    @patch("processor.db")
    @patch("processor.create_safe_filename", return_value="test_source")
    def test_existing_location_no_geocoding(self, mock_filename, mock_db, mock_geocode):
        """Existing locations from locations_map do not trigger geocoding."""
        from processor import process_events

        event_json = self._make_extracted_json([self._make_event(location="Blue Note")])
        mock_db.get_extracted_content.return_value = (event_json, 1)
        mock_db.get_crawled_content.return_value = None
        mock_db.get_all_locations.return_value = [
            {
                "id": 10,
                "name": "Blue Note",
                "short_name": "BN",
                "address": "131 W 3rd St",
                "lat": -34.60,
                "lng": -58.40,
                "emoji": None,
                "alternate_names": [],
            }
        ]
        mock_db.get_source_default_tags.return_value = {}
        mock_db.get_tag_rules.return_value = {
            "rewrite": {},
            "exclude": [],
            "remove": [],
        }

        cursor = MagicMock()
        connection = MagicMock()

        process_events(cursor, connection, 100, "Test", "2026-03-22")

        # Geocoding should NOT be called for existing locations
        mock_geocode.assert_not_called()


if __name__ == "__main__":
    unittest.main()
