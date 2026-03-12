from api.schemas.edit import EditResponse

from tests.schemas.helpers import make_edit_obj


def test_response_from_orm():
    obj = make_edit_obj()
    resp = EditResponse.model_validate(obj, from_attributes=True)
    assert resp.table_name == "events"
    assert resp.action == "UPDATE"
