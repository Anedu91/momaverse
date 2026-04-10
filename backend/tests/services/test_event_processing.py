"""Tests for pure event-processing helpers."""

from api.services.event_processing import (
    BLOCKED_EMOJI,
    extract_emoji,
    generate_short_name,
)


class TestGenerateShortName:
    def test_strips_exhibition_prefix(self) -> None:
        assert generate_short_name("Exhibition: Monet") == "Monet"

    def test_strips_at_venue_suffix(self) -> None:
        assert generate_short_name("Monet - at MoMA", "MoMA") == "Monet"

    def test_leaves_short_name_untouched(self) -> None:
        assert generate_short_name("Monet") == "Monet"


class TestExtractEmoji:
    def test_returns_first_emoji_and_stripped_text(self) -> None:
        assert extract_emoji("\U0001f3a8 Art Show") == ("\U0001f3a8", "Art Show")

    def test_none_when_no_emoji(self) -> None:
        assert extract_emoji("Art Show") == (None, "Art Show")

    def test_skips_blocked_emoji(self) -> None:
        # "▪" is a blocked glyph; the helper should skip past it and
        # either find the next emoji or return (None, text) unchanged.
        blocked = "\u25aa"
        assert blocked in BLOCKED_EMOJI

        text = f"{blocked} Art Show"
        assert extract_emoji(text) == (None, text)

        text_with_next = f"{blocked} \U0001f3a8 Art Show"
        emoji, stripped = extract_emoji(text_with_next)
        assert emoji == "\U0001f3a8"
        assert stripped == "Art Show"
