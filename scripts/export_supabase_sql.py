"""Writes supabase/01_schema.sql from the Alembic migrations (for the Supabase SQL Editor).

uv run python scripts/export_supabase_sql.py
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "supabase" / "01_schema.sql"

HEADER = """\
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

"""


def main() -> None:
    sql = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        # Placeholder URL (overrides .env): offline mode only needs the dialect and never connects.
        env={**os.environ, "DATABASE_URL": "postgresql+asyncpg://offline@localhost/offline"},
    ).stdout
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(HEADER + sql)
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(sql.splitlines())} lines)")


if __name__ == "__main__":
    main()
