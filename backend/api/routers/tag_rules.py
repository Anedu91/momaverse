from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from api.dependencies import CurrentUserDep, SessionDep
from api.models.tag import TagRule
from api.schemas.tag_rule import TagRuleCreate, TagRuleResponse, TagRuleUpdate

router = APIRouter(prefix="/tag-rules", tags=["tag-rules"])


@router.get("/", response_model=list[TagRuleResponse])
async def list_tag_rules(
    db: SessionDep,
    user: CurrentUserDep,
    include_deleted: bool = False,
) -> list[TagRuleResponse]:
    stmt = select(TagRule).order_by(TagRule.id)

    if not include_deleted:
        stmt = stmt.where(TagRule.active())

    result = await db.execute(stmt)
    rules = result.scalars().all()
    return [TagRuleResponse.model_validate(r) for r in rules]


@router.post("/", response_model=TagRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_tag_rule(
    data: TagRuleCreate,
    db: SessionDep,
    user: CurrentUserDep,
) -> TagRuleResponse:
    rule = TagRule(
        rule_type=data.rule_type,
        pattern=data.pattern,
        replacement=data.replacement,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return TagRuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=TagRuleResponse)
async def update_tag_rule(
    rule_id: int,
    data: TagRuleUpdate,
    db: SessionDep,
    user: CurrentUserDep,
) -> TagRuleResponse:
    rule = await db.scalar(
        select(TagRule).where(TagRule.id == rule_id, TagRule.active())
    )
    if rule is None:
        raise HTTPException(status_code=404, detail="Tag rule not found")

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return TagRuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag_rule(
    rule_id: int,
    db: SessionDep,
    user: CurrentUserDep,
) -> Response:
    rule = await db.scalar(
        select(TagRule).where(TagRule.id == rule_id, TagRule.active())
    )
    if rule is None:
        raise HTTPException(status_code=404, detail="Tag rule not found")

    rule.soft_delete()
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
