import re
from typing import Optional

from fastapi import Header, HTTPException

from . import config

_UID_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


def current_user(
    x_user_id: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
) -> str:
    """Resolve the caller.

    - With Supabase configured and a Bearer token: verify the token and use the Supabase user id.
    - Otherwise: use the anonymous X-User-Id header (the web app generates one per browser).
    """
    if authorization and authorization.lower().startswith("bearer ") and config.supabase_enabled():
        token = authorization.split(" ", 1)[1].strip()
        try:
            from .store import supabase_client

            user = supabase_client().auth.get_user(token).user
            if user and user.id:
                return str(user.id)
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if x_user_id and _UID_RE.match(x_user_id):
        return x_user_id
    raise HTTPException(status_code=401, detail="Missing or invalid X-User-Id header")
