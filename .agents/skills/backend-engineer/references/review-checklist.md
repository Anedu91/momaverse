# FastAPI/SQLAlchemy Review Checklist

## Quick Pass (every PR)

| Check | What to look for |
|-------|-----------------|
| **Annotated style** | No bare `= Field(...)`, no `= Depends(...)` — must use `Annotated[T, Field()]` |
| **No Ellipsis** | No `...` as default values in schemas or path operations |
| **from_attributes** | Response schemas have `model_config = ConfigDict(from_attributes=True)` |
| **Sync/async** | SQLAlchemy routes use `def` (not `async def`), async-only routes use `async def` |
| **Eager loading** | Queries touching relations use `selectinload`/`joinedload`, no lazy loads in routes |
| **Router config** | Prefix and tags on `APIRouter()`, not on `include_router()` |
| **Return types** | All endpoints have return type annotations or `response_model` |
| **uv** | Dependencies added with `uv add`, not `pip install` |

## Schema Review

| Check | What to look for |
|-------|-----------------|
| **Create schema** | Required fields have no default, optional fields use `| None = None` |
| **Update schema** | All fields are `| None = None` (partial updates) |
| **Response schema** | Includes `from_attributes=True`, only exposes safe fields |
| **No password leak** | `password`, `password_hash`, `editor_ip` never in response schemas |
| **Validation ranges** | Lat (-90..90), lng (-180..180), string max_lengths match DB constraints |
| **No RootModel** | Lists use `list[T]` with `Annotated`, not `RootModel[list[T]]` |

## Route Review

| Check | What to look for |
|-------|-----------------|
| **One operation per function** | No `@app.api_route` with multiple methods |
| **Input validation** | Path params use `Annotated[int, Path(ge=1)]` |
| **Error responses** | Uses `HTTPException` with meaningful detail messages |
| **Auth check** | Protected endpoints use auth dependency |
| **Pagination** | List endpoints support `skip`/`limit` or cursor pagination |
| **Dependency aliases** | Common deps use `TypeAlias` pattern: `SessionDep = Annotated[Session, Depends(get_session)]` |

## SQLAlchemy Review

| Check | What to look for |
|-------|-----------------|
| **N+1 queries** | No attribute access on relations without eager loading |
| **Commit/rollback** | Write operations wrapped in try/except with `session.rollback()` |
| **Parameterized queries** | No f-strings or `.format()` in any query |
| **Select style** | Uses `select(Model)` (2.0 style), not `session.query(Model)` (legacy) |
| **Scalar vs scalars** | `.scalar()` for single result, `.scalars().all()` for lists |
| **No model mutations** | Don't modify existing SQLAlchemy models unless issue explicitly requires it |

## Test Review

| Check | What to look for |
|-------|-----------------|
| **Happy path** | At least one test per endpoint with valid data |
| **Validation errors** | Tests for required field missing, out-of-range values, wrong types |
| **404 handling** | Tests for non-existent resource IDs |
| **Fixtures** | Shared setup in `conftest.py`, not duplicated per test |
| **Parametrize** | Similar test cases grouped with `@pytest.mark.parametrize` |
| **Assertions** | Test behavior (status code + response body), not implementation |
| **Independence** | Tests don't depend on execution order |
| **Cleanup** | DB fixtures use `yield` with proper teardown |

## Security Review

| Check | What to look for |
|-------|-----------------|
| **SQL injection** | All queries parameterized (ORM handles this, but check raw SQL) |
| **Mass assignment** | Create/Update schemas only accept intended fields |
| **Auth bypass** | Protected routes have dependency, not just a check inside the function |
| **Secrets** | No hardcoded passwords, API keys, or connection strings |
| **CORS** | If modified, verify allowed origins are intentional |

## Performance Review

| Check | What to look for |
|-------|-----------------|
| **N+1** | (repeated) Most common FastAPI/SQLAlchemy issue |
| **Unbounded queries** | List endpoints have `limit` with a max cap |
| **Missing indexes** | Columns used in `WHERE`/`ORDER BY` should be indexed |
| **Blocking in async** | No `time.sleep()`, `requests.get()`, or sync DB calls inside `async def` |
