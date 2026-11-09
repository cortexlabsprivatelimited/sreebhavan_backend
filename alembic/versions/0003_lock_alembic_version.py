"""Turn on row-level security for alembic_version.

Alembic creates its own table in `public`, which Supabase's Data API exposes to the anon and authenticated
roles. With RLS on and no policies, and grants revoked, only the table owner (this API) can read or write it.

Revision ID: 0003_lock_alembic_version
Revises: 0002_seed_businesses
Create Date: 2026-11-09
"""

from alembic import op

revision = "0003_lock_alembic_version"
down_revision = "0002_seed_businesses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL ON TABLE public.alembic_version FROM anon;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL ON TABLE public.alembic_version FROM authenticated;
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY")
