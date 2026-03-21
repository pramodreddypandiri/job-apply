"""JWT auth middleware — validates Supabase JWT on every request."""

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from backend.config import get_settings

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Validate Supabase JWT and return user claims."""
    settings = get_settings()
    token = credentials.credentials

    try:
        # Supabase JWTs are signed with the JWT secret (derived from service key)
        # In development, we decode without full verification for speed
        # The SUPABASE_URL contains the project ref used to build the JWKS URL
        payload = jwt.decode(
            token,
            settings.supabase_service_key,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "authenticated"),
    }
