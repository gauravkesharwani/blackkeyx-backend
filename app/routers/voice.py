"""
Voice API endpoints for call management.

Provides endpoints for:
- Getting call status
- Receiving session completion callbacks from LiveKit agent
- Managing call transcripts
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.call_repo import CallRepository
from app.db.session import get_db
from app.services.livekit_dispatcher import get_livekit_dispatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


class CallStatusResponse(BaseModel):
    """Response model for call status."""

    room_name: str
    status: str
    duration: Optional[int] = None
    has_transcript: bool = False


class SessionCompleteRequest(BaseModel):
    """Request model for session completion callback."""

    room_name: str
    transcript: str
    duration: int


class SessionCompleteResponse(BaseModel):
    """Response model for session completion."""

    success: bool
    call_id: Optional[str] = None


@router.get("/status/{room_name}", response_model=CallStatusResponse)
async def get_call_status(
    room_name: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get status of a voice call by room name.

    Returns the current status of the call including duration and
    whether a transcript is available.
    """
    repo = CallRepository(db)
    call = await repo.get_by_room_name(room_name)

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    return CallStatusResponse(
        room_name=room_name,
        status=call.status,
        duration=call.duration,
        has_transcript=call.transcript is not None,
    )


@router.post("/session-complete", response_model=SessionCompleteResponse)
async def session_complete(
    request: SessionCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Called by LiveKit agent when session ends.

    Saves the transcript and marks the call as completed.
    """
    logger.info(f"Session complete for room: {request.room_name}")

    repo = CallRepository(db)
    call = await repo.save_transcript(
        room_name=request.room_name,
        transcript=request.transcript,
        duration=request.duration,
    )

    if not call:
        logger.warning(f"Call not found for room: {request.room_name}")
        return SessionCompleteResponse(success=False)

    logger.info(f"Transcript saved for call: {call.id}")
    return SessionCompleteResponse(success=True, call_id=str(call.id))


@router.get("/room/{room_name}/active")
async def check_room_active(room_name: str):
    """
    Check if a LiveKit room is still active.

    Useful for polling call status from the frontend.
    """
    dispatcher = get_livekit_dispatcher()
    room_info = await dispatcher.get_room_status(room_name)

    return {
        "active": room_info is not None,
        "participants": room_info.get("num_participants", 0) if room_info else 0,
    }


@router.post("/room/{room_name}/end")
async def end_call(room_name: str):
    """
    Force end a call by deleting the room.

    Should only be used for administrative purposes.
    """
    dispatcher = get_livekit_dispatcher()
    success = await dispatcher.end_call(room_name)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to end call")

    return {"success": True}
