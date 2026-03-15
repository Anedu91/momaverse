# Backend Review Report Template

Use this template when producing a review report in Review mode.

```markdown
# Backend Review: [PR Title]

## Summary
[1-2 sentence overview: what this PR does and overall assessment]

**Verdict**: Approve | Request Changes | Comment

## FastAPI/SQLAlchemy Compliance

| Rule | Status | Notes |
|------|--------|-------|
| `Annotated` style | pass/fail | |
| `from_attributes=True` on responses | pass/fail | |
| Sync `def` for SQLAlchemy routes | pass/fail | |
| Eager loading (no N+1) | pass/fail | |
| Router prefix/tags on `APIRouter()` | pass/fail | |
| Return type annotations | pass/fail | |
| No Ellipsis defaults | pass/fail | |
| No RootModel | pass/fail | |

## Critical Issues (Must Fix)

### 1. [file:line] Title
- **Current**: What the code does now
- **Expected**: What it should do
- **Impact**: Security risk / data loss / crash
- **Fix**:
```python
# suggested code
```

## Major Issues (Should Fix)

### 1. [file:line] Title
- **Current**: ...
- **Suggested**: ...
- **Impact**: Performance / maintainability / correctness

## Minor Issues (Nice to Have)

### 1. [file:line] Title
- **Suggestion**: ...

## Positive Feedback
- [Specific patterns done well]

## Test Coverage Assessment
- [ ] Happy path tested
- [ ] Validation errors tested (422s)
- [ ] Not-found tested (404s)
- [ ] Edge cases tested
- [ ] Fixtures in conftest.py
- [ ] Parametrized where appropriate

## Questions for Author
- [Specific, answerable questions]
```

## Verdict Guidelines

| Verdict | When |
|---------|------|
| **Approve** | Compliance table all green, no critical/major issues |
| **Request Changes** | Any critical issue, or 2+ major issues |
| **Comment** | Questions need answers, or only minor issues |
