"""Tests for processor.py text and processing utilities."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processor import (
    build_locations_map,
    build_sources_map,
    create_short_name,
    get_location_id,
    normalize_event_name_caps,
    process_events,
    strip_leading_emoji,
)

# Test cases: (input, expected_output, description)
SHORT_NAME_TEST_CASES = [
    # Preserve times without am/pm that are part of the event name
    ("In Bed by 1:00 - New Years Eve 2026 at Caveat", "In Bed by 1:00"),
    # Remove trailing times with am/pm
    ("Event Name 7pm", "Event Name"),
    ("Show Name 10:30 PM", "Show Name"),
    # Remove trailing dates
    ("Museum Tour January 15th", "Museum Tour"),
    ("Gallery Opening Oct 5th 6:00pm", "Gallery Opening"),
    ("Park closes 1:00pm December 24", "Park closes"),
    # Preserve meaningful content like session numbers
    ("Everybody Can Sing - Session 2 - Wed 7:30 PM", "Everybody Can Sing - Session 2"),
    # Remove day + time suffixes
    ("Crochet for Beginners - Wed - 6:30PM - Jan", "Crochet for Beginners"),
    # Remove inline dates but preserve middle content
    ("New York Sign Museum December 28th Tour 3:00pm", "New York Sign Museum Tour"),
    # Short titles without metadata stay unchanged
    ("Film Night: The Great Movie", "Film Night: The Great Movie"),
    # Remove venue suffixes
    ("Concert at Madison Square Garden", "Concert"),
    # Long titles with colons extract subtitle
    (
        "A Very Long Exhibition Title That Exceeds Forty Characters: The Actual Show Name",
        "The Actual Show Name",
    ),
    # Time colons don't trigger subtitle extraction (original bug)
    ("New York Sign Museum December 28th Tour 3:00pm", "New York Sign Museum Tour"),
    # Common prefixes removed
    ("Exhibition: Art of the Century", "Art of the Century"),
    ("Screening: Classic Film", "Classic Film"),
    # Empty input
    ("", ""),
]


class TestCreateShortName(unittest.TestCase):
    """Tests for the create_short_name function."""

    def test_short_name_cases(self):
        """Test all short name transformation cases."""
        for input_str, expected in SHORT_NAME_TEST_CASES:
            with self.subTest(input=input_str):
                self.assertEqual(create_short_name(input_str), expected)

    def test_none_input(self):
        """None input should return None."""
        self.assertIsNone(create_short_name(None))


# Test cases: (input, expected_output)
NORMALIZE_CAPS_TEST_CASES = [
    # Apostrophe possessives lowercased
    ("EDGAR A. POE'S SMASHED VALENTINE", "Edgar A. Poe's Smashed Valentine"),
    # Middle initials preserved (A. not lowercased to a.)
    ("MARY J. BLIGE TRIBUTE NIGHT", "Mary J. Blige Tribute Night"),
    # Connecting words lowercased (except at start)
    ("NIGHT OF THE LIVING DEAD", "Night of the Living Dead"),
    ("A TALE OF TWO CITIES", "A Tale of Two Cities"),
    # Roman numerals uppercased
    ("STAR WARS EPISODE III SCREENING", "Star Wars Episode III Screening"),
    # Ordinals lowercased
    ("THE 5TH ANNUAL COMEDY SHOW", "The 5th Annual Comedy Show"),
    # w/ prefix lowercased
    ("JAZZ NIGHT W/ THE QUARTET", "Jazz Night w/ the Quartet"),
    # Film sizes
    ("CLASSIC 35MM FILM FESTIVAL", "Classic 35mm Film Festival"),
    # Two-letter acronyms preserved
    ("DJ NIGHT AT THE CLUB", "DJ Night at the Club"),
    # Already mixed case (<=50% upper) — unchanged
    ("Edgar A. Poe's Smashed Valentine", "Edgar A. Poe's Smashed Valentine"),
    # Short names (<=5 chars) — unchanged
    ("HELLO", "HELLO"),
    # Empty string — unchanged
    ("", ""),
]


# Test cases: (input, expected_output)
STRIP_EMOJI_TEST_CASES = [
    # Leading emoji stripped, trailing preserved
    (
        "\U0001f5a4\U0001f56f\ufe0f Edgar A. Poe's Smashed Valentine \U0001f494\U0001f377",
        "Edgar A. Poe's Smashed Valentine \U0001f494\U0001f377",
    ),
    # Multiple leading emoji with spaces
    ("\U0001f389 \U0001f38a Party Time", "Party Time"),
    # No leading emoji — unchanged
    ("Event Name", "Event Name"),
    # Leading digits not stripped (digits are \p{Emoji} but not \p{Emoji_Presentation})
    ("3 Blind Mice", "3 Blind Mice"),
    # Empty string
    ("", ""),
]


class TestNormalizeEventNameCaps(unittest.TestCase):
    """Tests for the normalize_event_name_caps function."""

    def test_normalize_caps_cases(self):
        for input_str, expected in NORMALIZE_CAPS_TEST_CASES:
            with self.subTest(input=input_str):
                self.assertEqual(normalize_event_name_caps(input_str), expected)


class TestStripLeadingEmoji(unittest.TestCase):
    """Tests for the strip_leading_emoji function."""

    def test_strip_emoji_cases(self):
        for input_str, expected in STRIP_EMOJI_TEST_CASES:
            with self.subTest(input=input_str):
                self.assertEqual(strip_leading_emoji(input_str), expected)

    def test_none_input(self):
        self.assertIsNone(strip_leading_emoji(None))


class TestBuildLocationsMap(unittest.TestCase):
    """Tests for the build_locations_map function."""

    @patch("processor.db")
    def test_no_website_scoped_key(self, mock_db):
        """build_locations_map should not include a 'website_scoped' key."""
        mock_db.get_all_locations.return_value = [
            {
                "id": 1,
                "name": "Test Venue",
                "short_name": "TV",
                "address": "123 Main St",
                "lat": 40.7,
                "lng": -74.0,
                "emoji": None,
                "alternate_names": [],
            }
        ]
        cursor = MagicMock()
        result = build_locations_map(cursor)
        self.assertNotIn("website_scoped", result)
        self.assertIn("names", result)
        self.assertIn("alternate_names", result)
        self.assertIn("short_names", result)
        self.assertIn("addresses", result)


class TestGetLocationId(unittest.TestCase):
    """Tests for the get_location_id function (no website_id param)."""

    def test_exact_name_match(self):
        """Should match by exact location name."""
        locations_map = {
            "names": {"test venue": {"id": 42, "emoji": None}},
            "alternate_names": {},
            "short_names": {},
            "addresses": {},
        }
        result = get_location_id(
            "Test Venue", "", "source", "Event Name", locations_map
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 42)

    def test_no_website_id_parameter(self):
        """get_location_id should not accept website_id keyword."""
        import inspect

        sig = inspect.signature(get_location_id)
        self.assertNotIn("website_id", sig.parameters)

    def test_no_match_returns_none(self):
        """Should return None when no location matches."""
        locations_map = {
            "names": {},
            "alternate_names": {},
            "short_names": {},
            "addresses": {},
        }
        result = get_location_id("Unknown Venue", "", "source", "Event", locations_map)
        self.assertIsNone(result)


class TestBuildSourcesMap(unittest.TestCase):
    """Tests for the renamed build_sources_map function."""

    @patch("processor.db")
    def test_calls_get_source_default_tags(self, mock_db):
        """build_sources_map should call db.get_source_default_tags."""
        mock_db.get_source_default_tags.return_value = {
            "http://example.com": ["jazz"],
        }
        cursor = MagicMock()
        result = build_sources_map(cursor)
        mock_db.get_source_default_tags.assert_called_once_with(cursor)
        self.assertEqual(result, {"http://example.com": ["jazz"]})


class TestProcessEvents(unittest.TestCase):
    """Tests for process_events with JSONB inserts and location creation."""

    def _make_extracted_json(self, events):
        """Helper to create extracted content JSON string."""
        return json.dumps({"events": events})

    @patch("processor.db")
    @patch("processor.create_safe_filename", return_value="test_source")
    def test_jsonb_insert_single_event(self, mock_filename, mock_db):
        """process_events should INSERT into extracted_events with JSONB occurrences and tags."""
        event_json = self._make_extracted_json(
            [
                {
                    "name": "Jazz Night",
                    "location": "Blue Note",
                    "sublocation": "",
                    "description": "Great jazz",
                    "url": "http://example.com/jazz",
                    "hashtags": ["jazz", "live-music"],
                    "emoji": "",
                    "occurrences": [
                        {"start_date": "2026-03-25", "start_time": "7pm"},
                    ],
                }
            ]
        )
        mock_db.get_extracted_content.return_value = (event_json, 1)
        mock_db.get_crawled_content.return_value = None
        mock_db.get_all_locations.return_value = [
            {
                "id": 10,
                "name": "Blue Note",
                "short_name": "BN",
                "address": "131 W 3rd St",
                "lat": 40.73,
                "lng": -74.0,
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

        event_count, _ = process_events(
            cursor, connection, 100, "Test Source", "2026-03-22"
        )

        self.assertEqual(event_count, 1)

        # Verify the INSERT was into extracted_events with JSONB
        insert_calls = [
            c
            for c in cursor.execute.call_args_list
            if "INSERT INTO extracted_events" in str(c)
        ]
        self.assertEqual(len(insert_calls), 1)

        # Check that occurrences and tags are JSON strings
        insert_args = insert_calls[0][0][1]
        occurrences_json = insert_args[9]
        tags_json = insert_args[10]
        occurrences = json.loads(occurrences_json)
        tags = json.loads(tags_json)
        self.assertIsInstance(occurrences, list)
        self.assertEqual(occurrences[0]["start_date"], "2026-03-25")
        self.assertIsInstance(tags, list)
        self.assertIn("jazz", tags)

        # Verify NO insert into crawl_events, crawl_event_occurrences, or crawl_event_tags
        all_sql = " ".join(str(c) for c in cursor.execute.call_args_list)
        self.assertNotIn("crawl_events", all_sql)
        self.assertNotIn("crawl_event_occurrences", all_sql)
        self.assertNotIn("crawl_event_tags", all_sql)

    @patch("processor.db")
    @patch("processor.create_safe_filename", return_value="test_source")
    def test_empty_arrays_not_null(self, mock_filename, mock_db):
        """Empty occurrences/tags should be stored as [] not NULL."""
        event_json = self._make_extracted_json(
            [
                {
                    "name": "Mystery Event",
                    "location": "Somewhere",
                    "sublocation": "",
                    "description": "",
                    "url": "",
                    "hashtags": [],
                    "emoji": "",
                    "occurrences": [
                        {"start_date": "2026-03-25"},
                    ],
                }
            ]
        )
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
        # Mock fetchone for location creation INSERT RETURNING id
        cursor.fetchone.return_value = [99]
        connection = MagicMock()

        event_count, _ = process_events(cursor, connection, 100, "Test", "2026-03-22")

        self.assertEqual(event_count, 1)
        insert_calls = [
            c
            for c in cursor.execute.call_args_list
            if "INSERT INTO extracted_events" in str(c)
        ]
        self.assertEqual(len(insert_calls), 1)
        insert_args = insert_calls[0][0][1]
        tags_json = insert_args[10]
        self.assertEqual(json.loads(tags_json), [])

    @patch("processor.db")
    @patch("processor.create_safe_filename", return_value="test_source")
    def test_location_creation_for_unmatched(self, mock_filename, mock_db):
        """When location not found, should INSERT into locations and location_alternate_names."""
        event_json = self._make_extracted_json(
            [
                {
                    "name": "New Event",
                    "location": "Brand New Venue",
                    "sublocation": "",
                    "description": "",
                    "url": "",
                    "hashtags": [],
                    "emoji": "",
                    "occurrences": [
                        {"start_date": "2026-03-25"},
                    ],
                }
            ]
        )
        mock_db.get_extracted_content.return_value = (event_json, 1)
        mock_db.get_crawled_content.return_value = None
        mock_db.get_all_locations.return_value = []  # No locations to match
        mock_db.get_source_default_tags.return_value = {}
        mock_db.get_tag_rules.return_value = {
            "rewrite": {},
            "exclude": [],
            "remove": [],
        }

        cursor = MagicMock()
        cursor.fetchone.return_value = [77]  # new location id
        connection = MagicMock()

        event_count, _ = process_events(cursor, connection, 100, "Test", "2026-03-22")

        self.assertEqual(event_count, 1)

        # Check that INSERT INTO locations was called
        location_inserts = [
            c
            for c in cursor.execute.call_args_list
            if "INSERT INTO locations" in str(c) and "alternate" not in str(c)
        ]
        self.assertTrue(len(location_inserts) >= 1)

        # Check that INSERT INTO location_alternate_names was called
        alt_name_inserts = [
            c
            for c in cursor.execute.call_args_list
            if "INSERT INTO location_alternate_names" in str(c)
        ]
        self.assertTrue(len(alt_name_inserts) >= 1)

    @patch("processor.db")
    @patch("processor.create_safe_filename", return_value="test_source")
    def test_no_location_creation_for_empty_name(self, mock_filename, mock_db):
        """When location name is empty and no match, should NOT create a location."""
        event_json = self._make_extracted_json(
            [
                {
                    "name": "Floating Event",
                    "location": "",
                    "sublocation": "",
                    "description": "",
                    "url": "",
                    "hashtags": [],
                    "emoji": "",
                    "occurrences": [
                        {"start_date": "2026-03-25"},
                    ],
                }
            ]
        )
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
        connection = MagicMock()

        process_events(cursor, connection, 100, "Test", "2026-03-22")

        # Should still process but NOT insert into locations
        all_sql = " ".join(str(c) for c in cursor.execute.call_args_list)
        self.assertNotIn("INSERT INTO locations", all_sql)

    @patch("processor.db")
    @patch("processor.create_safe_filename", return_value="test_source")
    def test_update_crawl_result_no_event_count(self, mock_filename, mock_db):
        """update_crawl_result_processed should be called without event_count."""
        mock_db.get_extracted_content.return_value = (None, 1)

        cursor = MagicMock()
        connection = MagicMock()

        process_events(cursor, connection, 100, "Test", "2026-03-22")
        mock_db.update_crawl_result_processed.assert_not_called()


if __name__ == "__main__":
    unittest.main()
