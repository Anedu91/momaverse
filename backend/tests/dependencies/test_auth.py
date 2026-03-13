"""Tests for auth dependencies: password hashing, JWT, user deps."""

import pytest
from api.dependencies import (
    _decode_token,
    create_access_token,
    get_current_user,
    get_optional_user,
    hash_password,
    verify_password,
)
from api.models.user import User
from fastapi.security import HTTPAuthorizationCredentials

# ---------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_password_returns_bcrypt_hash(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"
        assert hashed.startswith("$2")

    def test_verify_password_correct(self):
        hashed = hash_password("correct")
        assert verify_password("correct", hashed) is True

    def test_verify_password_wrong(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_different_calls_produce_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


# ---------------------------------------------------------------
# JWT round-trip
# ---------------------------------------------------------------


class TestJWT:
    def test_create_and_decode_round_trip(self):
        token = create_access_token(user_id=42)
        decoded = _decode_token(token)
        assert decoded == 42

    def test_invalid_token_returns_none(self):
        assert _decode_token("not.a.valid.token") is None

    def test_empty_token_returns_none(self):
        assert _decode_token("") is None

    @pytest.mark.parametrize("user_id", [1, 999, 123456])
    def test_various_user_ids(self, user_id):
        token = create_access_token(user_id=user_id)
        assert _decode_token(token) == user_id


# ---------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, db_session):
        user = User(
            email="auth@test.com",
            display_name="Auth User",
            password_hash="fakehash",
        )
        db_session.add(user)
        await db_session.flush()

        token = create_access_token(user_id=user.id)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = await get_current_user(db_session, creds)
        assert result.id == user.id
        assert result.email == "auth@test.com"

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self, db_session):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db_session, None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, db_session):
        from fastapi import HTTPException

        creds = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="bad.token.here"
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db_session, creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self, db_session):
        from fastapi import HTTPException

        token = create_access_token(user_id=999999)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db_session, creds)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------
# get_optional_user
# ---------------------------------------------------------------


class TestGetOptionalUser:
    @pytest.mark.asyncio
    async def test_no_credentials_returns_none(self, db_session):
        result = await get_optional_user(db_session, None)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self, db_session):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="garbage")
        result = await get_optional_user(db_session, creds)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, db_session):
        user = User(
            email="optional@test.com",
            display_name="Optional",
            password_hash="fakehash",
        )
        db_session.add(user)
        await db_session.flush()

        token = create_access_token(user_id=user.id)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = await get_optional_user(db_session, creds)
        assert result is not None
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_nonexistent_user_returns_none(self, db_session):
        token = create_access_token(user_id=888888)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        result = await get_optional_user(db_session, creds)
        assert result is None
