import pytest
from api.models.base import LocationType
from api.schemas.location import (
    LocationCreate,
    LocationDetailResponse,
    LocationResponse,
    LocationUpdate,
)
from pydantic import ValidationError

from tests.schemas.helpers import (
    make_alternate_name_obj,
    make_location_obj,
    make_tag_obj,
)

# ---------------------------------------------------------------------------
# LocationCreate
# ---------------------------------------------------------------------------


def test_create_valid_minimal():
    loc = LocationCreate(name="Central Park")
    assert loc.name == "Central Park"
    assert loc.lat is None
    assert loc.alternate_names == []


def test_create_valid_full():
    loc = LocationCreate(
        name="MoMA",
        short_name="MoMA",
        lat=40.7614,
        lng=-73.9776,
        emoji="x",
        alternate_names=["Museum of Modern Art"],
        tags=["museum", "art"],
    )
    assert loc.lat == 40.7614


def test_create_name_required():
    with pytest.raises(ValidationError):
        LocationCreate()  # type: ignore[call-arg]


def test_create_name_max_length():
    with pytest.raises(ValidationError):
        LocationCreate(name="x" * 256)


def test_create_lat_out_of_range_high():
    with pytest.raises(ValidationError):
        LocationCreate(name="Bad", lat=91.0)


def test_create_lat_out_of_range_low():
    with pytest.raises(ValidationError):
        LocationCreate(name="Bad", lat=-91.0)


def test_create_lng_out_of_range():
    with pytest.raises(ValidationError):
        LocationCreate(name="Bad", lng=181.0)


def test_create_lat_boundary_values():
    loc = LocationCreate(name="North Pole", lat=90.0, lng=0.0)
    assert loc.lat == 90.0
    loc2 = LocationCreate(name="South Pole", lat=-90.0, lng=-180.0)
    assert loc2.lng == -180.0


# ---------------------------------------------------------------------------
# LocationUpdate
# ---------------------------------------------------------------------------


def test_update_all_optional():
    update = LocationUpdate()
    assert update.name is None
    assert update.lat is None
    assert update.tags is None


def test_update_partial():
    update = LocationUpdate(name="New Name", lat=10.0)
    assert update.name == "New Name"
    assert update.description is None


# ---------------------------------------------------------------------------
# LocationResponse
# ---------------------------------------------------------------------------


def test_response_from_orm():
    obj = make_location_obj()
    resp = LocationResponse.model_validate(obj, from_attributes=True)
    assert resp.id == 1
    assert resp.name == "Test Location"


# ---------------------------------------------------------------------------
# LocationDetailResponse
# ---------------------------------------------------------------------------


def test_detail_with_relations():
    obj = make_location_obj(
        name="MoMA",
        address="11 W 53rd St",
        lat=40.7614,
        lng=-73.9776,
        alternate_names=[
            make_alternate_name_obj(alternate_name="Museum of Modern Art")
        ],
        tags=[make_tag_obj(name="museum")],
    )
    resp = LocationDetailResponse.model_validate(obj, from_attributes=True)
    assert len(resp.alternate_names) == 1
    assert resp.alternate_names[0].alternate_name == "Museum of Modern Art"
    assert resp.tags[0].name == "museum"


# ---------------------------------------------------------------------------
# LocationType enum validation
# ---------------------------------------------------------------------------


def test_create_type_default_is_venue():
    loc = LocationCreate(name="Test")
    assert loc.type == LocationType.venue


def test_create_type_accepts_valid_enum():
    loc = LocationCreate(name="Test", type=LocationType.area)
    assert loc.type == LocationType.area


def test_create_type_accepts_string_value():
    loc = LocationCreate(name="Test", type="meeting_point")  # type: ignore[arg-type]
    assert loc.type == LocationType.meeting_point


def test_create_type_rejects_invalid():
    with pytest.raises(ValidationError):
        LocationCreate(name="Test", type="invalid_type")  # type: ignore[arg-type]


def test_update_type_accepts_enum():
    update = LocationUpdate(type=LocationType.area)
    assert update.type == LocationType.area


def test_response_type_is_enum():
    obj = make_location_obj(type="area")
    resp = LocationResponse.model_validate(obj, from_attributes=True)
    assert resp.type == LocationType.area
    assert isinstance(resp.type, LocationType)
