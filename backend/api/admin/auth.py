"""SQLAdmin authentication backend using session cookies."""

from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import Response

from api.database import AsyncSessionLocal
from api.dependencies import verify_password
from api.models.user import User


class AdminAuth(AuthenticationBackend):
    """Authenticate admin users via session cookies.

    The login form accepts email + password. Only users with
    ``is_admin=True`` are allowed to log in.
    """

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username", "")
        password = form.get("password", "")

        if not email or not password:
            return False

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.email == str(email)))

        if user is None:
            return False

        if not verify_password(str(password), user.password_hash):
            return False

        if not user.is_admin:
            return False

        request.session.update({"user_id": user.id})
        return True

    async def logout(self, request: Request) -> Response | bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> Response | bool:
        user_id = request.session.get("user_id")
        if not user_id:
            return False
        return True
