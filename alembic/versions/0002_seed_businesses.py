"""Seed the two businesses. Their slugs are fixed because they are part of the public URLs.

The first owner account needs a Supabase Auth user, so it is created with the CLI instead:
    uv run python -m app.cli create-owner --email ... --name ... --password ...

Revision ID: 0002_seed_businesses
Revises: 0001_initial
Create Date: 2026-11-07
"""

import json

from alembic import op

revision = "0002_seed_businesses"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

BUSINESSES = [
    {
        "slug": "sreebhavan-veg-hotel",
        "name": "Sreebhavan Veg Hotel",
        "about": "Pure vegetarian Kerala meals.",
        "whatsapp": "9000000000",
        "timings": [{"label": "Mon – Sun", "hours": "6:00 am – 10:00 pm"}],
    },
    {
        "slug": "sreebhavanam",
        "name": "Sreebhavanam",
        "about": "Event hall and rooms.",
        "whatsapp": "9000000000",
        "timings": [{"label": "Front desk", "hours": "Open 24 hours"}],
    },
]


def _lit(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    # Literal values (not bound parameters) so `alembic upgrade head --sql` renders a usable script too.
    for b in BUSINESSES:
        op.execute(
            "INSERT INTO businesses (slug, name, about, whatsapp, timings) VALUES ("
            f"{_lit(b['slug'])}, {_lit(b['name'])}, {_lit(b['about'])}, {_lit(b['whatsapp'])}, "
            f"CAST({_lit(json.dumps(b['timings'], ensure_ascii=False))} AS jsonb)) "
            "ON CONFLICT (slug) DO NOTHING"
        )


def downgrade() -> None:
    op.execute("DELETE FROM businesses WHERE slug IN ('sreebhavan-veg-hotel', 'sreebhavanam')")
