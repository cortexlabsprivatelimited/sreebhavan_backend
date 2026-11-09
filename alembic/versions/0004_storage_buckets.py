"""Create the public Supabase Storage buckets used by POST /admin/uploads.

Buckets are public for reading (the websites load images straight from the CDN). Only the API writes, with
the secret key, which bypasses storage policies, so no policies are added. Skipped on plain PostgreSQL
(no `storage` schema), e.g. in CI.

Revision ID: 0004_storage_buckets
Revises: 0003_lock_alembic_version
Create Date: 2026-11-09
"""

from alembic import op

revision = "0004_storage_buckets"
down_revision = "0003_lock_alembic_version"
branch_labels = None
depends_on = None

FIVE_MB = 5 * 1024 * 1024
WEBP = "'image/webp'"
BUCKETS = {
    # bucket: allowed MIME types (the API converts every photo to WebP)
    "logos": f"{WEBP}, 'image/svg+xml', 'image/x-icon', 'image/vnd.microsoft.icon'",
    "banners": WEBP,
    "menu": f"{WEBP}, 'application/pdf'",  # menu/items photos and menu/cards PDFs
    "rooms": WEBP,
    "hall": WEBP,
    "gallery": WEBP,
    "testimonials": WEBP,
    "seo": WEBP,
}


def upgrade() -> None:
    values = ",\n                ".join(
        f"('{b}', '{b}', true, {FIVE_MB}, ARRAY[{types}]::text[])" for b, types in BUCKETS.items()
    )
    op.execute(
        f"""
        DO $$
        BEGIN
            IF to_regclass('storage.buckets') IS NOT NULL THEN
                INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
                VALUES
                {values}
                ON CONFLICT (id) DO NOTHING;
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    # Buckets may hold uploaded files; remove them from the Supabase dashboard if really needed.
    pass
