"""Tests for pure event-processing helpers."""

from api.services.event_processing import (
    BLOCKED_EMOJI,
    extract_emoji,
    generate_short_name,
)


def test_generate_short_name_strips_exhibition_prefix() -> None:
    assert generate_short_name("Exhibition: Monet") == "Monet"


def test_generate_short_name_strips_at_venue_suffix() -> None:
    assert generate_short_name("Monet - at MoMA", "MoMA") == "Monet"


def test_generate_short_name_leaves_short_name_untouched() -> None:
    assert generate_short_name("Monet") == "Monet"


def test_extract_emoji_returns_first_emoji_and_stripped_text() -> None:
    assert extract_emoji("\U0001f3a8 Art Show") == ("\U0001f3a8", "Art Show")


def test_extract_emoji_none_when_no_emoji() -> None:
    assert extract_emoji("Art Show") == (None, "Art Show")


def test_extract_emoji_skips_blocked_emoji_with_no_next() -> None:
    blocked = "\u25aa"
    assert blocked in BLOCKED_EMOJI

    text = f"{blocked} Art Show"
    assert extract_emoji(text) == (None, text)


def test_extract_emoji_skips_blocked_emoji_and_finds_next() -> None:
    blocked = "\u25aa"
    text = f"{blocked} \U0001f3a8 Art Show"
    emoji, stripped = extract_emoji(text)
    assert emoji == "\U0001f3a8"
    assert stripped == "Art Show"
