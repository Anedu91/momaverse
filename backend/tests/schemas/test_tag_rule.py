import pytest
from pydantic import ValidationError

from api.models.base import TagRuleType
from api.schemas.tag_rule import TagRuleCreate, TagRuleResponse, TagRuleUpdate
from tests.schemas.helpers import make_tag_rule_obj

# ---------------------------------------------------------------------------
# TagRuleCreate
# ---------------------------------------------------------------------------


def test_tag_rule_create_valid():
    rule = TagRuleCreate(
        rule_type=TagRuleType.rewrite, pattern="old", replacement="new"
    )
    assert rule.rule_type == TagRuleType.rewrite
    assert rule.pattern == "old"
    assert rule.replacement == "new"


def test_tag_rule_create_replacement_optional():
    rule = TagRuleCreate(rule_type=TagRuleType.exclude, pattern="spam")
    assert rule.replacement is None


def test_tag_rule_create_rule_type_required():
    with pytest.raises(ValidationError):
        TagRuleCreate(pattern="test")  # type: ignore[call-arg]


def test_tag_rule_create_pattern_required():
    with pytest.raises(ValidationError):
        TagRuleCreate(rule_type=TagRuleType.rewrite)  # type: ignore[call-arg]


def test_tag_rule_create_pattern_max_length():
    with pytest.raises(ValidationError):
        TagRuleCreate(rule_type=TagRuleType.rewrite, pattern="x" * 101)


def test_tag_rule_create_replacement_max_length():
    with pytest.raises(ValidationError):
        TagRuleCreate(
            rule_type=TagRuleType.rewrite, pattern="ok", replacement="x" * 101
        )


def test_tag_rule_create_invalid_rule_type():
    with pytest.raises(ValidationError):
        TagRuleCreate(rule_type="invalid", pattern="test")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TagRuleUpdate
# ---------------------------------------------------------------------------


def test_tag_rule_update_all_optional():
    update = TagRuleUpdate()
    assert update.rule_type is None
    assert update.pattern is None
    assert update.replacement is None


def test_tag_rule_update_partial():
    update = TagRuleUpdate(pattern="new-pattern")
    assert update.pattern == "new-pattern"
    assert update.rule_type is None


# ---------------------------------------------------------------------------
# TagRuleResponse
# ---------------------------------------------------------------------------


def test_tag_rule_response_from_orm():
    obj = make_tag_rule_obj()
    resp = TagRuleResponse.model_validate(obj, from_attributes=True)
    assert resp.id == 1
    assert resp.rule_type == TagRuleType.rewrite
    assert resp.pattern == "old-tag"
    assert resp.replacement == "new-tag"


def test_tag_rule_response_no_replacement():
    obj = make_tag_rule_obj(rule_type="exclude", replacement=None)
    resp = TagRuleResponse.model_validate(obj, from_attributes=True)
    assert resp.rule_type == TagRuleType.exclude
    assert resp.replacement is None
