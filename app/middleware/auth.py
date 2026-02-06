"""
Admin authentication middleware.

Provides a FastAPI dependency that validates admin sessions via:
1. Session cookie (admin_session) - set by POST /api/v1/admin/auth
2. X-API-Key header - for programmatic access

The session cookie contains an HMAC-signed token to prevent forgery.
"""

import hashlib
import hmac
import logging

from fastapi import Cookie, Header, HTTPException, Request
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Derive a signing key from the admin password
_SIGNING_KEY = hashlib.sha256(settings.admin_password.encode()).digest()


def sign_session_token(payload: str) -> str:
    """Create an HMAC-signed session token."""
    signature = hmac.new(_SIGNING_KEY, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_session_token(token: str) -> bool:
    """Verify an HMAC-signed session token."""
    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        return False
    payload, signature = parts
    expected = hmac.new(_SIGNING_KEY, payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


async def require_admin(
    request: Request,
    admin_session: Optional[str] = Cookie(None),
    x_api_key: Optional[str] = Header(None),
) -> bool:
    """
    FastAPI dependency that requires admin authentication.

    Checks (in order):
    1. X-API-Key header matches admin_api_key setting
    2. admin_session cookie contains a valid signed token

    Raises HTTPException 401 if neither check passes.
    """
    # Check API key header
    if x_api_key and hmac.compare_digest(x_api_key, settings.admin_api_key):
        return True

    # Check session cookie
    if admin_session and verify_session_token(admin_session):
        return True

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide a valid session cookie or X-API-Key header.",
    )
