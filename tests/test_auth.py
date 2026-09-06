import time

import jwt
import pytest
from fastapi import HTTPException
from freezegun import freeze_time

from backend.auth import get_current_user_id
from tests.auth_helpers import get_access_token
from tests.conftest import TEST_EMAIL, TEST_PASSWORD


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


def test_get_current_user_id_rejects_forged_token():
    # A token signed with a made-up secret/algorithm has no valid `kid`
    # in the real JWKS, so PyJWKClient itself rejects it before signature
    # verification even runs. Covers the "not real" branch generically —
    # renamed from "rejects_invalid_signature" since ES256/JWKS means
    # every one of "unknown kid", "bad signature", and "wrong algorithm"
    # is now the same rejection path.
    bad_token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "aud": "authenticated"},
        "wrong-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(authorization=f"Bearer {bad_token}")
    assert exc_info.value.status_code == 401


def test_get_current_user_id_rejects_expired_token(test_user_id):
    # We can't forge a validly-signed-but-expired ES256 token (we don't
    # hold Supabase's private key), so this test uses a genuine token and
    # travels time forward past its real expiry instead — proving
    # signature verification succeeds AND expiry is separately enforced,
    # against real signing infrastructure rather than a synthetic payload.
    token = get_access_token(TEST_EMAIL, TEST_PASSWORD)

    # Positive control: at real time, the same token verifies successfully.
    # Without this, the frozen-clock 401 below would be equally consistent
    # with "expiry enforced" or "JWKS fetch failed under the frozen clock" —
    # this assertion rules out the second explanation.
    assert get_current_user_id(authorization=f"Bearer {token}") == test_user_id

    future = time.time() + 7200  # past the local project's 1-hour jwt_expiry
    with freeze_time(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(future))):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_id(authorization=f"Bearer {token}")
        assert exc_info.value.status_code == 401


def test_get_current_user_id_rejects_corrupted_signature(test_user_id):
    # The forged-token test above is rejected at `kid` lookup, before
    # signature verification ever runs. This test uses a real token (real
    # `kid`, real key) and corrupts one byte of the signature segment, so
    # the request goes all the way through to actual ES256 signature
    # verification and fails there.
    token = get_access_token(TEST_EMAIL, TEST_PASSWORD)
    header, payload, signature = token.split(".")
    # Corrupt a character from the middle of the signature, not the last
    # character of the base64url string: base64's final partial group can
    # leave a character's low bits unused as padding, so flipping *that*
    # character sometimes decodes to the exact same signature bytes
    # (confirmed intermittently in practice - this position avoids it).
    mid = len(signature) // 2
    mid_char = signature[mid]
    replacement = "A" if mid_char != "A" else "B"
    corrupted_signature = signature[:mid] + replacement + signature[mid + 1 :]
    corrupted_token = f"{header}.{payload}.{corrupted_signature}"

    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(authorization=f"Bearer {corrupted_token}")
    assert exc_info.value.status_code == 401
