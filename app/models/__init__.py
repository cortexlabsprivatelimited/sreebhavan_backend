"""SQLAlchemy models for all 21 tables. Every schema change goes through an Alembic migration."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPk

ROLES = ("owner", "staff")
SLOTS = ("morning", "evening", "full")
BOOKING_STATUSES = ("booked", "tentative")
ENQUIRY_STATUSES = ("new", "contacted", "confirmed", "cancelled")
ENQUIRY_TYPES = ("room", "hall", "hotel")
ALBUM_CATEGORIES = ("rooms", "hall", "past-events", "food", "exterior")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} IN ({', '.join(repr(v) for v in values)})"


# ---- Admin ---------------------------------------------------------------------------
class AdminUser(TimestampMixin, Base):
    __tablename__ = "admin_users"
    __table_args__ = (CheckConstraint(_in("role", ROLES), name="role"),)

    # Same id as the Supabase auth.users row.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    role: Mapped[str] = mapped_column(String(16), default="staff")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sign_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActivityLog(UUIDPk, TimestampMixin, Base):
    __tablename__ = "activity_logs"
    __table_args__ = (Index("ix_activity_logs_entity", "entity", "entity_id"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(32))
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))


# ---- Settings ------------------------------------------------------------------------
class SiteSetting(TimestampMixin, Base):
    __tablename__ = "site_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONType, nullable=True)


class Business(UUIDPk, TimestampMixin, Base):
    __tablename__ = "businesses"

    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    logo_url: Mapped[str | None] = mapped_column(Text)
    about: Mapped[str | None] = mapped_column(Text)
    whatsapp: Mapped[str] = mapped_column(String(16))
    phone: Mapped[str | None] = mapped_column(String(32))
    timings: Mapped[list] = mapped_column(JSONType, default=list)


class Banner(UUIDPk, TimestampMixin, Base):
    __tablename__ = "banners"

    business_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("businesses.id", ondelete="SET NULL"))
    image_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(200))
    subtitle: Mapped[str | None] = mapped_column(Text)
    cta_text: Mapped[str | None] = mapped_column(String(80))
    cta_link: Mapped[str | None] = mapped_column(Text)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


# ---- Hotel ---------------------------------------------------------------------------
class MenuCategory(UUIDPk, TimestampMixin, Base):
    __tablename__ = "menu_categories"

    name: Mapped[str] = mapped_column(String(120))
    name_ml: Mapped[str | None] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    image_url: Mapped[str | None] = mapped_column(Text)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MenuItem(UUIDPk, TimestampMixin, Base):
    __tablename__ = "menu_items"

    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("menu_categories.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    name_ml: Mapped[str | None] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    price: Mapped[int] = mapped_column(Integer)
    image_url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    is_special: Mapped[bool] = mapped_column(Boolean, default=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class MenuCard(UUIDPk, TimestampMixin, Base):
    __tablename__ = "menu_cards"

    title: Mapped[str] = mapped_column(String(160))
    file_url: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


# ---- Rooms ---------------------------------------------------------------------------
class Room(UUIDPk, TimestampMixin, Base):
    __tablename__ = "rooms"

    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    price: Mapped[int] = mapped_column(Integer)
    capacity: Mapped[int] = mapped_column(Integer)
    amenities: Mapped[list] = mapped_column(JSONType, default=list)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    images: Mapped[list["RoomImage"]] = relationship(
        back_populates="room",
        order_by="RoomImage.sort",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class RoomImage(UUIDPk, TimestampMixin, Base):
    __tablename__ = "room_images"

    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    alt: Mapped[str] = mapped_column(String(300))
    sort: Mapped[int] = mapped_column(Integer, default=0)

    room: Mapped[Room] = relationship(back_populates="images")


class RoomBlock(UUIDPk, TimestampMixin, Base):
    __tablename__ = "room_blocks"
    __table_args__ = (CheckConstraint("date_to >= date_from", name="date_range"),)

    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text)


# ---- Hall ----------------------------------------------------------------------------
class Hall(UUIDPk, TimestampMixin, Base):
    __tablename__ = "hall"

    name: Mapped[str] = mapped_column(String(160))
    capacity_seating: Mapped[int | None] = mapped_column(Integer)
    capacity_floating: Mapped[int | None] = mapped_column(Integer)
    facilities: Mapped[list] = mapped_column(JSONType, default=list)
    rules: Mapped[str | None] = mapped_column(Text)


class HallPackage(UUIDPk, TimestampMixin, Base):
    __tablename__ = "hall_packages"

    name: Mapped[str] = mapped_column(String(160))
    price: Mapped[int] = mapped_column(Integer)
    inclusions: Mapped[list] = mapped_column(JSONType, default=list)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class HallImage(UUIDPk, TimestampMixin, Base):
    __tablename__ = "hall_images"

    url: Mapped[str] = mapped_column(Text)
    alt: Mapped[str] = mapped_column(String(300))
    sort: Mapped[int] = mapped_column(Integer, default=0)


class HallBooking(UUIDPk, TimestampMixin, Base):
    __tablename__ = "hall_bookings"
    __table_args__ = (
        UniqueConstraint("date", "slot"),
        CheckConstraint(_in("slot", SLOTS), name="slot"),
        CheckConstraint(_in("status", BOOKING_STATUSES), name="status"),
    )

    date: Mapped[date] = mapped_column(Date, index=True)
    slot: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    customer_name: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(32))
    event_type: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))


# ---- Enquiries -----------------------------------------------------------------------
class Enquiry(UUIDPk, TimestampMixin, Base):
    __tablename__ = "enquiries"
    __table_args__ = (
        CheckConstraint(_in("type", ENQUIRY_TYPES), name="type"),
        CheckConstraint(_in("status", ENQUIRY_STATUSES), name="status"),
        CheckConstraint("slot IS NULL OR " + _in("slot", SLOTS), name="slot"),
        Index("ix_enquiries_created_at", "created_at"),
        Index("ix_enquiries_status", "status"),
    )

    type: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(320))
    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)
    slot: Mapped[str | None] = mapped_column(String(16))
    guests: Mapped[int | None] = mapped_column(Integer)
    event_type: Mapped[str | None] = mapped_column(String(80))
    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="new")
    admin_notes: Mapped[str | None] = mapped_column(Text)

    room: Mapped[Room | None] = relationship(lazy="selectin")

    @property
    def room_name(self) -> str | None:
        return self.room.name if self.room else None


# ---- Gallery -------------------------------------------------------------------------
class GalleryAlbum(UUIDPk, TimestampMixin, Base):
    __tablename__ = "gallery_albums"
    __table_args__ = (CheckConstraint(_in("category", ALBUM_CATEGORIES), name="category"),)

    slug: Mapped[str] = mapped_column(String(160), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(32))
    cover_url: Mapped[str | None] = mapped_column(Text)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class GalleryImage(UUIDPk, TimestampMixin, Base):
    __tablename__ = "gallery_images"

    album_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gallery_albums.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text)
    thumb_url: Mapped[str | None] = mapped_column(Text)
    alt: Mapped[str] = mapped_column(String(300))
    caption: Mapped[str | None] = mapped_column(Text)
    sort: Mapped[int] = mapped_column(Integer, default=0)


# ---- Content -------------------------------------------------------------------------
class Testimonial(UUIDPk, TimestampMixin, Base):
    __tablename__ = "testimonials"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating"),)

    name: Mapped[str] = mapped_column(String(160))
    text: Mapped[str] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer)
    business_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("businesses.id", ondelete="SET NULL"))
    sort: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Faq(UUIDPk, TimestampMixin, Base):
    __tablename__ = "faqs"

    business_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("businesses.id", ondelete="SET NULL"))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    sort: Mapped[int] = mapped_column(Integer, default=0)


# ---- SEO -----------------------------------------------------------------------------
class SeoMeta(UUIDPk, TimestampMixin, Base):
    __tablename__ = "seo_meta"

    page_key: Mapped[str] = mapped_column(String(200), unique=True)
    title: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(String(160))
    og_image: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[str | None] = mapped_column(Text)
    noindex: Mapped[bool] = mapped_column(Boolean, default=False)


__all__ = [
    "Base",
    "AdminUser",
    "ActivityLog",
    "SiteSetting",
    "Business",
    "Banner",
    "MenuCategory",
    "MenuItem",
    "MenuCard",
    "Room",
    "RoomImage",
    "RoomBlock",
    "Hall",
    "HallPackage",
    "HallImage",
    "HallBooking",
    "Enquiry",
    "GalleryAlbum",
    "GalleryImage",
    "Testimonial",
    "Faq",
    "SeoMeta",
]
