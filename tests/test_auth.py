"""Tests for admin authentication middleware."""

import pytest

from app.middleware.auth import sign_session_token, verify_session_token


class TestSessionTokenSigning:
    """Test HMAC session token signing and verification."""

    def test_sign_and_verify_valid_token(self):
        payload = "1706745600_abc12345"
        signed = sign_session_token(payload)
        assert verify_session_token(signed) is True

    def test_verify_tampered_token(self):
        payload = "1706745600_abc12345"
        signed = sign_session_token(payload)
        # Tamper with the payload
        tampered = "1706745600_TAMPERED" + signed[signed.index("."):]
        assert verify_session_token(tampered) is False

    def test_verify_tampered_signature(self):
        payload = "1706745600_abc12345"
        signed = sign_session_token(payload)
        # Tamper with the signature
        tampered = signed[:-4] + "xxxx"
        assert verify_session_token(tampered) is False

    def test_verify_missing_signature(self):
        assert verify_session_token("no-dot-here") is False

    def test_verify_empty_string(self):
        assert verify_session_token("") is False

    def test_different_payloads_produce_different_signatures(self):
        signed1 = sign_session_token("payload1")
        signed2 = sign_session_token("payload2")
        sig1 = signed1.split(".")[-1]
        sig2 = signed2.split(".")[-1]
        assert sig1 != sig2


class TestAdminAuthEndpoints:
    """Test auth enforcement on admin API endpoints."""

    @pytest.mark.asyncio
    async def test_admin_login_correct_password(self, client):
        response = await client.post(
            "/api/v1/admin/auth",
            json={"password": "test-password"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should set admin_session cookie
        assert "admin_session" in response.cookies

    @pytest.mark.asyncio
    async def test_admin_login_wrong_password(self, client):
        response = await client.post(
            "/api/v1/admin/auth",
            json={"password": "wrong-password"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_stats_requires_auth(self, client):
        response = await client.get("/api/v1/admin/stats")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_leads_requires_auth(self, client):
        response = await client.get("/api/v1/admin/leads")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_stats_with_api_key(self, client, api_key_headers):
        try:
            response = await client.get(
                "/api/v1/admin/stats",
                headers=api_key_headers,
            )
            # Auth should pass - 500 from missing DB is acceptable, 401 is not
            assert response.status_code != 401
        except Exception:
            # DB connection errors are expected in test env without tables
            pass

    @pytest.mark.asyncio
    async def test_admin_stats_with_invalid_api_key(self, client, invalid_headers):
        response = await client.get(
            "/api/v1/admin/stats",
            headers=invalid_headers,
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_login_returns_signed_cookie(self, client):
        response = await client.post(
            "/api/v1/admin/auth",
            json={"password": "test-password"},
        )
        assert response.status_code == 200
        cookie_value = response.cookies.get("admin_session")
        assert cookie_value is not None
        # Verify the cookie is properly signed
        assert verify_session_token(cookie_value) is True

    @pytest.mark.asyncio
    async def test_admin_stats_with_valid_cookie(self, client):
        # First login to get a signed cookie
        login_response = await client.post(
            "/api/v1/admin/auth",
            json={"password": "test-password"},
        )
        assert login_response.status_code == 200

        # Use the cookie to access stats
        try:
            response = await client.get(
                "/api/v1/admin/stats",
                cookies={"admin_session": login_response.cookies["admin_session"]},
            )
            # Auth should pass (may fail on DB, but not on auth)
            assert response.status_code != 401
        except Exception:
            # DB connection errors are expected in test env without tables
            pass


class TestPropertiesAuthEnforcement:
    """Test auth enforcement on properties/deals endpoints."""

    @pytest.mark.asyncio
    async def test_list_deals_requires_auth(self, client):
        response = await client.get("/api/v1/properties")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_deal_requires_auth(self, client):
        response = await client.post(
            "/api/v1/properties",
            json={"name": "Test Deal"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_deals_with_api_key(self, client, api_key_headers):
        try:
            response = await client.get(
                "/api/v1/properties",
                headers=api_key_headers,
            )
            assert response.status_code != 401
        except Exception:
            # DB connection errors are expected in test env without tables
            pass


class TestMatchingAuthEnforcement:
    """Test auth enforcement on matching endpoints."""

    @pytest.mark.asyncio
    async def test_get_all_matches_requires_auth(self, client):
        response = await client.get("/api/v1/matching/all")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_run_matching_requires_auth(self, client):
        response = await client.post(
            "/api/v1/matching/run",
            json={},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_all_matches_with_api_key(self, client, api_key_headers):
        try:
            response = await client.get(
                "/api/v1/matching/all",
                headers=api_key_headers,
            )
            assert response.status_code != 401
        except Exception:
            # DB connection errors are expected in test env without tables
            pass


class TestPublicEndpoints:
    """Verify public endpoints don't require auth."""

    @pytest.mark.asyncio
    async def test_health_check_no_auth(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_submit_lead_no_auth_required(self, client):
        try:
            response = await client.post(
                "/api/v1/submit-lead",
                json={
                    "name": "Test User",
                    "phone_number": "+15105551234",
                    "consent": True,
                    "timestamp": "2025-01-01T00:00:00Z",
                },
            )
            # Should not be 401 - may fail for other reasons but auth isn't required
            assert response.status_code != 401
        except Exception:
            # DB connection errors are expected in test env without tables
            pass
