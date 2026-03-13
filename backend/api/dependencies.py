from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.database import get_db
from api.models.user import User

SessionDep = Annotated[AsyncSession, Depends(get_db)]

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    result: str = pwd_context.hash(password)
    return result


def verify_password(plain_password: str, hashed_password: str) -> bool:
    result: bool = pwd_context.verify(plain_password, hashed_password)
    return result


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


# TODO: Add `exp` claim to JWT tokens once user-facing auth flows are implemented.
# Currently tokens don't expire — acceptable during migration but must be addressed
# before production user interactions.
def create_access_token(user_id: int) -> str:
    settings = get_settings()
    payload = {"sub": str(user_id)}
    token: str = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token


def _decode_token(token: str) -> int | None:
    """Decode a JWT and return the user_id, or None if invalid."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None
        return int(sub)
    except JWTError, ValueError:
        return None


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
) -> User:
    """Require a valid JWT. Returns the User or raises 401."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_id = _decode_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_optional_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
) -> User | None:
    """Extract user from JWT if present; return None otherwise."""
    if credentials is None:
        return None

    user_id = _decode_token(credentials.credentials)
    if user_id is None:
        return None

    user: User | None = await db.scalar(select(User).where(User.id == user_id))
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]
