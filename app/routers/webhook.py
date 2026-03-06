"""LiveKit webhook handler for real-time call event tracking."""

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from livekit import api

from app.config import get_settings
from app.db.session import async_session_factory
from app.db.repositories.call_repo import CallRepository
from app.db.repositories.investor_repo import InvestorRepository

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/voice", tags=["voice-webhook"])

_webhook_receiver = None


def get_webhook_receiver() -> api.WebhookReceiver:
    global _webhook_receiver
    if _webhook_receiver is None:
        token_verifier = api.TokenVerifier(
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
        _webhook_receiver = api.WebhookReceiver(token_verifier)
    return _webhook_receiver


@router.post("/livekit-webhook")
async def livekit_webhook(
    request: Request,
    authorization: str = Header(...),
):
    """
    Receive LiveKit webhook events.

    On participant_joined for SIP participants in inbound rooms:
    creates a CallSession record so session-complete can find it later.
    """
    body = (await request.body()).decode("utf-8")

    try:
        event = get_webhook_receiver().receive(body, authorization)
    except Exception as e:
        logger.warning(f"Webhook verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = event.event
    logger.info(f"LiveKit webhook: {event_type}, room={event.room.name}")

    if event_type == "participant_joined":
        await _handle_participant_joined(event)

    return {"ok": True}


async def _handle_participant_joined(event):
    """
    When a SIP participant joins an inbound room, create a CallSession.

    The SIP participant's identity is the caller's phone number (E.164).
    The room name starts with "inbound-" for inbound calls.
    """
    room_name = event.room.name
    participant = event.participant

    # Only process inbound rooms
    if not room_name.startswith("inbound-"):
        return

    # Only process SIP participants (not the agent)
    # ParticipantInfo.Kind: STANDARD=0, INGRESS=1, EGRESS=2, SIP=3, AGENT=4
    if participant.kind != 3:  # SIP participant
        return

    # Extract caller phone: prefer SIP attributes, then parse from room name,
    # fall back to participant identity
    caller_phone = (
        participant.attributes.get("sip.phoneNumber")
        or participant.attributes.get("sip.callFrom")
    )
    if not caller_phone:
        # Room name format: inbound-_<E.164>_<random>
        parts = room_name.split("_")
        if len(parts) >= 2 and parts[1].startswith("+"):
            caller_phone = parts[1]
        else:
            caller_phone = participant.identity
    logger.info(f"Inbound SIP call detected: room={room_name}, caller={caller_phone}")

    async with async_session_factory() as session:
        try:
            call_repo = CallRepository(session)
            investor_repo = InvestorRepository(session)

            # Idempotency check
            existing = await call_repo.get_by_room_name(room_name)
            if existing:
                logger.info(f"CallSession already exists for {room_name}")
                return

            # Look up investor by phone number, create new lead if not found
            investor = await investor_repo.get_by_phone(caller_phone)
            is_new_investor = investor is None
            if not investor:
                investor = await investor_repo.create_from_inbound(caller_phone)
                logger.info(f"Created new lead from inbound call: {investor.id} ({caller_phone})")
            investor_id = investor.id

            # Create CallSession for the inbound call
            call = await call_repo.create_inbound_call(
                room_name=room_name,
                caller_phone=caller_phone,
                investor_id=investor_id,
            )

            # Only update stage for new investors — don't regress returning investors
            if is_new_investor:
                await investor_repo.update_stage(
                    investor_id=investor_id,
                    new_stage="call_dispatched",
                    changed_by="inbound_call",
                    notes=f"Inbound call from {caller_phone}",
                )

            await session.commit()
            logger.info(
                f"Inbound CallSession created: {call.id}, "
                f"investor={investor_id}, caller={caller_phone}"
            )
        except Exception:
            await session.rollback()
            logger.exception(f"Error handling inbound call for {room_name}")
