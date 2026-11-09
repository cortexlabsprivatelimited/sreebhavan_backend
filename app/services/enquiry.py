"""Public enquiry form: anti-spam, validation against live data, save, then build the WhatsApp link."""

import logging
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError, conflict, unprocessable
from app.models import Business, Enquiry, HallBooking, Room
from app.schemas.public import EnquiryCreated, EnquiryIn
from app.services import whatsapp
from app.services.booking import SLOT_LABELS, blocking_slots

log = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

HOTEL_SLUG = "sreebhavan-veg-hotel"
STAYS_SLUG = "sreebhavanam"
TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str | None, ip: str) -> None:
    secret = get_settings().turnstile_secret_key
    if not secret:
        return
    if not token:
        raise AppError(400, "captcha_required", "Please complete the security check.", "turnstile_token")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(TURNSTILE_URL, data={"secret": secret, "response": token, "remoteip": ip})
        ok = r.status_code == 200 and r.json().get("success") is True
    except httpx.HTTPError:
        log.warning("Turnstile verification unavailable; allowing enquiry")
        ok = True  # don't lose real customers when Cloudflare is down; rate limit still applies
    if not ok:
        raise AppError(
            400, "captcha_failed", "The security check failed. Please try again.", "turnstile_token"
        )


def honeypot_response() -> EnquiryCreated:
    """Looks like success to the bot; nothing is saved."""
    return EnquiryCreated(id=uuid.uuid4(), whatsapp_url="https://wa.me/")


def check_rules(body: EnquiryIn) -> None:
    """Cross-field rules. Each error names the field the user has to fix."""
    if body.type == "hall":
        if not body.date_from:
            raise unprocessable("date_required", "Pick the date for the event hall.", "date_from")
        if not body.slot:
            raise unprocessable("slot_required", "Pick a slot: morning, evening or full day.", "slot")
    if body.type == "room" and not (body.room_id or body.room_slug):
        raise unprocessable("room_required", "Pick a room.", "room_id")
    if body.date_to and not body.date_from:
        raise unprocessable("date_required", "Enter the start date as well.", "date_from")
    if body.date_to and body.date_from and body.date_to < body.date_from:
        raise unprocessable("date_range", "The end date must be on or after the start date.", "date_to")
    if body.date_from and body.date_from < datetime.now(IST).date():
        raise unprocessable("date_in_past", "The date cannot be in the past.", "date_from")


async def create_enquiry(db: AsyncSession, body: EnquiryIn) -> EnquiryCreated:
    check_rules(body)

    room: Room | None = None
    if body.type == "room":
        stmt = select(Room).where(Room.active.is_(True))
        stmt = (
            stmt.where(Room.id == body.room_id) if body.room_id else stmt.where(Room.slug == body.room_slug)
        )
        room = (await db.scalars(stmt)).first()
        if room is None:
            raise unprocessable(
                "invalid_room", "This room is not available. Please pick another room.", "room_id"
            )

    if body.type == "hall":
        stmt = select(HallBooking).where(
            HallBooking.date == body.date_from,
            HallBooking.slot.in_(blocking_slots(body.slot)),
            HallBooking.status == "booked",
        )
        if (await db.scalars(stmt.limit(1))).first():
            raise conflict(
                "slot_taken",
                f"The hall is already booked on {body.date_from:%d-%b-%Y} ({SLOT_LABELS[body.slot]}). "
                "Please pick another date or slot.",
                "slot",
            )

    slug = HOTEL_SLUG if body.type == "hotel" else STAYS_SLUG
    business = (await db.scalars(select(Business).where(Business.slug == slug))).first()
    if business is None:
        raise AppError(503, "not_configured", "Enquiries are not available right now. Please call us.")

    enquiry = Enquiry(
        type=body.type,
        name=body.name,
        phone=body.phone,
        email=body.email,
        date_from=body.date_from,
        date_to=body.date_to,
        slot=body.slot,
        guests=body.guests,
        event_type=body.event_type,
        room_id=room.id if room else None,
        message=body.message,
        status="new",
    )
    db.add(enquiry)
    await db.flush()
    # Commit before handing back the link, so the enquiry is kept even if the user never sends the message.
    await db.commit()

    text = whatsapp.build_message(
        business_name=business.name,
        type=body.type,
        name=body.name,
        phone=body.phone,
        date_from=body.date_from,
        date_to=body.date_to,
        slot=body.slot,
        guests=body.guests,
        event_type=body.event_type,
        room_name=room.name if room else None,
        message=body.message,
    )
    return EnquiryCreated(id=enquiry.id, whatsapp_url=whatsapp.build_url(business.whatsapp, text))
