"""Callback scheduler service — polls for due callbacks and dispatches follow-up calls."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CallbackScheduler:
    """Polls the database for due callback requests and dispatches outbound calls."""

    def __init__(self) -> None:
        self._running = False
        self._dispatching: set[uuid.UUID] = set()  # in-flight callback IDs

    async def run(self) -> None:
        """Main scheduler loop. Polls every `poll_interval` seconds."""
        self._running = True
        logger.info(
            "Callback scheduler started "
            f"(poll={settings.callback_poll_interval_seconds}s, "
            f"grace={settings.callback_grace_window_minutes}min)"
        )

        while self._running:
            try:
                await self._poll_and_dispatch()
            except Exception:
                logger.exception("Callback scheduler poll error")

            # Sleep in 1-second increments so stop() takes effect quickly
            for _ in range(settings.callback_poll_interval_seconds):
                if not self._running:
                    break
                await asyncio.sleep(1)

        logger.info("Callback scheduler stopped")

    def stop(self) -> None:
        """Signal the scheduler to stop after the current cycle."""
        self._running = False

    async def _poll_and_dispatch(self) -> None:
        """Query due callbacks and dispatch each one."""
        from app.db.repositories.call_repo import CallRepository
        from app.db.repositories.investor_repo import InvestorRepository
        from app.db.session import async_session_factory

        async with async_session_factory() as session:
            try:
                call_repo = CallRepository(session)
                investor_repo = InvestorRepository(session)

                due_callbacks = await call_repo.get_due_callbacks(
                    grace_window_minutes=settings.callback_grace_window_minutes,
                )

                if not due_callbacks:
                    return

                logger.info(f"Found {len(due_callbacks)} due callback(s)")

                for callback in due_callbacks:
                    if callback.id in self._dispatching:
                        continue  # already being dispatched

                    self._dispatching.add(callback.id)
                    try:
                        await self._dispatch_callback(
                            callback, call_repo, investor_repo
                        )
                    finally:
                        self._dispatching.discard(callback.id)

                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _dispatch_callback(
        self,
        callback,
        call_repo,
        investor_repo,
    ) -> None:
        """Dispatch a single callback — mirrors admin_service dispatch logic."""
        from app.services.livekit_dispatcher import get_livekit_dispatcher

        investor = await investor_repo.get(callback.investor_id)

        if not investor or not investor.phone:
            logger.warning(
                f"Cancelling callback {callback.id}: "
                f"investor missing or no phone"
            )
            await call_repo.update_callback_status(
                callback.id, "cancelled", datetime.now(timezone.utc)
            )
            return

        investor_context = {
            "investor_id": str(investor.id),
            "name": investor.name or "there",
            "capital_available": investor.capacity or investor.capital_available,
            "timeline": investor.timeline,
            "investment_preferences": investor.investment_preferences or [],
            "is_callback": True,
        }

        # Dispatch with retry
        livekit = get_livekit_dispatcher()
        room_name = await self._dispatch_with_retry(
            livekit, investor.phone, investor_context
        )

        if room_name is None:
            # All retries exhausted — leave as pending for next cycle
            logger.error(
                f"All retries exhausted for callback {callback.id}, "
                f"will retry next cycle"
            )
            return

        # Create call session record
        await call_repo.create_call(
            investor_id=investor.id,
            room_name=room_name,
            status="initiated",
        )

        # Update investor stage
        await investor_repo.update_stage(
            investor_id=investor.id,
            new_stage="call_dispatched",
            changed_by="callback_scheduler",
            notes=f"Auto-dispatched callback (requested: {callback.requested_datetime_raw})",
        )

        # Mark callback completed
        await call_repo.update_callback_status(
            callback.id, "completed", datetime.now(timezone.utc)
        )

        logger.info(
            f"Callback {callback.id} dispatched successfully "
            f"(room={room_name}, investor={investor.id})"
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
                wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                logger.warning(
                    f"Dispatch attempt {attempt + 1}/{settings.callback_max_retries} "
                    f"failed, retrying in {wait}s",
                    exc_info=True,
                )
                await asyncio.sleep(wait)

        return None


# Singleton
_scheduler: Optional[CallbackScheduler] = None


def get_callback_scheduler() -> CallbackScheduler:
    """Get or create the callback scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = CallbackScheduler()
    return _scheduler
