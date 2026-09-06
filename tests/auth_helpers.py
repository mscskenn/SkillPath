import os

import httpx
from dotenv import load_dotenv


def create_test_user(email: str, password: str = "testpassword123") -> str:
    load_dotenv()
    base_url = os.environ["SUPABASE_LOCAL_URL"]
    service_role_key = os.environ["SUPABASE_LOCAL_SERVICE_ROLE_KEY"]
    response = httpx.post(
        f"{base_url}/auth/v1/admin/users",
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
        },
        json={"email": email, "password": password, "email_confirm": True},
    )
    response.raise_for_status()
    return response.json()["id"]


def delete_test_user(user_id: str) -> None:
    load_dotenv()
    base_url = os.environ["SUPABASE_LOCAL_URL"]
    service_role_key = os.environ["SUPABASE_LOCAL_SERVICE_ROLE_KEY"]
    httpx.delete(
        f"{base_url}/auth/v1/admin/users/{user_id}",
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
        },
    )


def get_access_token(email: str, password: str) -> str:
    """Sign in as a real user via the local Supabase Auth API and return a
    genuine access token, signed by the real GoTrue instance and
    verifiable via its JWKS endpoint. The local stack has no shared
    HS256 secret to forge a synthetic token with, so tests must obtain
    real tokens this way — this exercises the exact same password-grant
    call the frontend's `supabase.auth.signInWithPassword` makes."""
    load_dotenv()
    base_url = os.environ["SUPABASE_LOCAL_URL"]
    anon_key = os.environ["SUPABASE_LOCAL_ANON_KEY"]
    response = httpx.post(
        f"{base_url}/auth/v1/token?grant_type=password",
        headers={"apikey": anon_key},
        json={"email": email, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]
