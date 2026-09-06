import os

import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException


def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    load_dotenv()
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="missing or invalid authorization header"
        )
    token = authorization.removeprefix("Bearer ")

    supabase_url = os.environ.get("SUPABASE_LOCAL_URL")
    if not supabase_url:
        raise RuntimeError(
            "SUPABASE_LOCAL_URL is not set. Run scripts/setup-sprint4-dev.sh "
            "and add it to your .env file."
        )
    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"

    try:
        jwks_client = jwt.PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token, signing_key.key, algorithms=["ES256"], audience="authenticated"
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid or expired token")

    return payload["sub"]
