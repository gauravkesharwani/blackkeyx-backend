"""Voice service for call management operations."""

import asyncio
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import dateparser
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.repositories.call_repo import CallRepository
from app.db.repositories.investor_repo import InvestorRepository
from app.models.voice import CallSession
from app.services.livekit_dispatcher import get_livekit_dispatcher

settings = get_settings()

logger = logging.getLogger(__name__)


def _compute_duration_from_history(history: list[dict[str, Any]]) -> Optional[int]:
    """Compute call duration in seconds from history timestamps."""
    timestamps: list[float] = []

    for item in history:
        if item.get("type") != "message":
            continue
        metrics = item.get("metrics", {})
        started = metrics.get("started_speaking_at")
        stopped = metrics.get("stopped_speaking_at")

        if started is not None:
            timestamps.append(started)
        if stopped is not None:
            timestamps.append(stopped)

    if len(timestamps) >= 2:
        return int(max(timestamps) - min(timestamps))
    return None


class VoiceService:
    """Service for voice/call operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.call_repo = CallRepository(session)
        self.investor_repo = InvestorRepository(session)
        self.livekit = get_livekit_dispatcher()

    async def complete_session(
        self,
        room_name: str,
        transcript: str,
        duration: Optional[int] = None,
        history: Optional[list[dict[str, Any]]] = None,
        voicemail_detected: bool = False,
        voicemail_confidence: float = 0.0,
        voicemail_message_left: bool = False,
        callback_requested: bool = False,
        callback_datetime: Optional[str] = None,
        callback_notes: Optional[str] = None,
        investor_timezone: Optional[str] = None,
    ) -> Optional[CallSession]:
        """
        Complete a call session - save transcript and update investor stage.
        Handles callback requests if the user requested to be called back later.

        Returns the updated CallSession or None if not found.
        """
        # Compute duration from history if not provided
        if duration is None and history:
            duration = _compute_duration_from_history(history)

        # Save transcript and mark call completed
        call = await self.call_repo.save_transcript(
            room_name=room_name,
            transcript=transcript,
            duration=duration or 0,
        )

        if not call:
            logger.warning(f"Call not found for room: {room_name}")
            return None

        # Save detailed transcript segments from history
        if history:
            await self._save_transcript_segments(call.id, history)

        # Handle voicemail detection
        if voicemail_detected:
            await self.call_repo.update_status(call.id, "voicemail")
            await self.call_repo.update_voicemail_fields(
                call.id,
                voicemail_detected=True,
                voicemail_confidence=voicemail_confidence,
                voicemail_message_left=voicemail_message_left,
            )

            # Check retry count
            total_attempts = await self.call_repo.count_voicemail_attempts(call.investor_id)
            if total_attempts < settings.voicemail_max_retries:
                retry_at = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.voicemail_retry_delay_minutes
                )
                await self.call_repo.create_voicemail_retry(
                    call.investor_id, call.id, retry_at
                )
                await self.investor_repo.update_stage(
                    investor_id=call.investor_id,
                    new_stage="voicemail_retry_scheduled",
                    changed_by="system",
                    notes=f"Voicemail detected (confidence: {voicemail_confidence:.0%}), retry scheduled",
                )
            else:
                await self.investor_repo.update_stage(
                    investor_id=call.investor_id,
                    new_stage="voicemail_max_retries",
                    changed_by="system",
                    notes=f"Voicemail max retries ({settings.voicemail_max_retries}) exhausted",
                )

            await self.session.commit()
            logger.info(
                f"Voicemail detected for call {call.id} "
                f"(confidence={voicemail_confidence}, attempts={total_attempts})"
            )
            return call

        # Handle callback request
        if callback_requested and callback_datetime:
            # Save investor timezone if provided (normalize to IANA)
            if investor_timezone:
                investor = await self.investor_repo.get(call.investor_id)
                if investor:
                    from app.utils.timezone import _normalize_tz
                    investor.timezone = _normalize_tz(investor_timezone) or investor_timezone
                    await self.session.flush()

            # Resolve timezone for dateparser
            from app.utils.timezone import get_investor_timezone

            investor = await self.investor_repo.get(call.investor_id)
            tz_name = get_investor_timezone(
                getattr(investor, "timezone", None),
                investor.phone if investor else None,
            )

            # Parse the datetime using dateparser with timezone awareness
            # Strip timezone references from the string since we handle
            # timezone separately via the TIMEZONE setting — leaving them in
            # can cause dateparser to return None.
            clean_dt = re.sub(
                r"\b(pacific|eastern|central|mountain|[PMCE][SD]T)\s*(time(zone)?)?\b",
                "",
                callback_datetime,
                flags=re.IGNORECASE,
            ).strip()
            # Normalize "X from now" → "in X" which dateparser handles better
            clean_dt = re.sub(
                r"(\d+\s+\w+)\s+from\s+now",
                r"in \1",
                clean_dt,
                flags=re.IGNORECASE,
            )
            logger.info(
                f"Parsing callback datetime: raw={callback_datetime!r}, "
                f"cleaned={clean_dt!r}, tz={tz_name}"
            )

            parsed_dt = None
            try:
                parsed_dt = dateparser.parse(
                    clean_dt,
                    settings={
                        "PREFER_DATES_FROM": "future",
                        "TIMEZONE": tz_name,
                        "RETURN_AS_TIMEZONE_AWARE": True,
                        "TO_TIMEZONE": "UTC",
                    },
                )
                # Fallback: try the original string without timezone settings
                if parsed_dt is None:
                    parsed_dt = dateparser.parse(
                        callback_datetime,
                        settings={"PREFER_DATES_FROM": "future"},
                    )
                    logger.info(
                        f"Fallback parse result: {parsed_dt}"
                    )
            except Exception as e:
                logger.warning(f"Could not parse callback datetime: {e}")

            # Create callback request record
            await self.call_repo.create_callback_request(
                investor_id=call.investor_id,
                call_session_id=call.id,
                requested_datetime_raw=callback_datetime,
                requested_datetime=parsed_dt,
                notes=callback_notes,
            )

            # Update investor stage to callback_requested
            await self.investor_repo.update_stage(
                investor_id=call.investor_id,
                new_stage="callback_requested",
                changed_by="system",
                notes=f"Callback requested for: {callback_datetime}",
            )
            logger.info(f"Callback request created for investor: {call.investor_id}")
        else:
            # Normal call completion
            await self.investor_repo.update_stage(
                investor_id=call.investor_id,
                new_stage="call_completed",
                changed_by="system",
                notes="Call completed automatically",
            )

        await self.session.commit()
        logger.info(f"Session completed for call: {call.id}")

        # Trigger async insight extraction (fire-and-forget)
        # Only extract if we have a transcript and it's not a callback request
        if transcript and not callback_requested:
            asyncio.create_task(
                self._extract_insights_background(call.investor_id, call.id, transcript)
            )

        return call

    async def _save_transcript_segments(
        self,
        call_id: Any,
        history: list[dict[str, Any]],
    ) -> None:
        """Parse history items and save as transcript segments."""
        for item in history:
            if item.get("type") != "message":
                continue

            role = item.get("role", "")
            content_list = item.get("content", [])
            content = " ".join(c for c in content_list if isinstance(c, str))

            if not content:
                continue

            # Map role to speaker
            speaker = "agent" if role == "assistant" else "investor"

            # Extract metrics
            metrics = item.get("metrics", {})
            start_time = metrics.get("started_speaking_at")
            end_time = metrics.get("stopped_speaking_at")
            confidence = item.get("transcript_confidence")

            await self.call_repo.add_transcript_segment(
                call_session_id=call_id,
                speaker=speaker,
                content=content,
                start_time=start_time,
                end_time=end_time,
                confidence=confidence,
            )

    async def get_call_status(self, room_name: str) -> Optional[CallSession]:
        """Get call status by room name."""
        return await self.call_repo.get_by_room_name(room_name)

    async def check_room_active(self, room_name: str) -> dict:
        """Check if a LiveKit room is still active."""
        room_info = await self.livekit.get_room_status(room_name)
        return {
            "active": room_info is not None,
            "participants": room_info.get("num_participants", 0) if room_info else 0,
        }

    async def end_call(self, room_name: str) -> bool:
        """Force end a call by deleting the room."""
        return await self.livekit.end_call(room_name)

    async def _extract_insights_background(
        self,
        investor_id: uuid.UUID,
        call_id: uuid.UUID,
        transcript: str,
    ) -> None:
        """Background task to extract insights from transcript.

        Creates a new database session since this runs asynchronously
        after the original request has completed.
        """
        try:
            # Import here to avoid circular imports
            from app.db.session import async_session_factory
            from app.services.insight_extraction_service import InsightExtractionService

            async with async_session_factory() as session:
                extraction_service = InsightExtractionService(session)
                await extraction_service.extract_and_save(
                    investor_id=investor_id,
                    call_session_id=call_id,
                    transcript=transcript,
                )
        except Exception as e:
            logger.error(f"Background insight extraction failed for call {call_id}: {e}")
