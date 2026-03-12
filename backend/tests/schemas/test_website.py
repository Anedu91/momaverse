import pytest
from pydantic import ValidationError

from api.schemas.website import (
    WebsiteCreate,
    WebsiteDetailResponse,
    WebsiteResponse,
    WebsiteUpdate,
)

from tests.schemas.helpers import make_location_obj, make_tag_obj, make_website_obj


# ---------------------------------------------------------------------------
# WebsiteCreate
# ---------------------------------------------------------------------------


def test_create_valid_minimal():
    ws = WebsiteCreate(name="Example Site")
    assert ws.max_pages == 30
    assert ws.urls == []


def test_create_valid_full():
    ws = WebsiteCreate(
        name="Events Page",
        base_url="https://example.com",
        urls=["https://example.com/events"],
        location_ids=[1, 2],
        tags=["music"],
    )
    assert len(ws.urls) == 1


def test_create_name_required():
    with pytest.raises(ValidationError):
        WebsiteCreate()


def test_create_name_max_length():
    with pytest.raises(ValidationError):
        WebsiteCreate(name="x" * 256)


# ---------------------------------------------------------------------------
# WebsiteUpdate
# ---------------------------------------------------------------------------


def test_update_all_optional():
    update = WebsiteUpdate()
    assert update.name is None
    assert update.disabled is None


def test_update_partial():
    update = WebsiteUpdate(disabled=True)
    assert update.disabled is True


# ---------------------------------------------------------------------------
# WebsiteResponse
# ---------------------------------------------------------------------------


def test_response_from_orm():
    obj = make_website_obj()
    resp = WebsiteResponse.model_validate(obj, from_attributes=True)
    assert resp.id == 1


# ---------------------------------------------------------------------------
# WebsiteDetailResponse
# ---------------------------------------------------------------------------


def test_detail_with_relations():
    obj = make_website_obj(
        urls=[],
        locations=[make_location_obj(id=5, name="Gallery")],
        tags=[make_tag_obj(name="music")],
    )
    resp = WebsiteDetailResponse.model_validate(obj, from_attributes=True)
    assert resp.locations[0].id == 5
    assert resp.tags[0].name == "music"
