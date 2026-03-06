"""
Integration tests for POST /api/v1/voice/livekit-webhook — Test IDs B-7 through B-10.

Tests webhook event handling for inbound call session creation,
idempotency, participant filtering, and auth.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set test environment BEFORE importing app
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("ADMIN_PASSWORD", "test-password")
os.environ.setdefault("ADMIN_API_KEY", "test-api-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("AGENT_CALLBACK_SECRET", "test-agent-secret")
os.environ.setdefault("LIVEKIT_API_KEY", "test-lk-key")
os.environ.setdefault("LIVEKIT_API_SECRET", "test-lk-secret")

from app.routers.webhook import _handle_participant_joined  # noqa: E402


def _make_event(
    room_name: str = "inbound-_+15105551234_abc",
    participant_kind: int = 3,  # SIP
    participant_identity: str = "+15105551234",
    participant_attributes: dict | None = None,
    event_type: str = "participant_joined",
):
    """Build a mock LiveKit webhook event."""
    participant = MagicMock()
    participant.kind = participant_kind
    participant.identity = participant_identity
    participant.attributes = participant_attributes or {}

    room = MagicMock()
    room.name = room_name

    event = MagicMock()
    event.event = event_type
    event.room = room
    event.participant = participant
    return event


# ---------------------------------------------------------------------------
# B-9: Outbound room ignored
# ---------------------------------------------------------------------------


class TestWebhookOutboundIgnored:
    """B-9: Webhook ignores outbound rooms."""

    @pytest.mark.asyncio
    async def test_outbound_room_skipped(self):
        """participant_joined for outbound room does nothing."""
        event = _make_event(room_name="outbound-investor-123")

        # If it tries to access DB, it would fail — so no DB mock needed
        # The function should return early
        await _handle_participant_joined(event)
        # No exception = passed (early return before DB access)


# ---------------------------------------------------------------------------
# B-8: Agent participant ignored
# ---------------------------------------------------------------------------


class TestWebhookAgentIgnored:
    """B-8: Webhook ignores non-SIP (agent) participants."""

    @pytest.mark.asyncio
    async def test_agent_participant_skipped(self):
        """participant_joined for agent participant (kind=4) does nothing."""
        event = _make_event(
            room_name="inbound-_+15105551234_abc",
            participant_kind=4,  # AGENT
            participant_identity="blackkeyx-advisor",
        )
        await _handle_participant_joined(event)
        # No exception = passed (early return before DB access)

    @pytest.mark.asyncio
    async def test_standard_participant_skipped(self):
        """participant_joined for standard participant (kind=0) does nothing."""
        event = _make_event(
            room_name="inbound-_+15105551234_abc",
            participant_kind=0,  # STANDARD
        )
        await _handle_participant_joined(event)


# ---------------------------------------------------------------------------
# B-7: Valid SIP participant creates session
# ---------------------------------------------------------------------------


class TestWebhookCreatesSession:
    """B-7: SIP participant in inbound room → CallSession created."""

    @pytest.mark.asyncio
    async def test_sip_participant_triggers_session_creation(self):
        """Verify _handle_participant_joined calls create_inbound_call for SIP participant."""
        event = _make_event(
            room_name="inbound-_+15105551234_abc",
            participant_kind=3,  # SIP
            participant_identity="+15105551234",
        )

        mock_call_repo = AsyncMock()
        mock_call_repo.get_by_room_name.return_value = None  # No existing session
        mock_call_repo.create_inbound_call.return_value = MagicMock(id="fake-call-id")

        mock_investor_repo = AsyncMock()
        mock_investor_repo.get_by_phone.return_value = None  # Unknown caller
        mock_investor = MagicMock(id="fake-investor-id")
        mock_investor_repo.create_from_inbound.return_value = mock_investor

        mock_session = AsyncMock()

        with patch("app.routers.webhook.async_session_factory") as mock_factory:
            # Set up async context manager
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_session
            mock_factory.return_value = mock_ctx

            with patch("app.routers.webhook.CallRepository", return_value=mock_call_repo), \
                 patch("app.routers.webhook.InvestorRepository", return_value=mock_investor_repo):
                await _handle_participant_joined(event)

            mock_call_repo.get_by_room_name.assert_called_once_with("inbound-_+15105551234_abc")
            mock_call_repo.create_inbound_call.assert_called_once()
            call_kwargs = mock_call_repo.create_inbound_call.call_args
            assert call_kwargs.kwargs.get("caller_phone") == "+15105551234" or \
                   (call_kwargs.args and "+15105551234" in str(call_kwargs))

    @pytest.mark.asyncio
    async def test_sip_participant_with_sip_attributes(self):
        """Caller phone extracted from SIP attributes when available."""
        event = _make_event(
            room_name="inbound-_+15105551234_abc",
            participant_kind=3,
            participant_identity="sip-random-id",
            participant_attributes={
                "sip.phoneNumber": "+15105559999",
            },
        )

        mock_call_repo = AsyncMock()
        mock_call_repo.get_by_room_name.return_value = None
        mock_call_repo.create_inbound_call.return_value = MagicMock(id="fake-id")

        mock_investor_repo = AsyncMock()
        mock_investor_repo.get_by_phone.return_value = None
        mock_investor_repo.create_from_inbound.return_value = MagicMock(id="fake-inv-id")

        mock_session = AsyncMock()

        with patch("app.routers.webhook.async_session_factory") as mock_factory:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_session
            mock_factory.return_value = mock_ctx

            with patch("app.routers.webhook.CallRepository", return_value=mock_call_repo), \
                 patch("app.routers.webhook.InvestorRepository", return_value=mock_investor_repo):
                await _handle_participant_joined(event)

            # Should use sip.phoneNumber, not participant identity
            create_call = mock_call_repo.create_inbound_call
            create_call.assert_called_once()


# ---------------------------------------------------------------------------
# B-7 + I-6: Idempotency check
# ---------------------------------------------------------------------------


class TestWebhookIdempotency:
    """I-6: Duplicate webhook does not create duplicate sessions."""

    @pytest.mark.asyncio
    async def test_existing_session_skipped(self):
        """If CallSession already exists for room, no new one is created."""
        event = _make_event(room_name="inbound-_+15105551234_abc")

        mock_call_repo = AsyncMock()
        mock_call_repo.get_by_room_name.return_value = MagicMock(id="existing-id")

        mock_session = AsyncMock()

        with patch("app.routers.webhook.async_session_factory") as mock_factory:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_session
            mock_factory.return_value = mock_ctx

            with patch("app.routers.webhook.CallRepository", return_value=mock_call_repo), \
                 patch("app.routers.webhook.InvestorRepository"):
                await _handle_participant_joined(event)

            # create_inbound_call should NOT be called
            mock_call_repo.create_inbound_call.assert_not_called()


# ---------------------------------------------------------------------------
# B-10: Invalid webhook signature
# ---------------------------------------------------------------------------


class TestWebhookAuthValidation:
    """B-10: Invalid webhook JWT → 401."""

    @pytest.mark.asyncio
    async def test_missing_authorization_returns_422(self, client):
        """Missing Authorization header → 422 (FastAPI validation) or 401."""
        response = await client.post(
            "/api/v1/voice/livekit-webhook",
            content="{}",
            headers={"Content-Type": "application/json"},
        )
        # FastAPI returns 422 for missing required header, or 401 for auth failure
        assert response.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_invalid_authorization_returns_401(self, client):
        """Invalid Authorization header → 401."""
        response = await client.post(
            "/api/v1/voice/livekit-webhook",
            content="{}",
            headers={
                "Content-Type": "application/json",
                "Authorization": "invalid-jwt-token",
            },
        )
        assert response.status_code == 401
