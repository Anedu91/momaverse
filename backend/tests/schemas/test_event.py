from datetime import date
from types import SimpleNamespace

import pytest
from api.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
    OccurrenceSchema,
)
from pydantic import ValidationError

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
        OccurrenceSchema()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# EventCreate
# ---------------------------------------------------------------------------


def test_create_valid_minimal():
    ev = EventCreate(name="Art Show", location_id=1)
    assert ev.name == "Art Show"
    assert ev.location_id == 1
    assert ev.occurrences == []


def test_create_valid_full():
    ev = EventCreate(
        name="Art Show",
        short_name="Art",
        emoji="x",
        location_id=1,
        occurrences=[OccurrenceSchema(start_date=date(2026, 4, 1), start_time="18:00")],
        urls=["https://example.com"],
        tags=["art"],
    )
    assert len(ev.occurrences) == 1


def test_create_name_required():
    with pytest.raises(ValidationError):
        EventCreate(location_id=1)  # type: ignore[call-arg]


def test_create_location_id_required():
    with pytest.raises(ValidationError):
        EventCreate(name="Art Show")  # type: ignore[call-arg]


def test_create_name_max_length():
    with pytest.raises(ValidationError):
        EventCreate(name="x" * 501, location_id=1)


# ---------------------------------------------------------------------------
# EventUpdate
# ---------------------------------------------------------------------------


def test_update_all_optional():
    update = EventUpdate()
    assert update.name is None
    assert update.status is None


def test_update_partial():
    update = EventUpdate(status="archived", reviewed=True)
    assert update.status == "archived"


# ---------------------------------------------------------------------------
# EventResponse
# ---------------------------------------------------------------------------


def test_response_from_orm():
    obj = make_event_obj()
    resp = EventResponse.model_validate(obj, from_attributes=True)
    assert resp.id == 1
    assert resp.status == "active"


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


# ---------------------------------------------------------------------------
# URL max_length validation
# ---------------------------------------------------------------------------


def test_create_url_max_length():
    with pytest.raises(ValidationError):
        EventCreate(
            name="Show", location_id=1, urls=["https://example.com/" + "x" * 2000]
        )


def test_create_url_at_max_length():
    url = "https://e.co/" + "x" * (2000 - len("https://e.co/"))
    ev = EventCreate(name="Show", location_id=1, urls=[url])
    assert len(ev.urls[0]) == 2000


def test_update_url_max_length():
    with pytest.raises(ValidationError):
        EventUpdate(urls=["https://example.com/" + "x" * 2000])


# ---------------------------------------------------------------------------
# Detail response nested serialization
# ---------------------------------------------------------------------------


def test_detail_multiple_tags():
    obj = make_event_obj(
        occurrences=[],
        urls=[],
        tags=[make_tag_obj(id=1, name="music"), make_tag_obj(id=2, name="art")],
    )
    resp = EventDetailResponse.model_validate(obj, from_attributes=True)
    assert len(resp.tags) == 2
    assert {t.name for t in resp.tags} == {"music", "art"}


def test_detail_with_occurrences():
    occ = SimpleNamespace(
        id=1,
        start_date=date(2026, 4, 1),
        start_time="18:00",
        end_date=None,
        end_time=None,
    )
    obj = make_event_obj(occurrences=[occ], urls=[], tags=[])
    resp = EventDetailResponse.model_validate(obj, from_attributes=True)
    assert len(resp.occurrences) == 1
    assert resp.occurrences[0].start_date == date(2026, 4, 1)


def test_detail_with_urls():
    url_obj = SimpleNamespace(id=1, url="https://example.com")
    obj = make_event_obj(occurrences=[], urls=[url_obj], tags=[])
    resp = EventDetailResponse.model_validate(obj, from_attributes=True)
    assert len(resp.urls) == 1
    assert resp.urls[0].url == "https://example.com"


def test_detail_empty_relations():
    obj = make_event_obj(occurrences=[], urls=[], tags=[])
    resp = EventDetailResponse.model_validate(obj, from_attributes=True)
    assert resp.occurrences == []
    assert resp.urls == []
    assert resp.tags == []
