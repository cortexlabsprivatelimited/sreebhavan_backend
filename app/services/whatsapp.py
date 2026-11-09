"""Builds the pre-filled wa.me link for a saved enquiry."""

import re
from datetime import date
from urllib.parse import quote

from app.services.booking import SLOT_LABELS


def wa_number(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        digits = "91" + digits
    return digits


def _d(day: date | None) -> str | None:
    return day.strftime("%d-%b-%Y") if day else None


def build_message(
    *,
    business_name: str,
    type: str,
    name: str,
    phone: str,
    date_from: date | None = None,
    date_to: date | None = None,
    slot: str | None = None,
    guests: int | None = None,
    event_type: str | None = None,
    room_name: str | None = None,
    message: str | None = None,
) -> str:
    """e.g. "Hi Sreebhavanam, I'd like to enquire about the Event Hall on 12-Dec-2026 (Evening) for a Wedding,
    about 400 guests. Name: Arun, Phone: 9847012345." """
    if type == "hall":
        subject = "the Event Hall"
    elif type == "room":
        subject = f"the {room_name}" if room_name else "a room"
    else:
        subject = "your hotel"

    parts = [f"Hi {business_name}, I'd like to enquire about {subject}"]
    if date_from and date_to and date_to != date_from:
        parts.append(f" from {_d(date_from)} to {_d(date_to)}")
    elif date_from:
        parts.append(f" on {_d(date_from)}")
    if slot and type == "hall":
        parts.append(f" ({SLOT_LABELS.get(slot, slot)})")
    if event_type:
        article = "an" if event_type[:1].lower() in "aeiou" else "a"
        parts.append(f" for {article} {event_type}")
    if guests:
        noun = "guests" if type == "hall" else ("guest" if guests == 1 else "guests")
        parts.append(f", about {guests} {noun}" if type == "hall" else f", {guests} {noun}")
    text = "".join(parts) + f". Name: {name}, Phone: {phone}."
    if message:
        text += f"\n{message}"
    return text


def build_url(number: str, text: str) -> str:
    return f"https://wa.me/{wa_number(number)}?text={quote(text)}"
