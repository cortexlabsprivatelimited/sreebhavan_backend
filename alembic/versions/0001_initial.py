"""Initial schema: 21 tables, row-level security on.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

TABLES = [
    "admin_users",
    "businesses",
    "gallery_albums",
    "hall",
    "hall_images",
    "hall_packages",
    "menu_cards",
    "menu_categories",
    "rooms",
    "seo_meta",
    "site_settings",
    "activity_logs",
    "banners",
    "enquiries",
    "faqs",
    "gallery_images",
    "hall_bookings",
    "menu_items",
    "room_blocks",
    "room_images",
    "testimonials",
]


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_sign_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'staff')", name=op.f("ck_admin_users_role")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_users")),
        sa.UniqueConstraint("email", name=op.f("uq_admin_users_email")),
    )
    op.create_table(
        "businesses",
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("about", sa.Text(), nullable=True),
        sa.Column("whatsapp", sa.String(length=16), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("timings", postgresql.JSONB(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_businesses")),
        sa.UniqueConstraint("slug", name=op.f("uq_businesses_slug")),
    )
    op.create_table(
        "gallery_albums",
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "category IN ('rooms', 'hall', 'past-events', 'food', 'exterior')",
            name=op.f("ck_gallery_albums_category"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gallery_albums")),
        sa.UniqueConstraint("slug", name=op.f("uq_gallery_albums_slug")),
    )
    op.create_table(
        "hall",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("capacity_seating", sa.Integer(), nullable=True),
        sa.Column("capacity_floating", sa.Integer(), nullable=True),
        sa.Column("facilities", postgresql.JSONB(), nullable=False),
        sa.Column("rules", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hall")),
    )
    op.create_table(
        "hall_images",
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("alt", sa.String(length=300), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hall_images")),
    )
    op.create_table(
        "hall_packages",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("inclusions", postgresql.JSONB(), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hall_packages")),
    )
    op.create_table(
        "menu_cards",
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_menu_cards")),
    )
    op.create_table(
        "menu_categories",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_ml", sa.String(length=160), nullable=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_menu_categories")),
        sa.UniqueConstraint("slug", name=op.f("uq_menu_categories_slug")),
    )
    op.create_table(
        "rooms",
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("amenities", postgresql.JSONB(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rooms")),
        sa.UniqueConstraint("slug", name=op.f("uq_rooms_slug")),
    )
    op.create_table(
        "seo_meta",
        sa.Column("page_key", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=60), nullable=True),
        sa.Column("description", sa.String(length=160), nullable=True),
        sa.Column("og_image", sa.Text(), nullable=True),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("noindex", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seo_meta")),
        sa.UniqueConstraint("page_key", name=op.f("uq_seo_meta_page_key")),
    )
    op.create_table(
        "site_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_site_settings")),
    )
    op.create_table(
        "activity_logs",
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("entity", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["admin_users.id"],
            name=op.f("fk_activity_logs_user_id_admin_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_logs")),
    )
    op.create_index("ix_activity_logs_entity", "activity_logs", ["entity", "entity_id"], unique=False)
    op.create_table(
        "banners",
        sa.Column("business_id", sa.Uuid(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("cta_text", sa.String(length=80), nullable=True),
        sa.Column("cta_link", sa.Text(), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name=op.f("fk_banners_business_id_businesses"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_banners")),
    )
    op.create_table(
        "enquiries",
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("slot", sa.String(length=16), nullable=True),
        sa.Column("guests", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=True),
        sa.Column("room_id", sa.Uuid(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "slot IS NULL OR slot IN ('morning', 'evening', 'full')", name=op.f("ck_enquiries_slot")
        ),
        sa.CheckConstraint(
            "status IN ('new', 'contacted', 'confirmed', 'cancelled')", name=op.f("ck_enquiries_status")
        ),
        sa.CheckConstraint("type IN ('room', 'hall', 'hotel')", name=op.f("ck_enquiries_type")),
        sa.ForeignKeyConstraint(
            ["room_id"], ["rooms.id"], name=op.f("fk_enquiries_room_id_rooms"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enquiries")),
    )
    op.create_index("ix_enquiries_created_at", "enquiries", ["created_at"], unique=False)
    op.create_index("ix_enquiries_status", "enquiries", ["status"], unique=False)
    op.create_table(
        "faqs",
        sa.Column("business_id", sa.Uuid(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name=op.f("fk_faqs_business_id_businesses"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_faqs")),
    )
    op.create_table(
        "gallery_images",
        sa.Column("album_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("thumb_url", sa.Text(), nullable=True),
        sa.Column("alt", sa.String(length=300), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["album_id"],
            ["gallery_albums.id"],
            name=op.f("fk_gallery_images_album_id_gallery_albums"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gallery_images")),
    )
    op.create_index(op.f("ix_gallery_images_album_id"), "gallery_images", ["album_id"], unique=False)
    op.create_table(
        "hall_bookings",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("slot", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("customer_name", sa.String(length=160), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("slot IN ('morning', 'evening', 'full')", name=op.f("ck_hall_bookings_slot")),
        sa.CheckConstraint("status IN ('booked', 'tentative')", name=op.f("ck_hall_bookings_status")),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["admin_users.id"],
            name=op.f("fk_hall_bookings_created_by_admin_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hall_bookings")),
        sa.UniqueConstraint("date", "slot", name=op.f("uq_hall_bookings_date_slot")),
    )
    op.create_index(op.f("ix_hall_bookings_date"), "hall_bookings", ["date"], unique=False)
    op.create_table(
        "menu_items",
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("name_ml", sa.String(length=200), nullable=True),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_special", sa.Boolean(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["menu_categories.id"],
            name=op.f("fk_menu_items_category_id_menu_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_menu_items")),
        sa.UniqueConstraint("slug", name=op.f("uq_menu_items_slug")),
    )
    op.create_index(op.f("ix_menu_items_category_id"), "menu_items", ["category_id"], unique=False)
    op.create_table(
        "room_blocks",
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("date_to >= date_from", name=op.f("ck_room_blocks_date_range")),
        sa.ForeignKeyConstraint(
            ["room_id"], ["rooms.id"], name=op.f("fk_room_blocks_room_id_rooms"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_room_blocks")),
    )
    op.create_index(op.f("ix_room_blocks_room_id"), "room_blocks", ["room_id"], unique=False)
    op.create_table(
        "room_images",
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("alt", sa.String(length=300), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["room_id"], ["rooms.id"], name=op.f("fk_room_images_room_id_rooms"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_room_images")),
    )
    op.create_index(op.f("ix_room_images_room_id"), "room_images", ["room_id"], unique=False)
    op.create_table(
        "testimonials",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name=op.f("ck_testimonials_rating")),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name=op.f("fk_testimonials_business_id_businesses"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_testimonials")),
    )

    # Row-level security on every table with no policies: the anon and authenticated roles (Supabase's
    # public API) can neither read nor write. FastAPI connects as the table owner, which bypasses RLS.
    for table in TABLES:
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."{table}" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."{table}" FROM authenticated;
                END IF;
            END $$
            """
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
