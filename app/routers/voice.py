"""
Voice API endpoints for call management.

Provides endpoints for:
- Getting call status
- Receiving session completion callbacks from LiveKit agent
- Managing call transcripts
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_voice_service
from app.services.voice_service import VoiceService

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
    duration: Optional[int] = None
    history: Optional[list[dict[str, Any]]] = None
    # Callback request fields
    callback_requested: bool = False
    callback_datetime: Optional[str] = None
    callback_notes: Optional[str] = None


class SessionCompleteResponse(BaseModel):
    """Response model for session completion."""

    success: bool
    call_id: Optional[str] = None


@router.get("/status/{room_name}", response_model=CallStatusResponse)
async def get_call_status(
    room_name: str,
    voice_service: VoiceService = Depends(get_voice_service),
):
    """
    Get status of a voice call by room name.

    Returns the current status of the call including duration and
    whether a transcript is available.
    """
    call = await voice_service.get_call_status(room_name)

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
    voice_service: VoiceService = Depends(get_voice_service),
):
    """
    Called by LiveKit agent when session ends.

    Saves the transcript and marks the call as completed.
    Handles callback requests if the user requested to be called back later.
    """
    logger.info(f"Session complete for room: {request.room_name}")

    if request.callback_requested:
        logger.info(f"Callback requested for: {request.callback_datetime}")

    call = await voice_service.complete_session(
        room_name=request.room_name,
        transcript=request.transcript,
        duration=request.duration,
        history=request.history,
        callback_requested=request.callback_requested,
        callback_datetime=request.callback_datetime,
        callback_notes=request.callback_notes,
    )

    if not call:
        return SessionCompleteResponse(success=False)

    return SessionCompleteResponse(success=True, call_id=str(call.id))


@router.get("/room/{room_name}/active")
async def check_room_active(
    room_name: str,
    voice_service: VoiceService = Depends(get_voice_service),
):
    """
    Check if a LiveKit room is still active.

    Useful for polling call status from the frontend.
    """
    return await voice_service.check_room_active(room_name)


@router.post("/room/{room_name}/end")
async def end_call(
    room_name: str,
    voice_service: VoiceService = Depends(get_voice_service),
):
    """
    Force end a call by deleting the room.

    Should only be used for administrative purposes.
    """
    success = await voice_service.end_call(room_name)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to end call")

    return {"success": True}
