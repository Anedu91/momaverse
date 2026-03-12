from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.edit_logger import EditLogger
from api.models.base import EditSource
from api.models.user import User

SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request, db: SessionDep) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await db.get(User, user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def get_optional_user(request: Request, db: SessionDep) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = await db.get(User, user_id)
    if not user:
        request.session.clear()
        return None
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]


async def get_edit_logger(
    request: Request,
    db: SessionDep,
    user: OptionalUserDep,
) -> EditLogger:
    logger = EditLogger(session=db, source=EditSource.website)
    logger.set_user_context_from_request(request, user_id=user.id if user else None)
    return logger


EditLoggerDep = Annotated[EditLogger, Depends(get_edit_logger)]
