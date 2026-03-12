import pytest
from pydantic import ValidationError

from api.schemas.edit import EditResponse

from tests.schemas.helpers import make_edit_obj


def test_response_from_orm():
    obj = make_edit_obj()
    resp = EditResponse.model_validate(obj, from_attributes=True)
    assert resp.table_name == "events"
    assert resp.action == "UPDATE"


def test_response_all_fields():
    obj = make_edit_obj()
    resp = EditResponse.model_validate(obj, from_attributes=True)
    assert resp.id == 1
    assert resp.edit_uuid == "abc-123"
    assert resp.record_id == 42
    assert resp.field_name == "name"
    assert resp.old_value == "Old"
    assert resp.new_value == "New"
    assert resp.source == "local"
    assert resp.user_id == 1
    assert resp.applied_at is None


def test_response_nullable_fields():
    obj = make_edit_obj(field_name=None, old_value=None, new_value=None, user_id=None)
    resp = EditResponse.model_validate(obj, from_attributes=True)
    assert resp.field_name is None
    assert resp.old_value is None
    assert resp.new_value is None
    assert resp.user_id is None


def test_response_field_name_max_length():
    with pytest.raises(ValidationError):
        EditResponse.model_validate(
            make_edit_obj(field_name="x" * 101), from_attributes=True
        )


def test_response_field_name_at_max_length():
    obj = make_edit_obj(field_name="x" * 100)
    resp = EditResponse.model_validate(obj, from_attributes=True)
    assert len(resp.field_name) == 100


def test_response_all_actions():
    for action in ("INSERT", "UPDATE", "DELETE"):
        obj = make_edit_obj(action=action)
        resp = EditResponse.model_validate(obj, from_attributes=True)
        assert resp.action == action


def test_response_all_sources():
    for source in ("local", "website", "crawl"):
        obj = make_edit_obj(source=source)
        resp = EditResponse.model_validate(obj, from_attributes=True)
        assert resp.source == source
