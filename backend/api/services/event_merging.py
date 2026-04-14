"""Event deduplication and merging helpers.

Pure helpers ported verbatim from ``pipeline/merger.py`` lines 17-87
(name normalization, stemming, and significant-word extraction).

This module intentionally has no database access; it only exposes pure
functions used by the event-merging service. See ``pipeline/merger.py``
for the original reference implementation.
"""

from __future__ import annotations

import re
import unicodedata

STOP_WORDS: frozenset[str] = frozenset(
    {"the", "and", "for", "with", "from", "into", "your"}
)

SEMANTIC_EQUIVALENTS: dict[str, str] = {
    "dinner": "dine",
    "dining": "dine",
    "diner": "dine",
    # Day abbreviations -> full names
    "mon": "monday",
    "tue": "tuesday",
    "tues": "tuesday",
    "wed": "wednesday",
    "weds": "wednesday",
    "thu": "thursday",
    "thur": "thursday",
    "thurs": "thursday",
    "fri": "friday",
    "sat": "saturday",
    "sun": "sunday",
}

STEM_SUFFIXES: list[tuple[str, str]] = [
    ("ency", "enc"),  # residency -> residenc
    ("ence", "enc"),  # residence -> residenc
    ("ing", ""),  # running -> runn
    ("tion", "t"),  # creation -> creat
    ("sion", "s"),  # decision -> decis
    ("ies", "y"),  # stories -> story
    ("es", ""),  # boxes -> box
    ("s", ""),  # cats -> cat
]


def normalize_name_for_dedup(name: str) -> str:
    """Remove accents, punctuation, underscores, and extra whitespace.

    Returns a lowercase, whitespace-collapsed string suitable for
    deduplication comparisons.
    """
    # Normalize unicode to remove accents (é -> e, etc.)
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))

    no_underscores = ascii_name.replace("_", "")
    # Replace punctuation with spaces (not just remove) to avoid word
    # concatenation, e.g. "Alice/Bob" -> "Alice Bob", not "AliceBob".
    no_punct = re.sub(r"[^\w\s]", " ", no_underscores.strip().lower())
    normalized = re.sub(r"\s+", " ", no_punct).strip()
    return normalized


def stem_word(word: str) -> str:
    """Apply semantic equivalents then a small set of suffix rules."""
    if word in SEMANTIC_EQUIVALENTS:
        return SEMANTIC_EQUIVALENTS[word]

    for suffix, replacement in STEM_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            return word[: -len(suffix)] + replacement
    return word


def _is_year(word: str) -> bool:
    """Return True if ``word`` is a 4-digit year in the 20XX range."""
    return len(word) == 4 and word.isdigit() and word.startswith("20")


def get_significant_words(name: str, *, stem: bool = False) -> frozenset[str]:
    """Return 3+ char words from ``name`` minus stop words and years.

    When ``stem`` is true, each word is passed through :func:`stem_word`
    before being returned.
    """
    norm = normalize_name_for_dedup(name)
    words = norm.split()

    result = {
        w for w in words if len(w) >= 3 and w not in STOP_WORDS and not _is_year(w)
    }
    if stem:
        result = {stem_word(w) for w in result}
    return frozenset(result)
