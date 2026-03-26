"""Tests for soft-delete filtering in SQLAdmin views."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import DeclarativeBase

from api.admin.views import EventAdmin, LocationAdmin, SourceAdmin, TagRuleAdmin
from api.models.event import Event
from api.models.location import Location
from api.models.source import Source
from api.models.tag import TagRule

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Maps each admin class to the model it manages
_SOFT_DELETE_VIEWS: list[tuple[type, type[DeclarativeBase]]] = [
    (LocationAdmin, Location),
    (SourceAdmin, Source),
    (EventAdmin, Event),
    (TagRuleAdmin, TagRule),
]

_VIEW_IDS = ["LocationAdmin", "SourceAdmin", "EventAdmin", "TagRuleAdmin"]


def _fake_request() -> Any:
    """Return a minimal mock request for query methods."""
    return MagicMock()


def _compile_where(stmt: Any) -> str:
    """Compile a statement's WHERE clause to a string for assertion."""
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("admin_cls", "model_cls"),
    _SOFT_DELETE_VIEWS,
    ids=_VIEW_IDS,
)
def test_list_query_filters_soft_deleted(
    admin_cls: type, model_cls: type[DeclarativeBase]
) -> None:
    """list_query should include a WHERE clause filtering on deleted_at IS NULL."""
    admin = admin_cls()
    query = admin.list_query(_fake_request())

    compiled = _compile_where(query)
    assert "deleted_at IS NULL" in compiled

    # The FROM clause should match
    assert model_cls.__tablename__ in compiled


@pytest.mark.parametrize(
    ("admin_cls", "model_cls"),
    _SOFT_DELETE_VIEWS,
    ids=_VIEW_IDS,
)
def test_count_query_filters_soft_deleted(
    admin_cls: type, model_cls: type[DeclarativeBase]
) -> None:
    """count_query should count only active (non-deleted) records."""
    admin = admin_cls()
    query = admin.count_query(_fake_request())

    compiled = _compile_where(query)
    assert "deleted_at IS NULL" in compiled

    # Verify it uses count()
    assert "count(" in compiled.lower()


@pytest.mark.parametrize(
    ("admin_cls", "model_cls"),
    _SOFT_DELETE_VIEWS,
    ids=_VIEW_IDS,
)
def test_details_query_filters_soft_deleted(
    admin_cls: type, model_cls: type[DeclarativeBase]
) -> None:
    """details_query should filter out soft-deleted records."""
    admin = admin_cls()
    query = admin.details_query(_fake_request())

    compiled = _compile_where(query)
    assert "deleted_at IS NULL" in compiled
    assert model_cls.__tablename__ in compiled


@pytest.mark.parametrize(
    ("admin_cls", "model_cls"),
    _SOFT_DELETE_VIEWS,
    ids=_VIEW_IDS,
)
def test_list_query_matches_expected_shape(
    admin_cls: type, model_cls: type[DeclarativeBase]
) -> None:
    """list_query should return a select(Model).where(Model.active()) equivalent."""
    admin = admin_cls()
    actual = str(
        admin.list_query(_fake_request()).compile(
            compile_kwargs={"literal_binds": True}
        )
    )
    expected = str(
        select(model_cls)
        .where(model_cls.active())  # type: ignore[attr-defined]
        .compile(compile_kwargs={"literal_binds": True})
    )
    assert actual == expected


@pytest.mark.parametrize(
    ("admin_cls", "model_cls"),
    _SOFT_DELETE_VIEWS,
    ids=_VIEW_IDS,
)
def test_count_query_matches_expected_shape(
    admin_cls: type, model_cls: type[DeclarativeBase]
) -> None:
    """count_query should return select(func.count(Model.id)).where(Model.active())."""
    admin = admin_cls()
    actual = str(
        admin.count_query(_fake_request()).compile(
            compile_kwargs={"literal_binds": True}
        )
    )
    expected = str(
        select(func.count(model_cls.id))  # type: ignore[attr-defined]
        .where(model_cls.active())  # type: ignore[attr-defined]
        .compile(compile_kwargs={"literal_binds": True})
    )
    assert actual == expected
