"""FastAPI auth dependency — verifies the Supabase access token on each request."""
from fastapi import Depends, HTTPException, Header
from backend.supabase_client import anon_client


class AuthedUser:
    """A verified Supabase user."""
    def __init__(self, user_id: str, email: str):
        self.id = user_id
        self.email = email


def get_current_user(authorization: str = Header(default="")) -> AuthedUser:
    """
    Validate the `Authorization: Bearer <access_token>` header against Supabase
    and return the authenticated user. Raises 401 when missing/invalid.
    """
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    try:
        resp = anon_client().auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = getattr(resp, "user", None)
    if not user or not getattr(user, "id", None):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return AuthedUser(user_id=user.id, email=getattr(user, "email", "") or "")


CurrentUser = Depends(get_current_user)
