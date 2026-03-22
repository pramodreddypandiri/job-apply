"""JWT auth middleware — validates Supabase JWT on every request."""

from functools import lru_cache
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, jwk, JWTError
from loguru import logger
import httpx
from backend.config import get_settings

security = HTTPBearer()


@lru_cache
def _get_jwks_key():
    """Fetch and cache the Supabase JWKS public key."""
    settings = get_settings()
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    resp = httpx.get(jwks_url, timeout=10)
    resp.raise_for_status()
    keys = resp.json()["keys"]
    return jwk.construct(keys[0])


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Validate Supabase JWT and return user claims."""
    settings = get_settings()
    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg == "HS256":
            payload = jwt.decode(
                token, settings.supabase_jwt_secret, algorithms=["HS256"],
                options={"verify_aud": False},
            )
        else:
            key = _get_jwks_key()
            payload = jwt.decode(
                token, key, algorithms=[alg], options={"verify_aud": False},
            )
    except JWTError as e:
        logger.error(f"JWT decode failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "authenticated"),
    }
