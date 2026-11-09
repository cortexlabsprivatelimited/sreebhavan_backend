import re
import uuid
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PAGE_KEY_RE = re.compile(r"^[a-z0-9-]+(/[a-z0-9-]+)?$")
INDIAN_MOBILE_RE = re.compile(r"^(?:91)?[6-9]\d{9}$")
MONTH_RE = r"^\d{4}-(0[1-9]|1[0-2])$"

Role = Literal["owner", "staff"]
Slot = Literal["morning", "evening", "full"]
BookingStatus = Literal["booked", "tentative"]
EnquiryStatus = Literal["new", "contacted", "confirmed", "cancelled"]
EnquiryType = Literal["room", "hall", "hotel"]
AlbumCategory = Literal["rooms", "hall", "past-events", "food", "exterior"]
UploadFolder = Literal[
    "logos", "banners", "menu/items", "menu/cards", "rooms", "hall", "gallery", "testimonials", "seo"
]


def _blank_to_none(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def _strip(v):
    return v.strip() if isinstance(v, str) else v


def _check_slug(v: str) -> str:
    if not SLUG_RE.match(v):
        raise ValueError("Use lowercase letters, numbers and single hyphens only (e.g. deluxe-ac-room).")
    return v


def _check_page_key(v: str) -> str:
    if not PAGE_KEY_RE.match(v):
        raise ValueError("Use a page name like 'rooms' or an item key like 'room/deluxe-ac-room'.")
    return v


def _normalise_phone(v):
    if isinstance(v, str):
        return re.sub(r"[\s\-()+]", "", v)
    return v


def _check_whatsapp(v: str) -> str:
    if not INDIAN_MOBILE_RE.match(v):
        raise ValueError("Enter a 10-digit Indian mobile number, optionally starting with 91.")
    return v


# Optional text: "" and whitespace become null.
OptStr = Annotated[str | None, BeforeValidator(_blank_to_none)]
# Required, non-empty text.
ReqStr = Annotated[str, BeforeValidator(_strip), StringConstraints(min_length=1)]
Slug = Annotated[str, BeforeValidator(_strip), StringConstraints(max_length=160), AfterValidator(_check_slug)]
PageKey = Annotated[
    str, BeforeValidator(_strip), StringConstraints(max_length=200), AfterValidator(_check_page_key)
]
WhatsApp = Annotated[str, BeforeValidator(_normalise_phone), AfterValidator(_check_whatsapp)]
_PhoneDigits = Annotated[str, StringConstraints(min_length=6, max_length=15, pattern=r"^\d+$")]
Phone = Annotated[_PhoneDigits, BeforeValidator(_normalise_phone)]
# Validators run last-to-first: normalise, then blank -> null.
OptPhone = Annotated[_PhoneDigits | None, BeforeValidator(_blank_to_none), BeforeValidator(_normalise_phone)]
Money = Annotated[int, Field(ge=0)]
Sort = Annotated[int, Field(default=0)]
Month = Annotated[str, StringConstraints(pattern=MONTH_RE)]


class InSchema(BaseModel):
    """Request bodies: ignore unknown keys (e.g. an `id` echoed back by the panel)."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=False)


class OutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IdOut(OutSchema):
    id: uuid.UUID
