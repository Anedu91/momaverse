"""Tests for name normalization helpers in ``event_merging``."""

from api.services.event_merging import (
    get_significant_words,
    normalize_name_for_dedup,
    stem_word,
)


def test_normalize_name_for_dedup_strips_accents() -> None:
    assert normalize_name_for_dedup("café") == "cafe"
    assert normalize_name_for_dedup("Café Noël") == "cafe noel"


def test_normalize_name_for_dedup_replaces_punctuation_with_space() -> None:
    assert normalize_name_for_dedup("Alice/Bob") == "alice bob"


def test_normalize_name_for_dedup_collapses_whitespace() -> None:
    assert normalize_name_for_dedup("  Hello   world  ") == "hello world"
    assert normalize_name_for_dedup("foo___bar") == "foobar"
    assert normalize_name_for_dedup("foo\t\nbar") == "foo bar"


def test_stem_word_semantic_equivalents() -> None:
    assert stem_word("dinner") == "dine"
    assert stem_word("dining") == "dine"
    assert stem_word("diner") == "dine"
    assert stem_word("tues") == "tuesday"
    assert stem_word("fri") == "friday"


def test_stem_word_suffix_rules() -> None:
    assert stem_word("residency") == "residenc"
    assert stem_word("residence") == "residenc"
    assert stem_word("stories") == "story"
    assert stem_word("boxes") == "box"
    assert stem_word("creation") == "creat"
    assert stem_word("decision") == "decis"


def test_stem_word_short_word_unchanged() -> None:
    assert stem_word("cat") == "cat"
    # Guard: len(word) > len(suffix) + 2, so short words stay put.
    # For suffix "s" (len 1), word must be longer than 3, so "is" and "as"
    # are unchanged. Similarly "running" (len 7) > 3+2 so the "ing" rule
    # fires, but shorter "ing" words like "sing" stay as "sing".
    assert stem_word("is") == "is"
    assert stem_word("as") == "as"
    assert stem_word("sing") == "sing"
    assert stem_word("boxes") == "box"  # boundary for "es" (len 5 > 4)


def test_get_significant_words_drops_stop_words_and_years() -> None:
    assert get_significant_words("The 2025 Jazz Festival") == frozenset(
        {"jazz", "festival"}
    )
    # Stop words and <3 char words are dropped.
    assert get_significant_words("a and the for") == frozenset()


def test_get_significant_words_stemmed() -> None:
    assert get_significant_words("Dinner Stories", stem=True) == frozenset(
        {"dine", "story"}
    )
    # Without stem, raw words are retained.
    assert get_significant_words("Dinner Stories") == frozenset({"dinner", "stories"})
