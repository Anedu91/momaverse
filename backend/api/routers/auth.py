from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from api.config import get_settings
from api.dependencies import (
    CurrentUserDep,
    SessionDep,
    create_access_token,
    hash_password,
    verify_password,
)
from api.models.user import User
from api.schemas.auth import AuthResponse
from api.schemas.user import UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(data: UserCreate, db: SessionDep) -> AuthResponse:
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(data: UserLogin, db: SessionDep) -> AuthResponse:
    user = await db.scalar(select(User).where(User.email == data.email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user.last_login_at = func.now()
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_user: CurrentUserDep) -> Response:
    # TODO: implement token blocklist for real logout
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUserDep) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/promote-admin", status_code=status.HTTP_200_OK)
async def promote_admin(
    email: str,
    api_key: str,
    db: SessionDep,
) -> dict[str, str]:
    """Promote a user to admin. Secured by SYNC_API_KEY."""
    settings = get_settings()
    if api_key != settings.sync_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_admin = True
    await db.commit()
    return {"message": f"{email} is now an admin"}
