"""Tests for JSONB occurrence and tag parsing in ``event_merging``."""

from datetime import date

from api.services.event_merging import (
    ParsedOccurrence,
    _parse_jsonb,
    parse_occurrences,
    parse_tags,
)

TODAY = date(2026, 4, 10)


# ---------------------------------------------------------------------------
# _parse_jsonb
# ---------------------------------------------------------------------------


def test_parse_jsonb_passthrough_dict() -> None:
    value = {"a": 1, "b": [1, 2]}
    assert _parse_jsonb(value) == value
    assert _parse_jsonb([1, 2, 3]) == [1, 2, 3]


def test_parse_jsonb_string() -> None:
    assert _parse_jsonb('[{"start_date": "2026-05-01"}]') == [
        {"start_date": "2026-05-01"}
    ]
    assert _parse_jsonb('{"k": "v"}') == {"k": "v"}


def test_parse_jsonb_none() -> None:
    assert _parse_jsonb(None) is None


def test_parse_jsonb_invalid() -> None:
    assert _parse_jsonb("not json at all") is None
    # Valid JSON but not a dict/list.
    assert _parse_jsonb("42") is None
    assert _parse_jsonb('"a string"') is None
    # Non-string, non-container types.
    assert _parse_jsonb(42) is None
    assert _parse_jsonb(object()) is None


# ---------------------------------------------------------------------------
# parse_occurrences
# ---------------------------------------------------------------------------


def test_parse_occurrences_filters_past() -> None:
    raw = [{"start_date": "2020-01-01"}]
    assert parse_occurrences(raw, today=TODAY) == []


def test_parse_occurrences_filters_far_future() -> None:
    raw = [{"start_date": "2099-01-01"}]
    assert parse_occurrences(raw, today=TODAY) == []


def test_parse_occurrences_keeps_end_date() -> None:
    raw = [
        {
            "start_date": "2026-04-15",
            "start_time": "19:00",
            "end_date": "2026-04-16",
            "end_time": "21:00",
        }
    ]
    result = parse_occurrences(raw, today=TODAY)
    assert result == [
        ParsedOccurrence(
            start_date=date(2026, 4, 15),
            start_time="19:00",
            end_date=date(2026, 4, 16),
            end_time="21:00",
        )
    ]


def test_parse_occurrences_handles_bad_format() -> None:
    raw = [
        {"start_date": "not-a-date"},
        {"start_date": "2026-04-15", "end_date": "garbage"},
        "not a dict",
        {},
        None,
    ]
    result = parse_occurrences(raw, today=TODAY)
    assert len(result) == 1
    assert result[0].start_date == date(2026, 4, 15)
    assert result[0].end_date is None


def test_parse_occurrences_accepts_json_string() -> None:
    raw = '[{"start_date": "2026-04-20"}]'
    result = parse_occurrences(raw, today=TODAY)
    assert [o.start_date for o in result] == [date(2026, 4, 20)]


def test_parse_occurrences_handles_none_raw() -> None:
    assert parse_occurrences(None, today=TODAY) == []


# ---------------------------------------------------------------------------
# parse_tags
# ---------------------------------------------------------------------------


def test_parse_tags_list() -> None:
    assert parse_tags(["Music", "Art"]) == ["Music", "Art"]
    assert parse_tags('["Music", "Art"]') == ["Music", "Art"]


def test_parse_tags_drops_non_string() -> None:
    assert parse_tags(["Music", "", None, 42, "  Art  "]) == ["Music", "Art"]
    assert parse_tags(None) == []
    assert parse_tags("not json") == []
    assert parse_tags({"not": "a list"}) == []
