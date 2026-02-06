"""
Rate limiting middleware using slowapi.

Provides:
- A configured Limiter instance for per-route decorators
- A key function that extracts client IP (respecting X-Forwarded-For behind ALB)
- A global default rate limit applied via SlowAPIMiddleware
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import get_settings

settings = get_settings()


def _get_client_ip(request: Request) -> str:
    """Extract client IP, checking X-Forwarded-For first for ALB/proxy setups."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_client_ip,
    default_limits=[settings.rate_limit_global],
    storage_uri="memory://",
)
