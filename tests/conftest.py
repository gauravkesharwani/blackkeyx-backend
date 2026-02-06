"""Shared test fixtures and configuration."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Set test environment variables BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test.db"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["ADMIN_API_KEY"] = "test-api-key"
os.environ["OPENAI_API_KEY"] = "sk-test"

from app.main import app  # noqa: E402


@pytest.fixture
def api_key_headers() -> dict:
    """Headers with valid API key for authenticated requests."""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def invalid_headers() -> dict:
    """Headers with invalid API key."""
    return {"X-API-Key": "wrong-key"}


@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
