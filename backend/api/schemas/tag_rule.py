from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from api.models.base import TagRuleType

__all__ = [
    "TagRuleResponse",
    "TagRuleCreate",
    "TagRuleUpdate",
]


class TagRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_type: TagRuleType
    pattern: str
    replacement: str | None = None
    created_at: datetime


class TagRuleCreate(BaseModel):
    rule_type: TagRuleType
    pattern: Annotated[str, Field(max_length=100)]
    replacement: Annotated[str | None, Field(max_length=100)] = None


class TagRuleUpdate(BaseModel):
    rule_type: TagRuleType | None = None
    pattern: Annotated[str | None, Field(max_length=100)] = None
    replacement: Annotated[str | None, Field(max_length=100)] = None
