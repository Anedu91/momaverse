from api.schemas.common import PaginatedResponse, TagResponse

from tests.schemas.helpers import make_tag_obj


def test_paginated_response():
    resp = PaginatedResponse[int](data=[1, 2, 3], total=10)
    assert len(resp.data) == 3
    assert resp.total == 10


def test_tag_response_from_orm():
    obj = make_tag_obj(id=5, name="music")
    resp = TagResponse.model_validate(obj, from_attributes=True)
    assert resp.id == 5
    assert resp.name == "music"
