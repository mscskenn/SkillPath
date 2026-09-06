import os
import time

import httpx
import jwt
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


def make_test_jwt(user_id: str) -> str:
    load_dotenv()
    secret = os.environ["SUPABASE_JWT_SECRET"]
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, secret, algorithm="HS256")
