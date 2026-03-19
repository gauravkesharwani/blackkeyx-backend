"""
Investor Portal JWT authentication middleware.

Handles Google ID token verification and our own JWT issuance.
Entirely separate from the admin HMAC-cookie auth in auth.py.

Flow:
  1. Frontend sends Google ID token to POST /api/v1/investor/auth/google
  2. We verify it with google-auth library
  3. We issue our own short-lived access JWT + long-lived refresh JWT
  4. Next.js BFF stores both as httpOnly cookies
  5. Every protected request reads the access token cookie via require_investor()
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Cookie, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleTokenInfo(BaseModel):
    sub: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


class TokenPayload(BaseModel):
    sub: str   # investor_user_id as string
    email: str
    type: str  # access | refresh
    exp: int


def verify_google_id_token(token: str) -> GoogleTokenInfo:
    """
    Verify a Google ID token and return user info.
    Raises HTTPException 401 if invalid.
    """
    try:
        info = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.google_client_id,
        )
        return GoogleTokenInfo(
            sub=info["sub"],
            email=info["email"],
            name=info.get("name"),
            picture=info.get("picture"),
        )
    except ValueError as e:
        logger.warning("Invalid Google ID token: %s", e)
        raise HTTPException(status_code=401, detail="Invalid Google ID token")


def create_access_token(investor_user_id: uuid.UUID, email: str) -> str:
    """Create a short-lived JWT access token (60 min)."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": str(investor_user_id),
        "email": email,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(investor_user_id: uuid.UUID, email: str) -> str:
    """Create a long-lived JWT refresh token (30 days)."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": str(investor_user_id),
        "email": email,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    try:
        raw = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(**raw)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


async def require_investor(
    investor_access_token: Optional[str] = Cookie(None),
) -> uuid.UUID:
    """
    FastAPI dependency for investor-protected routes.
    Reads 'investor_access_token' httpOnly cookie set by Next.js BFF.
    Returns the investor_user_id UUID.
    """
    if not investor_access_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = decode_token(investor_access_token)

    if payload.type != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    return uuid.UUID(payload.sub)
