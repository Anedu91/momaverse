"""Tests for false-positive guards and name similarity in ``event_merging``."""

from api.services.event_merging import (
    are_names_similar,
    is_false_positive,
)

# ---------------------------------------------------------------------------
# False-positive guards
# ---------------------------------------------------------------------------


def test_fp_mens_vs_womens() -> None:
    assert is_false_positive("Knicks Men's Game", "Knicks Women's Game") is True


def test_fp_different_episodes() -> None:
    assert is_false_positive("Podcast Live Ep. 1", "Podcast Live Ep. 2") is True
    assert is_false_positive("Podcast Live Episode 3", "Podcast Live Episode 4") is True


def test_fp_different_showtimes() -> None:
    assert is_false_positive("Jazz Night | 6:00 PM", "Jazz Night | 8:00 PM") is True


def test_fp_set_1_vs_set_2() -> None:
    assert is_false_positive("Jam Session Set 1", "Jam Session Set 2") is True


def test_fp_different_vs_opponents() -> None:
    assert is_false_positive("Knicks vs Lakers", "Knicks vs Celtics") is True


def test_fp_early_vs_late() -> None:
    assert is_false_positive("Comedy Show Early Set", "Comedy Show Late Set") is True


# ---------------------------------------------------------------------------
# Name similarity
# ---------------------------------------------------------------------------


def test_similar_exact_normalized() -> None:
    assert are_names_similar("Café Jazz", "cafe jazz") is True


def test_similar_after_prefix_strip() -> None:
    assert are_names_similar("[member-only] Sewing Machines", "Sewing Machines") is True


def test_similar_substring() -> None:
    assert (
        are_names_similar(
            "Jazz at Lincoln Center",
            "Jazz at Lincoln Center Tonight",
        )
        is True
    )


def test_similar_presenter_prefix() -> None:
    assert (
        are_names_similar(
            "Manhattan Theatre Club Presents The Monsters",
            "The Monsters",
        )
        is True
    )


def test_similar_jaccard_70() -> None:
    # Four words overlap out of five -> 4/5 = 0.8 >= 0.7.
    assert (
        are_names_similar(
            "Brooklyn Jazz Night Downtown",
            "Brooklyn Jazz Night Uptown",
        )
        is True
    )


def test_similar_stemmed_residency_residence() -> None:
    assert are_names_similar("The Residency Program", "The Residence Program") is True


def test_not_similar_backstage_pass_different_subtitles() -> None:
    assert (
        are_names_similar(
            "Backstage Pass: Duran Duran",
            "Backstage Pass: Arctic Monkeys",
        )
        is False
    )
