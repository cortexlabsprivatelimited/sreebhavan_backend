-- =====================================================================================================
-- Sreebhavan API: full database setup for Supabase (run once, on an empty project)
--
-- Supabase dashboard > SQL Editor > New query > paste this whole file > Run.
--
-- Creates the 21 tables (row-level security ON, no direct access for anon/authenticated), seeds the two
-- businesses, creates the 8 public storage buckets, and records the migration version in alembic_version
-- so later `uv run alembic upgrade head` runs continue from here. Runs in one transaction: all or nothing.
--
-- GENERATED from the Alembic migrations. Do not edit by hand. Regenerate with:
--     uv run python scripts/export_supabase_sql.py
-- =====================================================================================================

BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_initial

CREATE TABLE admin_users (
    id UUID NOT NULL, 
    name VARCHAR(120) NOT NULL, 
    email VARCHAR(320) NOT NULL, 
    role VARCHAR(16) NOT NULL, 
    active BOOLEAN NOT NULL, 
    last_sign_in_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_admin_users PRIMARY KEY (id), 
    CONSTRAINT ck_admin_users_role CHECK (role IN ('owner', 'staff')), 
    CONSTRAINT uq_admin_users_email UNIQUE (email)
);

CREATE TABLE businesses (
    slug VARCHAR(120) NOT NULL, 
    name VARCHAR(160) NOT NULL, 
    logo_url TEXT, 
    about TEXT, 
    whatsapp VARCHAR(16) NOT NULL, 
    phone VARCHAR(32), 
    timings JSONB NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_businesses PRIMARY KEY (id), 
    CONSTRAINT uq_businesses_slug UNIQUE (slug)
);

CREATE TABLE gallery_albums (
    slug VARCHAR(160) NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    category VARCHAR(32) NOT NULL, 
    cover_url TEXT, 
    sort INTEGER NOT NULL, 
    active BOOLEAN NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_gallery_albums PRIMARY KEY (id), 
    CONSTRAINT ck_gallery_albums_category CHECK (category IN ('rooms', 'hall', 'past-events', 'food', 'exterior')), 
    CONSTRAINT uq_gallery_albums_slug UNIQUE (slug)
);

CREATE TABLE hall (
    name VARCHAR(160) NOT NULL, 
    capacity_seating INTEGER, 
    capacity_floating INTEGER, 
    facilities JSONB NOT NULL, 
    rules TEXT, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_hall PRIMARY KEY (id)
);

CREATE TABLE hall_images (
    url TEXT NOT NULL, 
    alt VARCHAR(300) NOT NULL, 
    sort INTEGER NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_hall_images PRIMARY KEY (id)
);

CREATE TABLE hall_packages (
    name VARCHAR(160) NOT NULL, 
    price INTEGER NOT NULL, 
    inclusions JSONB NOT NULL, 
    sort INTEGER NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_hall_packages PRIMARY KEY (id)
);

CREATE TABLE menu_cards (
    title VARCHAR(160) NOT NULL, 
    file_url TEXT NOT NULL, 
    active BOOLEAN NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_menu_cards PRIMARY KEY (id)
);

CREATE TABLE menu_categories (
    name VARCHAR(120) NOT NULL, 
    name_ml VARCHAR(160), 
    slug VARCHAR(120) NOT NULL, 
    image_url TEXT, 
    sort INTEGER NOT NULL, 
    active BOOLEAN NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_menu_categories PRIMARY KEY (id), 
    CONSTRAINT uq_menu_categories_slug UNIQUE (slug)
);

CREATE TABLE rooms (
    slug VARCHAR(120) NOT NULL, 
    name VARCHAR(160) NOT NULL, 
    price INTEGER NOT NULL, 
    capacity INTEGER NOT NULL, 
    amenities JSONB NOT NULL, 
    description TEXT, 
    active BOOLEAN NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_rooms PRIMARY KEY (id), 
    CONSTRAINT uq_rooms_slug UNIQUE (slug)
);

CREATE TABLE seo_meta (
    page_key VARCHAR(200) NOT NULL, 
    title VARCHAR(60), 
    description VARCHAR(160), 
    og_image TEXT, 
    keywords TEXT, 
    noindex BOOLEAN NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_seo_meta PRIMARY KEY (id), 
    CONSTRAINT uq_seo_meta_page_key UNIQUE (page_key)
);

CREATE TABLE site_settings (
    key VARCHAR(64) NOT NULL, 
    value JSONB, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_site_settings PRIMARY KEY (key)
);

CREATE TABLE activity_logs (
    user_id UUID, 
    action VARCHAR(32) NOT NULL, 
    entity VARCHAR(64) NOT NULL, 
    entity_id VARCHAR(64), 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_activity_logs PRIMARY KEY (id), 
    CONSTRAINT fk_activity_logs_user_id_admin_users FOREIGN KEY(user_id) REFERENCES admin_users (id) ON DELETE SET NULL
);

CREATE INDEX ix_activity_logs_entity ON activity_logs (entity, entity_id);

CREATE TABLE banners (
    business_id UUID, 
    image_url TEXT NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    subtitle TEXT, 
    cta_text VARCHAR(80), 
    cta_link TEXT, 
    sort INTEGER NOT NULL, 
    active BOOLEAN NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_banners PRIMARY KEY (id), 
    CONSTRAINT fk_banners_business_id_businesses FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE SET NULL
);

CREATE TABLE enquiries (
    type VARCHAR(16) NOT NULL, 
    name VARCHAR(160) NOT NULL, 
    phone VARCHAR(32) NOT NULL, 
    email VARCHAR(320), 
    date_from DATE, 
    date_to DATE, 
    slot VARCHAR(16), 
    guests INTEGER, 
    event_type VARCHAR(80), 
    room_id UUID, 
    message TEXT, 
    status VARCHAR(16) NOT NULL, 
    admin_notes TEXT, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_enquiries PRIMARY KEY (id), 
    CONSTRAINT ck_enquiries_slot CHECK (slot IS NULL OR slot IN ('morning', 'evening', 'full')), 
    CONSTRAINT ck_enquiries_status CHECK (status IN ('new', 'contacted', 'confirmed', 'cancelled')), 
    CONSTRAINT ck_enquiries_type CHECK (type IN ('room', 'hall', 'hotel')), 
    CONSTRAINT fk_enquiries_room_id_rooms FOREIGN KEY(room_id) REFERENCES rooms (id) ON DELETE SET NULL
);

CREATE INDEX ix_enquiries_created_at ON enquiries (created_at);

CREATE INDEX ix_enquiries_status ON enquiries (status);

CREATE TABLE faqs (
    business_id UUID, 
    question TEXT NOT NULL, 
    answer TEXT NOT NULL, 
    sort INTEGER NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_faqs PRIMARY KEY (id), 
    CONSTRAINT fk_faqs_business_id_businesses FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE SET NULL
);

CREATE TABLE gallery_images (
    album_id UUID NOT NULL, 
    url TEXT NOT NULL, 
    thumb_url TEXT, 
    alt VARCHAR(300) NOT NULL, 
    caption TEXT, 
    sort INTEGER NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_gallery_images PRIMARY KEY (id), 
    CONSTRAINT fk_gallery_images_album_id_gallery_albums FOREIGN KEY(album_id) REFERENCES gallery_albums (id) ON DELETE CASCADE
);

CREATE INDEX ix_gallery_images_album_id ON gallery_images (album_id);

CREATE TABLE hall_bookings (
    date DATE NOT NULL, 
    slot VARCHAR(16) NOT NULL, 
    status VARCHAR(16) NOT NULL, 
    customer_name VARCHAR(160), 
    phone VARCHAR(32), 
    event_type VARCHAR(80), 
    notes TEXT, 
    created_by UUID, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_hall_bookings PRIMARY KEY (id), 
    CONSTRAINT ck_hall_bookings_slot CHECK (slot IN ('morning', 'evening', 'full')), 
    CONSTRAINT ck_hall_bookings_status CHECK (status IN ('booked', 'tentative')), 
    CONSTRAINT fk_hall_bookings_created_by_admin_users FOREIGN KEY(created_by) REFERENCES admin_users (id) ON DELETE SET NULL, 
    CONSTRAINT uq_hall_bookings_date_slot UNIQUE (date, slot)
);

CREATE INDEX ix_hall_bookings_date ON hall_bookings (date);

CREATE TABLE menu_items (
    category_id UUID NOT NULL, 
    name VARCHAR(160) NOT NULL, 
    name_ml VARCHAR(200), 
    slug VARCHAR(160) NOT NULL, 
    price INTEGER NOT NULL, 
    image_url TEXT, 
    description TEXT, 
    is_special BOOLEAN NOT NULL, 
    is_available BOOLEAN NOT NULL, 
    sort INTEGER NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_menu_items PRIMARY KEY (id), 
    CONSTRAINT fk_menu_items_category_id_menu_categories FOREIGN KEY(category_id) REFERENCES menu_categories (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_menu_items_slug UNIQUE (slug)
);

CREATE INDEX ix_menu_items_category_id ON menu_items (category_id);

CREATE TABLE room_blocks (
    room_id UUID NOT NULL, 
    date_from DATE NOT NULL, 
    date_to DATE NOT NULL, 
    reason TEXT, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_room_blocks PRIMARY KEY (id), 
    CONSTRAINT ck_room_blocks_date_range CHECK (date_to >= date_from), 
    CONSTRAINT fk_room_blocks_room_id_rooms FOREIGN KEY(room_id) REFERENCES rooms (id) ON DELETE CASCADE
);

CREATE INDEX ix_room_blocks_room_id ON room_blocks (room_id);

CREATE TABLE room_images (
    room_id UUID NOT NULL, 
    url TEXT NOT NULL, 
    alt VARCHAR(300) NOT NULL, 
    sort INTEGER NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_room_images PRIMARY KEY (id), 
    CONSTRAINT fk_room_images_room_id_rooms FOREIGN KEY(room_id) REFERENCES rooms (id) ON DELETE CASCADE
);

CREATE INDEX ix_room_images_room_id ON room_images (room_id);

CREATE TABLE testimonials (
    name VARCHAR(160) NOT NULL, 
    text TEXT NOT NULL, 
    rating INTEGER NOT NULL, 
    business_id UUID, 
    sort INTEGER NOT NULL, 
    active BOOLEAN NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_testimonials PRIMARY KEY (id), 
    CONSTRAINT ck_testimonials_rating CHECK (rating BETWEEN 1 AND 5), 
    CONSTRAINT fk_testimonials_business_id_businesses FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE SET NULL
);

ALTER TABLE public."admin_users" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."admin_users" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."admin_users" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."businesses" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."businesses" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."businesses" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."gallery_albums" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."gallery_albums" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."gallery_albums" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."hall" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."hall" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."hall" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."hall_images" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."hall_images" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."hall_images" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."hall_packages" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."hall_packages" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."hall_packages" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."menu_cards" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."menu_cards" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."menu_cards" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."menu_categories" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."menu_categories" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."menu_categories" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."rooms" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."rooms" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."rooms" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."seo_meta" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."seo_meta" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."seo_meta" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."site_settings" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."site_settings" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."site_settings" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."activity_logs" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."activity_logs" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."activity_logs" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."banners" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."banners" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."banners" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."enquiries" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."enquiries" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."enquiries" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."faqs" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."faqs" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."faqs" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."gallery_images" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."gallery_images" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."gallery_images" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."hall_bookings" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."hall_bookings" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."hall_bookings" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."menu_items" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."menu_items" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."menu_items" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."room_blocks" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."room_blocks" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."room_blocks" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."room_images" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."room_images" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."room_images" FROM authenticated;
                END IF;
            END $$;

ALTER TABLE public."testimonials" ENABLE ROW LEVEL SECURITY;

DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public."testimonials" FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public."testimonials" FROM authenticated;
                END IF;
            END $$;

INSERT INTO alembic_version (version_num) VALUES ('0001_initial') RETURNING alembic_version.version_num;

-- Running upgrade 0001_initial -> 0002_seed_businesses

INSERT INTO businesses (slug, name, about, whatsapp, timings) VALUES ('sreebhavan-veg-hotel', 'Sreebhavan Veg Hotel', 'Pure vegetarian Kerala meals.', '9000000000', CAST('[{"label": "Mon – Sun", "hours": "6:00 am – 10:00 pm"}]' AS jsonb)) ON CONFLICT (slug) DO NOTHING;

INSERT INTO businesses (slug, name, about, whatsapp, timings) VALUES ('sreebhavanam', 'Sreebhavanam', 'Event hall and rooms.', '9000000000', CAST('[{"label": "Front desk", "hours": "Open 24 hours"}]' AS jsonb)) ON CONFLICT (slug) DO NOTHING;

UPDATE alembic_version SET version_num='0002_seed_businesses' WHERE alembic_version.version_num = '0001_initial';

-- Running upgrade 0002_seed_businesses -> 0003_lock_alembic_version

ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;

DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL ON TABLE public.alembic_version FROM anon;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL ON TABLE public.alembic_version FROM authenticated;
            END IF;
        END $$;

UPDATE alembic_version SET version_num='0003_lock_alembic_version' WHERE alembic_version.version_num = '0002_seed_businesses';

-- Running upgrade 0003_lock_alembic_version -> 0004_storage_buckets

DO $$
        BEGIN
            IF to_regclass('storage.buckets') IS NOT NULL THEN
                INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
                VALUES
                ('logos', 'logos', true, 5242880, ARRAY['image/webp', 'image/svg+xml', 'image/x-icon', 'image/vnd.microsoft.icon']::text[]),
                ('banners', 'banners', true, 5242880, ARRAY['image/webp']::text[]),
                ('menu', 'menu', true, 5242880, ARRAY['image/webp', 'application/pdf']::text[]),
                ('rooms', 'rooms', true, 5242880, ARRAY['image/webp']::text[]),
                ('hall', 'hall', true, 5242880, ARRAY['image/webp']::text[]),
                ('gallery', 'gallery', true, 5242880, ARRAY['image/webp']::text[]),
                ('testimonials', 'testimonials', true, 5242880, ARRAY['image/webp']::text[]),
                ('seo', 'seo', true, 5242880, ARRAY['image/webp']::text[])
                ON CONFLICT (id) DO NOTHING;
            END IF;
        END $$;

UPDATE alembic_version SET version_num='0004_storage_buckets' WHERE alembic_version.version_num = '0003_lock_alembic_version';

COMMIT;

