"""
Voice API endpoints for call management.

Provides endpoints for:
- Getting call status
- Receiving session completion callbacks from LiveKit agent
- Managing call transcripts
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.db.session import async_session_factory
from app.db.repositories.investor_repo import InvestorRepository
from app.dependencies import get_voice_service
from app.middleware.auth import require_agent_auth, verify_agent_signature
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
    # Voicemail detection fields
    voicemail_detected: bool = False
    voicemail_confidence: float = 0.0
    voicemail_message_left: bool = False
    # Inbound call fields
    caller_phone: Optional[str] = None  # Caller's phone number (E.164), set for inbound calls
    caller_name: Optional[str] = None   # Caller's name as collected during the call
    # Callback request fields
    callback_requested: bool = False
    callback_datetime: Optional[str] = None
    callback_notes: Optional[str] = None
    investor_timezone: Optional[str] = None  # IANA timezone confirmed during call


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


@router.post("/inbound-context")
async def get_inbound_context(
    request: Request,
    x_agent_signature: Optional[str] = None,
):
    """
    Called by the agent at the start of an inbound call to fetch investor context.
    Returns known profile data so the agent can personalize the conversation.
    Secured with the same HMAC signature as session-complete.
    """
    from fastapi import Header
    x_agent_signature = request.headers.get("X-Agent-Signature")
    if not x_agent_signature:
        raise HTTPException(status_code=401, detail="Missing X-Agent-Signature header.")
    body = await request.body()
    if not verify_agent_signature(body, x_agent_signature):
        raise HTTPException(status_code=401, detail="Invalid agent signature.")

    import json as _json
    try:
        data = _json.loads(body)
        phone = data.get("phone")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    if not phone:
        raise HTTPException(status_code=400, detail="phone is required.")

    async with async_session_factory() as session:
        investor_repo = InvestorRepository(session)
        investor = await investor_repo.get_by_phone(phone)

    if not investor:
        return {"found": False}

    return {
        "found": True,
        "name": investor.name or "",
        "stage": investor.stage,
        "capital_available": investor.capital_available,
        "timeline": investor.timeline,
        "investment_preferences": list(investor.investment_preferences or []),
        "risk_tolerance": investor.risk_tolerance,
        "qualification_bucket": investor.qualification_bucket,
        "investment_thesis": investor.investment_thesis,
    }


@router.post("/session-complete", response_model=SessionCompleteResponse)
async def session_complete(
    request: SessionCompleteRequest,
    voice_service: VoiceService = Depends(get_voice_service),
    _agent_auth: bool = Depends(require_agent_auth),
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
        caller_phone=request.caller_phone,
        caller_name=request.caller_name,
        voicemail_detected=request.voicemail_detected,
        voicemail_confidence=request.voicemail_confidence,
        voicemail_message_left=request.voicemail_message_left,
        callback_requested=request.callback_requested,
        callback_datetime=request.callback_datetime,
        callback_notes=request.callback_notes,
        investor_timezone=request.investor_timezone,
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
