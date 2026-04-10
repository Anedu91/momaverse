"""Pure, sync event-processing helpers ported from ``pipeline/processor.py``.

This module contains only the synchronous helpers needed for the backend
event-processing consumer: short-name generation and emoji extraction,
plus the ``BLOCKED_EMOJI`` constant. Async DB-touching services
(``resolve_location``, tag processing) are added in a follow-up PR.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Blocked emoji — ported verbatim from pipeline/processor.py lines 57-77.
# These render as plain boxes/squares and are treated as "no emoji".
# ---------------------------------------------------------------------------
BLOCKED_EMOJI: frozenset[str] = frozenset(
    {
        "\u2b1c",  # ⬜
        "\u25a1",  # □
        "\u25fb",  # ◻
        "\u2b1b",  # ⬛
        "\u25a0",  # ■
        "\u25aa",  # ▪
        "\u25ab",  # ▫
        "\u25fc",  # ◼
        "\u25fe",  # ◾
        "\u25fd",  # ◽
        "\u25ff",  # ◿
        "\u25a2",  # ▢
        "\u25a3",  # ▣
        "\u25a4",  # ▤
        "\u25a5",  # ▥
        "\u25a6",  # ▦
        "\u25a7",  # ▧
        "\u25a8",  # ▨
        "\u25a9",  # ▩
    }
)


# ---------------------------------------------------------------------------
# Emoji regex — a practical approximation of ``pipeline/processor.py``'s
# ``find_first_emoji`` (line 85) and ``strip_leading_emoji`` (line 108).
# The legacy implementation uses the third-party ``regex`` package with
# ``\p{Emoji}`` property classes; here we match the common Unicode emoji
# ranges directly so the backend can rely on stdlib ``re``. Matches a base
# pictographic glyph plus optional variation selectors, skin-tone
# modifiers, and ZWJ sequences.
# ---------------------------------------------------------------------------
_EMOJI_BASE = (
    r"(?:"
    r"[\U0001F1E6-\U0001F1FF]{2}"  # regional indicator pairs (flags)
    r"|[\U0001F300-\U0001F5FF]"  # misc symbols and pictographs
    r"|[\U0001F600-\U0001F64F]"  # emoticons
    r"|[\U0001F680-\U0001F6FF]"  # transport and map
    r"|[\U0001F700-\U0001F77F]"  # alchemical
    r"|[\U0001F780-\U0001F7FF]"  # geometric shapes extended
    r"|[\U0001F800-\U0001F8FF]"  # supplemental arrows-C
    r"|[\U0001F900-\U0001F9FF]"  # supplemental symbols and pictographs
    r"|[\U0001FA00-\U0001FA6F]"  # chess, symbols and pictographs extended-A
    r"|[\U0001FA70-\U0001FAFF]"  # symbols and pictographs extended-B
    r"|[\u2600-\u26FF]"  # miscellaneous symbols
    r"|[\u2700-\u27BF]"  # dingbats
    r"|[\u25A0-\u25FF]"  # geometric shapes
    r"|[\u2B00-\u2BFF]"  # miscellaneous symbols and arrows
    r")"
)
_EMOJI_MODIFIER = r"[\U0001F3FB-\U0001F3FF]"  # skin tone modifiers
_EMOJI_CLUSTER = (
    rf"{_EMOJI_BASE}[\uFE0E\uFE0F]?(?:{_EMOJI_MODIFIER})?"
    rf"(?:\u200D{_EMOJI_BASE}[\uFE0E\uFE0F]?(?:{_EMOJI_MODIFIER})?)*"
)
_EMOJI_RE: re.Pattern[str] = re.compile(_EMOJI_CLUSTER)


def extract_emoji(text: str) -> tuple[str | None, str]:
    """Return the first non-blocked emoji and the text with it stripped.

    Scans ``text`` for emoji clusters. The first cluster that is not in
    :data:`BLOCKED_EMOJI` is returned together with ``text`` with that
    leading emoji (plus any adjacent whitespace) removed. If no
    acceptable emoji is found, returns ``(None, text)`` unchanged.
    """
    if not text:
        return (None, text)

    for match in _EMOJI_RE.finditer(text):
        candidate = match.group(0)
        if candidate in BLOCKED_EMOJI:
            continue
        # Everything up to and including the matched emoji, plus any
        # following whitespace, is stripped. Any leading content that
        # isn't whitespace or a (blocked) emoji means the emoji sits
        # mid-string and we return the original text unchanged.
        prefix = text[: match.start()]
        prefix_cleaned = _EMOJI_RE.sub("", prefix)
        if prefix_cleaned.strip() != "":
            return (candidate, text)
        stripped = text[match.end() :].lstrip()
        return (candidate, stripped)

    return (None, text)


# ---------------------------------------------------------------------------
# Short name generation — ports the ``Exhibition: `` prefix and
# `` - at {venue}`` suffix handling from ``pipeline/processor.py``'s
# ``create_short_name`` (line 167). The full legacy implementation also
# strips dates, times, and other suffixes; those are intentionally out
# of scope for this PR.
# ---------------------------------------------------------------------------
_EXHIBITION_PREFIX_RE = re.compile(r"^Exhibition:\s*")


def generate_short_name(name: str, location_name: str | None = None) -> str:
    """Return a shortened version of an event ``name``.

    - Strips a leading ``"Exhibition: "`` prefix (case-sensitive).
    - If ``location_name`` is provided, strips a trailing
      ``" - at {location_name}"`` suffix.
    - Idempotent: already-short names are returned unchanged (aside from
      whitespace trimming).
    """
    if not name:
        return name

    short = _EXHIBITION_PREFIX_RE.sub("", name)

    if location_name:
        suffix = f" - at {location_name}"
        if short.endswith(suffix):
            short = short[: -len(suffix)]

    return short.strip()
