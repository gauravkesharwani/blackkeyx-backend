"""
Tests for VoicemailScheduler — Test IDs S-1 through S-5.

Tests the voicemail retry scheduler's poll-and-dispatch logic,
max retry enforcement, and edge cases.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("ADMIN_PASSWORD", "test-password")
os.environ.setdefault("ADMIN_API_KEY", "test-api-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("AGENT_CALLBACK_SECRET", "test-agent-secret")

from app.services.voicemail_scheduler import VoicemailScheduler  # noqa: E402


def _make_retry(
    investor_id=None,
    retry_id=None,
    requested_datetime=None,
):
    """Build a mock CallbackRequest representing a voicemail retry."""
    retry = MagicMock()
    retry.id = retry_id or uuid.uuid4()
    retry.investor_id = investor_id or uuid.uuid4()
    retry.requested_datetime_raw = "voicemail_retry"
    retry.requested_datetime = requested_datetime or (
        datetime.now(timezone.utc) - timedelta(minutes=5)
    )
    retry.status = "pending"
    return retry


def _make_investor(investor_id=None, phone="+15105551234", name="Test Investor"):
    investor = MagicMock()
    investor.id = investor_id or uuid.uuid4()
    investor.phone = phone
    investor.name = name
    investor.capacity = None
    investor.capital_available = "$1M"
    investor.timeline = "3 months"
    investor.investment_preferences = ["industrial"]
    return investor


# Patch targets: the scheduler uses deferred imports inside _poll_and_dispatch,
# so we patch at the source modules.
_PATCHES_VM = {
    "session_factory": "app.db.session.async_session_factory",
    "call_repo_cls": "app.db.repositories.call_repo.CallRepository",
    "investor_repo_cls": "app.db.repositories.investor_repo.InvestorRepository",
    "livekit": "app.services.livekit_dispatcher.get_livekit_dispatcher",
}

_PATCHES_CB = {
    "session_factory": "app.db.session.async_session_factory",
    "call_repo_cls": "app.db.repositories.call_repo.CallRepository",
    "investor_repo_cls": "app.db.repositories.investor_repo.InvestorRepository",
    "livekit": "app.services.livekit_dispatcher.get_livekit_dispatcher",
}


def _setup_session_mock(mock_factory, mock_session):
    """Configure the async_session_factory mock to return mock_session as context manager."""
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_session
    mock_factory.return_value = mock_ctx


# ---------------------------------------------------------------------------
# S-1: Happy path — retry dispatched
# ---------------------------------------------------------------------------


class TestVoicemailRetryHappyPath:
    """S-1: Due retry is dispatched, new CallSession created, callback marked completed."""

    @pytest.mark.asyncio
    async def test_dispatch_retry_success(self):
        scheduler = VoicemailScheduler()
        investor_id = uuid.uuid4()
        retry = _make_retry(investor_id=investor_id)
        investor = _make_investor(investor_id=investor_id)

        mock_call_repo = AsyncMock()
        mock_call_repo.get_due_voicemail_retries.return_value = [retry]
        mock_call_repo.count_voicemail_attempts.return_value = 0
        mock_call_repo.create_call.return_value = MagicMock(id=uuid.uuid4())

        mock_investor_repo = AsyncMock()
        mock_investor_repo.get.return_value = investor

        mock_livekit = AsyncMock()
        mock_livekit.dispatch_outbound_call.return_value = "outbound-retry-room-123"

        mock_session = AsyncMock()

        with patch(_PATCHES_VM["session_factory"]) as mock_factory, \
             patch(_PATCHES_VM["call_repo_cls"], return_value=mock_call_repo), \
             patch(_PATCHES_VM["investor_repo_cls"], return_value=mock_investor_repo), \
             patch(_PATCHES_VM["livekit"], return_value=mock_livekit):

            _setup_session_mock(mock_factory, mock_session)
            await scheduler._poll_and_dispatch()

        mock_livekit.dispatch_outbound_call.assert_called_once()
        mock_call_repo.create_call.assert_called_once()
        create_kwargs = mock_call_repo.create_call.call_args.kwargs
        assert create_kwargs["retry_count"] == 1
        assert create_kwargs["investor_id"] == investor_id
        mock_call_repo.update_callback_status.assert_called_once()
        status_args = mock_call_repo.update_callback_status.call_args
        assert status_args.args[0] == retry.id
        assert status_args.args[1] == "completed"


# ---------------------------------------------------------------------------
# S-2: Retry hits max retries
# ---------------------------------------------------------------------------


class TestVoicemailRetryMaxReached:
    """S-2: Retry cancelled when max retries already exhausted."""

    @pytest.mark.asyncio
    async def test_max_retries_cancels(self):
        scheduler = VoicemailScheduler()
        investor_id = uuid.uuid4()
        retry = _make_retry(investor_id=investor_id)
        investor = _make_investor(investor_id=investor_id)

        mock_call_repo = AsyncMock()
        mock_call_repo.get_due_voicemail_retries.return_value = [retry]
        mock_call_repo.count_voicemail_attempts.return_value = 1  # At max

        mock_investor_repo = AsyncMock()
        mock_investor_repo.get.return_value = investor

        mock_session = AsyncMock()

        with patch(_PATCHES_VM["session_factory"]) as mock_factory, \
             patch(_PATCHES_VM["call_repo_cls"], return_value=mock_call_repo), \
             patch(_PATCHES_VM["investor_repo_cls"], return_value=mock_investor_repo):

            _setup_session_mock(mock_factory, mock_session)
            await scheduler._poll_and_dispatch()

        mock_call_repo.update_callback_status.assert_called_once()
        status_args = mock_call_repo.update_callback_status.call_args
        assert status_args.args[1] == "cancelled"
        mock_investor_repo.update_stage.assert_called_once()
        stage_kwargs = mock_investor_repo.update_stage.call_args.kwargs
        assert stage_kwargs["new_stage"] == "voicemail_max_retries"
        mock_call_repo.create_call.assert_not_called()


# ---------------------------------------------------------------------------
# S-3: Callback scheduler happy path
# ---------------------------------------------------------------------------


class TestCallbackSchedulerHappyPath:
    """S-3: Callback scheduler dispatches due callbacks."""

    @pytest.mark.asyncio
    async def test_dispatch_callback_success(self):
        from app.services.callback_scheduler import CallbackScheduler

        scheduler = CallbackScheduler()
        investor_id = uuid.uuid4()

        callback = MagicMock()
        callback.id = uuid.uuid4()
        callback.investor_id = investor_id
        callback.requested_datetime_raw = "Tuesday at 2pm"

        investor = _make_investor(investor_id=investor_id)

        mock_call_repo = AsyncMock()
        mock_call_repo.get_due_callbacks.return_value = [callback]

        mock_investor_repo = AsyncMock()
        mock_investor_repo.get.return_value = investor

        mock_livekit = AsyncMock()
        mock_livekit.dispatch_outbound_call.return_value = "outbound-callback-room"

        mock_session = AsyncMock()

        with patch(_PATCHES_CB["session_factory"]) as mock_factory, \
             patch(_PATCHES_CB["call_repo_cls"], return_value=mock_call_repo), \
             patch(_PATCHES_CB["investor_repo_cls"], return_value=mock_investor_repo), \
             patch(_PATCHES_CB["livekit"], return_value=mock_livekit):

            _setup_session_mock(mock_factory, mock_session)
            await scheduler._poll_and_dispatch()

        mock_livekit.dispatch_outbound_call.assert_called_once()
        mock_call_repo.create_call.assert_called_once()
        mock_call_repo.update_callback_status.assert_called_once()


# ---------------------------------------------------------------------------
# S-4: Retry not yet due
# ---------------------------------------------------------------------------


class TestVoicemailRetryNotDue:
    """S-4: Future retry is NOT picked up by scheduler."""

    @pytest.mark.asyncio
    async def test_no_due_retries_does_nothing(self):
        scheduler = VoicemailScheduler()

        mock_call_repo = AsyncMock()
        mock_call_repo.get_due_voicemail_retries.return_value = []

        mock_session = AsyncMock()

        with patch(_PATCHES_VM["session_factory"]) as mock_factory, \
             patch(_PATCHES_VM["call_repo_cls"], return_value=mock_call_repo), \
             patch(_PATCHES_VM["investor_repo_cls"]):

            _setup_session_mock(mock_factory, mock_session)
            await scheduler._poll_and_dispatch()

        mock_call_repo.create_call.assert_not_called()
        mock_call_repo.update_callback_status.assert_not_called()


# ---------------------------------------------------------------------------
# S-5: Investor missing / no phone
# ---------------------------------------------------------------------------


class TestVoicemailRetryMissingInvestor:
    """S-5: Retry cancelled if investor is missing or has no phone."""

    @pytest.mark.asyncio
    async def test_missing_investor_cancels_retry(self):
        scheduler = VoicemailScheduler()
        retry = _make_retry()

        mock_call_repo = AsyncMock()
        mock_call_repo.get_due_voicemail_retries.return_value = [retry]

        mock_investor_repo = AsyncMock()
        mock_investor_repo.get.return_value = None

        mock_session = AsyncMock()

        with patch(_PATCHES_VM["session_factory"]) as mock_factory, \
             patch(_PATCHES_VM["call_repo_cls"], return_value=mock_call_repo), \
             patch(_PATCHES_VM["investor_repo_cls"], return_value=mock_investor_repo):

            _setup_session_mock(mock_factory, mock_session)
            await scheduler._poll_and_dispatch()

        mock_call_repo.update_callback_status.assert_called_once()
        status_args = mock_call_repo.update_callback_status.call_args
        assert status_args.args[1] == "cancelled"
        mock_call_repo.create_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_phone_cancels_retry(self):
        scheduler = VoicemailScheduler()
        retry = _make_retry()
        investor = _make_investor(phone=None)

        mock_call_repo = AsyncMock()
        mock_call_repo.get_due_voicemail_retries.return_value = [retry]

        mock_investor_repo = AsyncMock()
        mock_investor_repo.get.return_value = investor

        mock_session = AsyncMock()

        with patch(_PATCHES_VM["session_factory"]) as mock_factory, \
             patch(_PATCHES_VM["call_repo_cls"], return_value=mock_call_repo), \
             patch(_PATCHES_VM["investor_repo_cls"], return_value=mock_investor_repo):

            _setup_session_mock(mock_factory, mock_session)
            await scheduler._poll_and_dispatch()

        mock_call_repo.update_callback_status.assert_called_once()
        status_args = mock_call_repo.update_callback_status.call_args
        assert status_args.args[1] == "cancelled"
