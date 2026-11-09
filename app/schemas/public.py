"""Response bodies for the public (user website) endpoints. Read-only data that is safe to cache."""

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import EmailStr, Field, StringConstraints, field_validator, model_validator

from app.schemas.admin import Timing
from app.schemas.common import (
    AlbumCategory,
    BookingStatus,
    EnquiryType,
    InSchema,
    OutSchema,
    Phone,
    ReqStr,
    Slot,
)


class PublicBusiness(OutSchema):
    id: uuid.UUID
    slug: str
    name: str
    logo_url: str | None
    about: str | None
    whatsapp: str
    phone: str | None
    timings: list[Timing]


class PublicBanner(OutSchema):
    id: uuid.UUID
    business_id: uuid.UUID | None
    image_url: str
    title: str
    subtitle: str | None
    cta_text: str | None
    cta_link: str | None
    sort: int


class PublicMenuCategory(OutSchema):
    id: uuid.UUID
    name: str
    name_ml: str | None
    slug: str
    image_url: str | None
    sort: int


class PublicMenuItem(OutSchema):
    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    name_ml: str | None
    slug: str
    price: int
    image_url: str | None
    description: str | None
    is_special: bool
    sort: int


class PublicMenuCard(OutSchema):
    id: uuid.UUID
    title: str
    file_url: str


class PublicImage(OutSchema):
    id: uuid.UUID
    url: str
    alt: str
    sort: int


class PublicRoom(OutSchema):
    id: uuid.UUID
    slug: str
    name: str
    price: int
    capacity: int
    amenities: list[str]
    description: str | None
    images: list[PublicImage]


class PublicHall(OutSchema):
    name: str
    capacity_seating: int | None
    capacity_floating: int | None
    facilities: list[str]
    rules: str | None
    images: list[PublicImage] = Field(default_factory=list)


class PublicHallPackage(OutSchema):
    id: uuid.UUID
    name: str
    price: int
    inclusions: list[str]
    sort: int


class Availability(OutSchema):
    """Never includes customer name, phone or notes."""

    date: date
    slot: Slot
    status: BookingStatus


class PublicAlbum(OutSchema):
    id: uuid.UUID
    slug: str
    title: str
    category: AlbumCategory
    cover_url: str | None
    sort: int
    image_count: int = 0


class PublicGalleryImage(OutSchema):
    id: uuid.UUID
    url: str
    thumb_url: str | None
    alt: str
    caption: str | None
    sort: int


class PublicAlbumDetail(PublicAlbum):
    images: list[PublicGalleryImage] = Field(default_factory=list)


class PublicTestimonial(OutSchema):
    id: uuid.UUID
    name: str
    text: str
    rating: int
    business_id: uuid.UUID | None
    sort: int


class PublicFaq(OutSchema):
    id: uuid.UUID
    business_id: uuid.UUID | None
    question: str
    answer: str
    sort: int


class PublicSeo(OutSchema):
    page_key: str
    title: str | None
    description: str | None
    og_image: str | None
    keywords: str | None
    noindex: bool


class SitemapEntry(OutSchema):
    slug: str
    updated_at: datetime


class SitemapData(OutSchema):
    rooms: list[SitemapEntry]
    menu_categories: list[SitemapEntry]
    albums: list[SitemapEntry]


# ---- Enquiry form --------------------------------------------------------------------
class EnquiryIn(InSchema):
    type: EnquiryType
    name: Annotated[ReqStr, StringConstraints(max_length=120)]
    phone: Phone
    email: EmailStr | None = None
    date_from: date | None = None
    date_to: date | None = None
    slot: Slot | None = None
    guests: Annotated[int, Field(ge=1, le=5000)] | None = None
    event_type: Annotated[str, StringConstraints(max_length=80)] | None = None
    room_id: uuid.UUID | None = None
    room_slug: str | None = Field(None, description="Alternative to room_id")
    message: Annotated[str, StringConstraints(max_length=1000)] | None = None
    # Anti-spam
    website: str | None = Field(None, description="Honeypot. Leave empty; bots fill it in.")
    turnstile_token: str | None = Field(None, description="Cloudflare Turnstile token, when enabled")

    @field_validator("email", "event_type", "message", "room_slug", mode="before")
    @classmethod
    def _blank(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

    @model_validator(mode="after")
    def _normalise(self):
        # Cross-field rules are checked in services.enquiry so each error can name its field.
        if self.type != "hall":
            self.slot = None
        if self.type != "room":
            self.room_id = None
            self.room_slug = None
        return self


class EnquiryCreated(OutSchema):
    id: uuid.UUID
    whatsapp_url: str
