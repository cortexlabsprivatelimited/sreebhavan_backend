"""Request/response bodies for the admin endpoints (API spec section 6).

`<Name>In` is the create body and also the full PATCH body. Partial PATCH bodies are merged with the stored
record and validated against the same `<Name>In`, so required fields can never be cleared.
"""

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import EmailStr, Field, StringConstraints, field_validator, model_validator

from app.schemas.common import (
    AlbumCategory,
    BookingStatus,
    EnquiryStatus,
    EnquiryType,
    InSchema,
    Money,
    OptPhone,
    OptStr,
    OutSchema,
    PageKey,
    ReqStr,
    Role,
    Slot,
    Slug,
    WhatsApp,
)

StrList = list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]]


# ---- Auth ----------------------------------------------------------------------------
class LoginIn(InSchema):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=1)]


class AdminBrief(OutSchema):
    id: uuid.UUID
    name: str
    email: str
    role: Role


class LoginOut(OutSchema):
    access_token: str
    token_type: str = "bearer"
    admin: AdminBrief


class ForgotPasswordIn(InSchema):
    email: EmailStr


# ---- Dashboard -----------------------------------------------------------------------
class DashboardBooking(OutSchema):
    id: uuid.UUID
    date: date
    slot: Slot
    status: BookingStatus
    customer_name: str | None
    event_type: str | None


class DashboardEnquiry(OutSchema):
    id: uuid.UUID
    type: EnquiryType
    name: str
    phone: str
    status: EnquiryStatus
    created_at: datetime


class MonthBooking(OutSchema):
    date: date
    slot: Slot
    status: BookingStatus


class DashboardStats(OutSchema):
    new_enquiries: int
    open_enquiries: int
    enquiries_this_month: int
    hall_bookings_this_month: int
    upcoming_bookings: list[DashboardBooking]
    recent_enquiries: list[DashboardEnquiry]
    month_bookings: list[MonthBooking]


# ---- Site settings -------------------------------------------------------------------
class SiteSettingsBody(InSchema):
    brand_logo_url: OptStr = None
    favicon_url: OptStr = None
    contact_phone: OptStr = None
    contact_email: OptStr = None
    address: OptStr = None
    map_embed_url: OptStr = None
    map_link_url: OptStr = None
    facebook_url: OptStr = None
    instagram_url: OptStr = None
    youtube_url: OptStr = None
    footer_text: OptStr = None
    google_analytics_id: OptStr = None
    search_console_verification: OptStr = None


SETTINGS_KEYS = tuple(SiteSettingsBody.model_fields)


# ---- Businesses ----------------------------------------------------------------------
class Timing(InSchema):
    label: ReqStr
    hours: ReqStr


class BusinessIn(InSchema):
    name: ReqStr
    logo_url: OptStr = None
    about: OptStr = None
    whatsapp: WhatsApp
    phone: OptStr = None
    timings: list[Timing] = Field(default_factory=list)


class BusinessOut(OutSchema):
    id: uuid.UUID
    slug: str
    name: str
    logo_url: str | None
    about: str | None
    whatsapp: str
    phone: str | None
    timings: list[Timing]


# ---- Banners -------------------------------------------------------------------------
class BannerIn(InSchema):
    business_id: uuid.UUID | None = None
    image_url: ReqStr
    title: Annotated[ReqStr, StringConstraints(max_length=200)]
    subtitle: OptStr = None
    cta_text: OptStr = None
    cta_link: OptStr = None
    sort: int = 0
    active: bool = True


class BannerOut(BannerIn, OutSchema):
    id: uuid.UUID


# ---- Menu ----------------------------------------------------------------------------
class MenuCategoryIn(InSchema):
    name: ReqStr
    name_ml: OptStr = None
    slug: Slug
    image_url: OptStr = None
    sort: int = 0
    active: bool = True


class MenuCategoryOut(MenuCategoryIn, OutSchema):
    id: uuid.UUID


class MenuItemIn(InSchema):
    category_id: uuid.UUID
    name: ReqStr
    name_ml: OptStr = None
    slug: Slug
    price: Money
    image_url: OptStr = None
    description: OptStr = None
    is_special: bool = False
    is_available: bool = True
    sort: int = 0


class MenuItemOut(MenuItemIn, OutSchema):
    id: uuid.UUID


class MenuCardIn(InSchema):
    title: ReqStr
    file_url: ReqStr
    active: bool = True


class MenuCardOut(MenuCardIn, OutSchema):
    id: uuid.UUID


# ---- Rooms ---------------------------------------------------------------------------
class ImageIn(InSchema):
    url: ReqStr
    alt: Annotated[ReqStr, StringConstraints(max_length=300)]
    sort: int = 0


class ImageOut(OutSchema):
    id: uuid.UUID
    url: str
    alt: str
    sort: int


class RoomIn(InSchema):
    slug: Slug
    name: ReqStr
    price: Money
    capacity: Annotated[int, Field(ge=1)]
    amenities: StrList = Field(default_factory=list)
    description: OptStr = None
    active: bool = True


class RoomOut(RoomIn, OutSchema):
    id: uuid.UUID
    images: list[ImageOut] = Field(default_factory=list)


# ---- Hall ----------------------------------------------------------------------------
class HallIn(InSchema):
    name: ReqStr
    capacity_seating: Annotated[int, Field(ge=0)] | None = None
    capacity_floating: Annotated[int, Field(ge=0)] | None = None
    facilities: StrList = Field(default_factory=list)
    rules: OptStr = None


class HallOut(HallIn, OutSchema):
    pass


class HallPackageIn(InSchema):
    name: ReqStr
    price: Money
    inclusions: StrList = Field(default_factory=list)
    sort: int = 0


class HallPackageOut(HallPackageIn, OutSchema):
    id: uuid.UUID


class HallBookingIn(InSchema):
    date: date
    slot: Slot
    status: BookingStatus
    customer_name: OptStr = None
    phone: OptPhone = None
    event_type: OptStr = None
    notes: OptStr = None


class HallBookingOut(HallBookingIn, OutSchema):
    id: uuid.UUID


# ---- Enquiries -----------------------------------------------------------------------
class EnquiryOut(OutSchema):
    id: uuid.UUID
    type: EnquiryType
    name: str
    phone: str
    email: str | None
    date_from: date | None
    date_to: date | None
    slot: Slot | None
    guests: int | None
    event_type: str | None
    room_id: uuid.UUID | None
    room_name: str | None
    message: str | None
    status: EnquiryStatus
    admin_notes: str | None
    created_at: datetime


class EnquiryPatch(InSchema):
    status: EnquiryStatus | None = None
    admin_notes: OptStr = None


# ---- Gallery -------------------------------------------------------------------------
class GalleryAlbumIn(InSchema):
    slug: Slug
    title: ReqStr
    category: AlbumCategory
    cover_url: OptStr = None
    sort: int = 0
    active: bool = True


class GalleryAlbumOut(GalleryAlbumIn, OutSchema):
    id: uuid.UUID
    image_count: int = 0


class GalleryImageItem(InSchema):
    url: ReqStr
    thumb_url: OptStr = None
    alt: Annotated[ReqStr, StringConstraints(max_length=300)]
    caption: OptStr = None
    sort: int = 0


class GalleryImagesBulkIn(InSchema):
    album_id: uuid.UUID
    images: Annotated[list[GalleryImageItem], Field(min_length=1, max_length=200)]


class GalleryImagePatch(InSchema):
    alt: Annotated[ReqStr, StringConstraints(max_length=300)]
    caption: OptStr = None
    sort: int = 0


class GalleryImageOut(OutSchema):
    id: uuid.UUID
    album_id: uuid.UUID
    url: str
    thumb_url: str | None
    alt: str
    caption: str | None
    sort: int


# ---- Testimonials / FAQs -------------------------------------------------------------
class TestimonialIn(InSchema):
    name: ReqStr
    text: ReqStr
    rating: Annotated[int, Field(ge=1, le=5)]
    business_id: uuid.UUID | None = None
    sort: int = 0
    active: bool = True


class TestimonialOut(TestimonialIn, OutSchema):
    id: uuid.UUID


class FaqIn(InSchema):
    business_id: uuid.UUID | None = None
    question: ReqStr
    answer: ReqStr
    sort: int = 0


class FaqOut(FaqIn, OutSchema):
    id: uuid.UUID


# ---- SEO -----------------------------------------------------------------------------
class SeoIn(InSchema):
    page_key: PageKey
    title: Annotated[str, StringConstraints(max_length=60)] | None = None
    description: Annotated[str, StringConstraints(max_length=160)] | None = None
    og_image: OptStr = None
    keywords: OptStr = None
    noindex: bool = False

    @field_validator("title", "description", mode="before")
    @classmethod
    def _blank(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class SeoOut(SeoIn, OutSchema):
    id: uuid.UUID


# ---- Uploads -------------------------------------------------------------------------
class UploadOut(OutSchema):
    url: str
    thumb_url: str | None


# ---- Admin users ---------------------------------------------------------------------
class AdminUserIn(InSchema):
    name: ReqStr
    email: EmailStr
    role: Role = "staff"
    active: bool = True

    @model_validator(mode="after")
    def _lower_email(self):
        self.email = self.email.lower()
        return self


class AdminUserOut(OutSchema):
    id: uuid.UUID
    name: str
    email: str
    role: Role
    active: bool
    last_sign_in_at: datetime | None
