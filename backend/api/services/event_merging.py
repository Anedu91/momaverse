"""Event deduplication and merging helpers.

Pure helpers ported verbatim from ``pipeline/merger.py`` lines 17-87
(name normalization, stemming, and significant-word extraction).

This module intentionally has no database access; it only exposes pure
functions used by the event-merging service. See ``pipeline/merger.py``
for the original reference implementation.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

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


KNOWN_PROGRAM_PREFIXES: tuple[str, ...] = ("FIDO",)

PRESENTER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^.+?\s+presents?\s*:?\s*", re.IGNORECASE),
    re.compile(r"^.+?\s+productions?\s*:?\s*", re.IGNORECASE),
    re.compile(r"^hosted\s+by\s+.+?:\s*", re.IGNORECASE),
)

_BRACKETED_PREFIX_RE = re.compile(r"^\s*\[[^\]]+\]\s*")


def strip_common_prefixes(name: str) -> str:
    """Strip common prefixes that don't change event identity.

    Handles:
    - Bracketed prefixes: ``[member-only]``, ``[free]``, ``[virtual]``, etc.
    - Known event program prefixes: ``FIDO`` (Prospect Park dog events), etc.

    Examples:
        ``"[member-only] Sewing Machines"`` -> ``"Sewing Machines"``
        ``"FIDO Coffee Bark"`` -> ``"Coffee Bark"``
        ``"[FREE] Jazz in the Park"`` -> ``"Jazz in the Park"``
    """
    result = name.strip()
    result = _BRACKETED_PREFIX_RE.sub("", result)

    for prefix in KNOWN_PROGRAM_PREFIXES:
        pattern = rf"^{re.escape(prefix)}\s+"
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)

    return result.strip()


def extract_core_title(name: str) -> str:
    """Extract the core title by removing presenter prefixes and subtitles.

    Examples:
        ``"Manhattan Theatre Club Presents The Monsters"`` -> ``"The Monsters"``
        ``"The Monsters: a Sibling Love Story"`` -> ``"The Monsters"``
        ``"Lincoln Center Presents: Jazz at Midnight"`` -> ``"Jazz at Midnight"``
        ``"[member-only] Sewing Class"`` -> ``"Sewing Class"``
        ``"FIDO Coffee Bark"`` -> ``"Coffee Bark"``
    """
    result = strip_common_prefixes(name)

    for pattern in PRESENTER_PATTERNS:
        result = pattern.sub("", result)

    # Remove subtitles after colon, but keep if main title is too short.
    if ":" in result:
        main_title = result.split(":", 1)[0].strip()
        if len(main_title) >= 5:
            result = main_title

    return result.strip()


# Precompiled patterns for false-positive detection.
_TIME_END_RE: re.Pattern[str] = re.compile(r"\d{3,4}\s*(?:am|pm)$", re.IGNORECASE)
_NIGHT_RE: re.Pattern[str] = re.compile(r"night\s*(\d+)")
_EPISODE_RE: re.Pattern[str] = re.compile(r"ep(?:isode)?\.?\s*(\d+)", re.IGNORECASE)
NUMBERED_KEYWORDS: tuple[str, ...] = (
    "set",
    "part",
    "vol",
    "volume",
    "chapter",
    "session",
    "round",
)
_NUMBERED_RE_BY_KEYWORD: dict[str, re.Pattern[str]] = {
    kw: re.compile(rf"\b{kw}\.?\s*(\d+)", re.IGNORECASE) for kw in NUMBERED_KEYWORDS
}
_SEQ_RE: re.Pattern[str] = re.compile(r"(?:^|\|)\s*#?\s*(\d+)\s*(?:\||$)")
_VS_RE: re.Pattern[str] = re.compile(r"vs\.?\s+(.+?)(?:\s*-|$)", re.IGNORECASE)
_TIME_ANYWHERE_RE: re.Pattern[str] = re.compile(
    r"\b(\d{1,2}\s*\d{2}\s*(?:am|pm))\b", re.IGNORECASE
)


def is_false_positive(name1: str, name2: str) -> bool:
    """Return True if two "similar" names are actually distinct events.

    Ported verbatim from ``pipeline/merger.py`` lines 157-244. Catches
    cases where names share words but refer to different events:

    - Men's vs Women's sports
    - Different showtimes (6:00 PM vs 8:00 PM, anywhere in name)
    - Early vs Late sets
    - Different episode numbers
    - Different set/part/volume numbers
    - Different sports opponents
    """
    norm1 = normalize_name_for_dedup(name1)
    norm2 = normalize_name_for_dedup(name2)

    # Different gendered sports events (Men's vs Women's).
    if ("men" in norm1) != ("men" in norm2) or ("women" in norm1) != ("women" in norm2):
        return True

    # Different times at end (different showtimes).
    time1 = _TIME_END_RE.search(norm1)
    time2 = _TIME_END_RE.search(norm2)
    if time1 and time2 and time1.group() != time2.group():
        return True

    # Early vs Late sets.
    if ("early" in norm1) != ("early" in norm2) or ("late" in norm1) != (
        "late" in norm2
    ):
        return True

    # Different numbered nights/sessions.
    night1 = _NIGHT_RE.search(norm1)
    night2 = _NIGHT_RE.search(norm2)
    if night1 and night2 and night1.group(1) != night2.group(1):
        return True

    # Different episodes.
    ep1 = _EPISODE_RE.search(norm1)
    ep2 = _EPISODE_RE.search(norm2)
    if ep1 and ep2 and ep1.group(1) != ep2.group(1):
        return True

    # Different set/part/volume numbers.
    for keyword in NUMBERED_KEYWORDS:
        pattern = _NUMBERED_RE_BY_KEYWORD[keyword]
        match1 = pattern.search(norm1)
        match2 = pattern.search(norm2)
        if match1 and match2 and match1.group(1) != match2.group(1):
            return True

    # Different standalone sequence numbers after pipe/dash separators.
    seq1 = _SEQ_RE.findall(norm1)
    seq2 = _SEQ_RE.findall(norm2)
    if seq1 and seq2 and seq1 != seq2:
        return True

    # Different sports opponents (vs X vs vs Y).
    vs1 = _VS_RE.search(norm1)
    vs2 = _VS_RE.search(norm2)
    if vs1 and vs2:
        opponent1 = vs1.group(1).strip()
        opponent2 = vs2.group(1).strip()
        if (
            opponent1 != opponent2
            and opponent1 not in opponent2
            and opponent2 not in opponent1
        ):
            return True

    # Different times anywhere in name.
    times1 = set(_TIME_ANYWHERE_RE.findall(norm1))
    times2 = set(_TIME_ANYWHERE_RE.findall(norm2))
    if times1 and times2 and times1 != times2:
        return True

    return False


def are_names_similar(name1: str, name2: str) -> bool:
    """Return True if two event names are similar enough to be duplicates.

    Ported verbatim from ``pipeline/merger.py`` lines 247-361. Uses six
    strategies:

    1. Exact match after normalization.
    2. Match after stripping common prefixes (FIDO, [member-only], etc.).
    3. Substring matching for prefix/suffix variations.
    4. Core title extraction (removing presenter prefixes and subtitles),
       with a subtitle-match exception for colon-separated series titles.
    5. Word-based matching: subset or Jaccard >= 0.7.
    6. Stemmed word matching with asymmetric 0.75 containment.

    Also short-circuits to False for known false-positive patterns via
    :func:`is_false_positive`.
    """
    # False-positive short-circuit.
    if is_false_positive(name1, name2):
        return False

    norm1 = normalize_name_for_dedup(name1)
    norm2 = normalize_name_for_dedup(name2)

    # 1. Exact match after normalization.
    if norm1 == norm2:
        return True

    # 2. Match after stripping common prefixes.
    stripped1 = normalize_name_for_dedup(strip_common_prefixes(name1))
    stripped2 = normalize_name_for_dedup(strip_common_prefixes(name2))
    if stripped1 == stripped2:
        return True

    # 3. Substring match for prefix/suffix variations.
    if len(norm1) >= 5 and len(norm2) >= 5:
        if norm1 in norm2 or norm2 in norm1:
            return True

    if len(stripped1) >= 5 and len(stripped2) >= 5:
        if stripped1 in stripped2 or stripped2 in stripped1:
            return True

    # 4. Core title comparison (with subtitle exception for series titles).
    core1 = extract_core_title(name1)
    core2 = extract_core_title(name2)
    skip_core_title_match = False
    if core1 and core2:
        norm_core1 = normalize_name_for_dedup(core1)
        norm_core2 = normalize_name_for_dedup(core2)
        if norm_core1 == norm_core2:
            # Series:episode format — require subtitle similarity too.
            if ":" in name1 and ":" in name2:
                subtitle1 = name1.split(":", 1)[1].strip()
                subtitle2 = name2.split(":", 1)[1].strip()
                if subtitle1 and subtitle2:
                    norm_sub1 = normalize_name_for_dedup(subtitle1)
                    norm_sub2 = normalize_name_for_dedup(subtitle2)
                    if (
                        norm_sub1 == norm_sub2
                        or norm_sub1 in norm_sub2
                        or norm_sub2 in norm_sub1
                    ):
                        return True
                    skip_core_title_match = True
                else:
                    return True
            else:
                return True
        if not skip_core_title_match and len(norm_core1) >= 5 and len(norm_core2) >= 5:
            if norm_core1 in norm_core2 or norm_core2 in norm_core1:
                return True

    # 5. Word-based similarity with unstemmed words.
    words1 = get_significant_words(name1)
    words2 = get_significant_words(name2)

    if words1 and words2:
        if words1.issubset(words2) or words2.issubset(words1):
            return True

        intersection = words1 & words2
        union = words1 | words2
        if len(intersection) / len(union) >= 0.7:
            return True

    # 6. Stemmed word matching.
    stemmed1 = get_significant_words(name1, stem=True)
    stemmed2 = get_significant_words(name2, stem=True)

    if stemmed1 and stemmed2:
        if stemmed1.issubset(stemmed2) or stemmed2.issubset(stemmed1):
            return True

        intersection = stemmed1 & stemmed2
        union = stemmed1 | stemmed2
        if len(intersection) / len(union) >= 0.7:
            return True

        # Asymmetric containment: 75%+ of shorter name's words in the longer.
        shorter, longer = (
            (stemmed1, stemmed2)
            if len(stemmed1) <= len(stemmed2)
            else (stemmed2, stemmed1)
        )
        if len(shorter) >= 2 and len(intersection) / len(shorter) >= 0.75:
            return True

    return False


# ---------------------------------------------------------------------------
# JSONB parsing helpers (ported from pipeline/merger.py lines 364-375, 563-610)
# ---------------------------------------------------------------------------

FUTURE_LIMIT_DAYS: int = 90
ARCHIVE_GRACE_DAYS: int = 14


@dataclass(frozen=True)
class ParsedOccurrence:
    """A single parsed occurrence from the JSONB ``occurrences`` column."""

    start_date: date
    start_time: str | None
    end_date: date | None
    end_time: str | None


def _parse_jsonb(value: object) -> list[Any] | dict[str, Any] | None:
    """Parse a JSONB value that may be a string, dict/list, or None.

    Ported from ``pipeline/merger.py`` lines 364-375.
    """
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return None
        if isinstance(parsed, (dict, list)):
            return parsed
        return None
    return None


def _parse_date(value: object) -> date | None:
    """Safely parse a YYYY-MM-DD string into a date, or None."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _parse_time_str(value: object) -> str | None:
    """Return the value as a string if non-empty, else None."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def parse_occurrences(raw: object, *, today: date) -> list[ParsedOccurrence]:
    """Parse and filter the JSONB ``occurrences`` column.

    Keeps only occurrences whose ``start_date`` falls within
    ``[today, today + FUTURE_LIMIT_DAYS]``. Malformed entries are skipped.

    Ported from ``pipeline/merger.py`` lines 563-605.
    """
    parsed = _parse_jsonb(raw) or []
    if not isinstance(parsed, list):
        return []

    future_limit = today + timedelta(days=FUTURE_LIMIT_DAYS)
    result: list[ParsedOccurrence] = []

    for occ in parsed:
        if not isinstance(occ, dict):
            continue
        start_date = _parse_date(occ.get("start_date"))
        if start_date is None:
            continue
        if not (today <= start_date <= future_limit):
            continue

        result.append(
            ParsedOccurrence(
                start_date=start_date,
                start_time=_parse_time_str(occ.get("start_time")),
                end_date=_parse_date(occ.get("end_date")),
                end_time=_parse_time_str(occ.get("end_time")),
            )
        )

    return result


def parse_tags(raw: object) -> list[str]:
    """Parse the JSONB ``tags`` column into a clean list of strings.

    Drops non-string entries and strips whitespace from each tag. Empty
    strings (after stripping) are also dropped.

    Ported from ``pipeline/merger.py`` lines 607-610.
    """
    parsed = _parse_jsonb(raw) or []
    if not isinstance(parsed, list):
        return []

    result: list[str] = []
    for tag in parsed:
        if not isinstance(tag, str):
            continue
        stripped = tag.strip()
        if stripped:
            result.append(stripped)
    return result
