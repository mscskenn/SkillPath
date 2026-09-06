import os
import time

import jwt
import pytest
from fastapi import HTTPException

from backend.auth import get_current_user_id


def test_get_current_user_id_returns_sub_for_valid_token(auth_headers, test_user_id):
    token = auth_headers["Authorization"].removeprefix("Bearer ")
    user_id = get_current_user_id(authorization=f"Bearer {token}")
    assert user_id == test_user_id


def test_get_current_user_id_rejects_missing_header():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(authorization=None)
    assert exc_info.value.status_code == 401


def test_get_current_user_id_rejects_malformed_header():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(authorization="NotBearer sometoken")
    assert exc_info.value.status_code == 401


def test_get_current_user_id_rejects_invalid_signature():
    bad_token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "aud": "authenticated"},
        "wrong-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(authorization=f"Bearer {bad_token}")
    assert exc_info.value.status_code == 401


def test_get_current_user_id_rejects_expired_token(test_user_id):
    secret = os.environ["SUPABASE_JWT_SECRET"]
    expired_token = jwt.encode(
        {
            "sub": test_user_id,
            "aud": "authenticated",
            "exp": int(time.time()) - 60,
        },
        secret,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(authorization=f"Bearer {expired_token}")
    assert exc_info.value.status_code == 401
