"""Tests for prefix stripping and core title extraction in ``event_merging``."""

from api.services.event_merging import (
    extract_core_title,
    strip_common_prefixes,
)


def test_strip_common_prefixes_bracketed() -> None:
    assert strip_common_prefixes("[member-only] Sewing") == "Sewing"
    assert strip_common_prefixes("[member-only] Sewing Machines") == "Sewing Machines"


def test_strip_common_prefixes_fido() -> None:
    assert strip_common_prefixes("FIDO Coffee Bark") == "Coffee Bark"
    # Case-insensitive match on the known prefix.
    assert strip_common_prefixes("fido Coffee Bark") == "Coffee Bark"


def test_strip_common_prefixes_nested() -> None:
    assert strip_common_prefixes("[FREE] Jazz") == "Jazz"
    assert strip_common_prefixes("[FREE] Jazz in the Park") == "Jazz in the Park"


def test_extract_core_title_presenter() -> None:
    assert (
        extract_core_title("Manhattan Theatre Club Presents The Monsters")
        == "The Monsters"
    )
    assert (
        extract_core_title("Lincoln Center Presents: Jazz at Midnight")
        == "Jazz at Midnight"
    )


def test_extract_core_title_subtitle() -> None:
    assert extract_core_title("The Monsters: a Sibling Love Story") == "The Monsters"


def test_extract_core_title_short_main_keeps_subtitle() -> None:
    # Main title "ABC" is under 5 chars, so the subtitle is kept.
    assert extract_core_title("ABC: Long Title Here") == "ABC: Long Title Here"


def test_extract_core_title_hosted_by() -> None:
    assert extract_core_title("Hosted by Jane: Talk") == "Talk"
