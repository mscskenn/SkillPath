import os
import time

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

    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "SUPABASE_JWT_SECRET is not set. Run scripts/setup-sprint4-dev.sh "
            "and add it to your .env file."
        )

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid or expired token")

    return payload["sub"]
