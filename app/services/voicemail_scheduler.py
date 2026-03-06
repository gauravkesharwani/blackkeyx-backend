"""Voicemail retry scheduler — polls for due voicemail retries and redispatches calls."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VoicemailScheduler:
    """Polls the database for due voicemail retries and dispatches outbound calls."""

    def __init__(self) -> None:
        self._running = False
        self._dispatching: set[uuid.UUID] = set()

    async def run(self) -> None:
        """Main scheduler loop. Polls every `poll_interval` seconds."""
        self._running = True
        logger.info(
            "Voicemail retry scheduler started "
            f"(poll={settings.callback_poll_interval_seconds}s, "
            f"retry_delay={settings.voicemail_retry_delay_days}d, "
            f"max_retries={settings.voicemail_max_retries})"
        )

        while self._running:
            try:
                await self._poll_and_dispatch()
            except Exception:
                logger.exception("Voicemail scheduler poll error")

            for _ in range(settings.callback_poll_interval_seconds):
                if not self._running:
                    break
                await asyncio.sleep(1)

        logger.info("Voicemail retry scheduler stopped")

    def stop(self) -> None:
        """Signal the scheduler to stop after the current cycle."""
        self._running = False

    async def _poll_and_dispatch(self) -> None:
        """Query due voicemail retries and dispatch each one."""
        from app.db.repositories.call_repo import CallRepository
        from app.db.repositories.investor_repo import InvestorRepository
        from app.db.session import async_session_factory

        async with async_session_factory() as session:
            try:
                call_repo = CallRepository(session)
                investor_repo = InvestorRepository(session)

                due_retries = await call_repo.get_due_voicemail_retries(
                    grace_window_minutes=settings.callback_grace_window_minutes,
                )

                if not due_retries:
                    return

                logger.info(f"Found {len(due_retries)} due voicemail retry(ies)")

                for retry in due_retries:
                    if retry.id in self._dispatching:
                        continue

                    self._dispatching.add(retry.id)
                    try:
                        await self._dispatch_retry(
                            retry, call_repo, investor_repo
                        )
                    finally:
                        self._dispatching.discard(retry.id)

                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _dispatch_retry(
        self,
        retry,
        call_repo,
        investor_repo,
    ) -> None:
        """Dispatch a single voicemail retry call."""
        from app.services.livekit_dispatcher import get_livekit_dispatcher

        investor = await investor_repo.get(retry.investor_id)

        if not investor or not investor.phone:
            logger.warning(
                f"Cancelling voicemail retry {retry.id}: investor missing or no phone"
            )
            await call_repo.update_callback_status(
                retry.id, "cancelled", datetime.now(timezone.utc)
            )
            return

        # Count previous voicemail attempts
        total_attempts = await call_repo.count_voicemail_attempts(investor.id)
        if total_attempts >= settings.voicemail_max_retries:
            logger.info(
                f"Voicemail retry {retry.id}: max retries reached ({total_attempts}), "
                f"marking as cancelled"
            )
            await call_repo.update_callback_status(
                retry.id, "cancelled", datetime.now(timezone.utc)
            )
            await investor_repo.update_stage(
                investor_id=investor.id,
                new_stage="voicemail_max_retries",
                changed_by="voicemail_scheduler",
                notes=f"Max voicemail retries ({settings.voicemail_max_retries}) exhausted",
            )
            return

        investor_context = {
            "investor_id": str(investor.id),
            "name": investor.name or "there",
            "capital_available": investor.capacity or investor.capital_available,
            "timeline": investor.timeline,
            "investment_preferences": investor.investment_preferences or [],
            "outbound": True,
            "is_voicemail_retry": True,
        }

        livekit = get_livekit_dispatcher()
        room_name = await self._dispatch_with_retry(
            livekit, investor.phone, investor_context
        )

        if room_name is None:
            logger.error(
                f"All retries exhausted for voicemail retry {retry.id}, "
                f"will retry next cycle"
            )
            return

        await call_repo.create_call(
            investor_id=investor.id,
            room_name=room_name,
            status="initiated",
            retry_count=total_attempts + 1,
        )

        await investor_repo.update_stage(
            investor_id=investor.id,
            new_stage="call_dispatched",
            changed_by="voicemail_scheduler",
            notes=f"Voicemail retry #{total_attempts + 1} dispatched",
        )

        await call_repo.update_callback_status(
            retry.id, "completed", datetime.now(timezone.utc)
        )

        logger.info(
            f"Voicemail retry {retry.id} dispatched successfully "
            f"(room={room_name}, investor={investor.id}, attempt={total_attempts + 1})"
        )

    async def _dispatch_with_retry(
        self,
        livekit,
        phone_number: str,
        investor_context: dict,
    ) -> Optional[str]:
        """Attempt dispatch with exponential backoff. Returns room_name or None."""
        for attempt in range(settings.callback_max_retries):
            try:
                return await livekit.dispatch_outbound_call(
                    phone_number=phone_number,
                    investor_context=investor_context,
                )
            except Exception:
                wait = 2 ** (attempt + 1)
                logger.warning(
                    f"Voicemail dispatch attempt {attempt + 1}/{settings.callback_max_retries} "
                    f"failed, retrying in {wait}s",
                    exc_info=True,
                )
                await asyncio.sleep(wait)

        return None


# Singleton
_scheduler: Optional[VoicemailScheduler] = None


def get_voicemail_scheduler() -> VoicemailScheduler:
    """Get or create the voicemail scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = VoicemailScheduler()
    return _scheduler
