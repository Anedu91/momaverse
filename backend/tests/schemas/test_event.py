from datetime import date

import pytest
from pydantic import ValidationError

from api.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
    OccurrenceSchema,
)

from tests.schemas.helpers import make_event_obj, make_tag_obj


# ---------------------------------------------------------------------------
# OccurrenceSchema
# ---------------------------------------------------------------------------


def test_occurrence_valid():
    occ = OccurrenceSchema(start_date=date(2026, 3, 15), start_time="19:00")
    assert occ.start_date == date(2026, 3, 15)
    assert occ.end_date is None


def test_occurrence_start_date_required():
    with pytest.raises(ValidationError):
        OccurrenceSchema()


# ---------------------------------------------------------------------------
# EventCreate
# ---------------------------------------------------------------------------


def test_create_valid_minimal():
    ev = EventCreate(name="Art Show")
    assert ev.name == "Art Show"
    assert ev.occurrences == []


def test_create_valid_full():
    ev = EventCreate(
        name="Art Show",
        short_name="Art",
        emoji="🎨",
        location_name="Gallery",
        occurrences=[
            OccurrenceSchema(start_date=date(2026, 4, 1), start_time="18:00")
        ],
        urls=["https://example.com"],
        tags=["art"],
    )
    assert len(ev.occurrences) == 1


def test_create_name_required():
    with pytest.raises(ValidationError):
        EventCreate()


def test_create_name_max_length():
    with pytest.raises(ValidationError):
        EventCreate(name="x" * 501)


# ---------------------------------------------------------------------------
# EventUpdate
# ---------------------------------------------------------------------------


def test_update_all_optional():
    update = EventUpdate()
    assert update.name is None
    assert update.archived is None


def test_update_partial():
    update = EventUpdate(archived=True, reviewed=True)
    assert update.archived is True


# ---------------------------------------------------------------------------
# EventResponse
# ---------------------------------------------------------------------------


def test_response_from_orm():
    obj = make_event_obj()
    resp = EventResponse.model_validate(obj, from_attributes=True)
    assert resp.id == 1
    assert resp.archived is False


# ---------------------------------------------------------------------------
# EventDetailResponse
# ---------------------------------------------------------------------------


def test_detail_inherits_base_fields():
    obj = make_event_obj(
        occurrences=[],
        urls=[],
        tags=[make_tag_obj(name="concert")],
    )
    resp = EventDetailResponse.model_validate(obj, from_attributes=True)
    assert resp.id == 1
    assert resp.name == "Test Event"
    assert resp.tags[0].name == "concert"
