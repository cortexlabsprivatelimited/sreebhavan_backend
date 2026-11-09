# Sreebhavan API

FastAPI backend for the **Sreebhavan Veg Hotel** and **Sreebhavanam Event Hall & Rooms** websites. It serves the
Nuxt admin panel (`/api/v1/admin/**`, JWT-protected) and the public site (`/api/v1/public/**`, cached). Only this
API talks to Supabase (Postgres, Auth, Storage).

Stack: FastAPI · Pydantic v2 · SQLAlchemy 2.0 (async, asyncpg) · Alembic · Pillow · httpx · PyJWT.

## Quick start

```bash
uv sync                                  # Python 3.12 + dependencies
cp .env.example .env                     # fill in the Supabase values
uv run alembic upgrade head              # 21 tables, RLS on, businesses seeded, storage buckets
uv run python -m app.cli create-owner --email owner@example.com --name "Owner" --password '<strong password>'
uv run uvicorn app.main:app --reload     # http://localhost:8000/docs
```

After seeding, set the real WhatsApp numbers for both businesses in the admin panel (the seed uses a
placeholder `9000000000`).

## Layout

```
app/
├── core/        config, database, responses + errors (standard envelope), security (JWT), supabase (Auth + Storage), rate limit
├── models/      SQLAlchemy models, all 21 tables
├── schemas/     Pydantic request/response bodies (admin.py, public.py)
├── routers/     admin/ (one module per panel area) and public/
├── services/    crud helpers + activity log, hall booking rules, enquiry + WhatsApp, uploads, settings
├── cli.py       create-owner, create-buckets, cleanup-orphans
└── main.py
alembic/versions/  0001 schema + RLS · 0002 seed businesses · 0003 lock alembic_version · 0004 storage buckets
supabase/          SQL Editor scripts + setup guide (supabase/README.md)
tests/             pytest, SQLite by default or PostgreSQL with TEST_DATABASE_URL
```

## Supabase

Step-by-step project setup is in [supabase/README.md](supabase/README.md). It covers the SQL to run (or
`alembic upgrade head`), the first owner account, and the dashboard settings (secret key, 12-hour token
expiry, redirect URLs, sign-ups off).

## Postman

Import `postman/Sreebhavan-API.postman_collection.json` and an environment from `postman/`. Instructions are in
[postman/README.md](postman/README.md). Swagger UI is at `/docs`, and the raw OpenAPI schema at `/openapi.json`.

## Tests

```bash
uv run pytest                                                     # SQLite, no services needed
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test uv run pytest   # PostgreSQL
uv run ruff check . && uv run ruff format --check .
```

Supabase is replaced by a fake in tests; tokens are signed with a test HS256 secret. The concurrent
double-booking test only runs on PostgreSQL, because it depends on advisory locks.

CI (`.github/workflows/ci.yml`) runs lint, both test modes, `alembic upgrade/check/downgrade` against
Postgres 15, and a Docker build.

## Deploy

`Dockerfile` runs `alembic upgrade head`, then uvicorn on `$PORT`. Set `RUN_MIGRATIONS=false` if your platform
runs migrations as a separate release step. Works on Railway, Render or a VPS.

Production checklist:

- `ENVIRONMENT=production`, and `CORS_ORIGINS` set to exactly the admin and site origins. Localhost is only
  allowed outside production.
- `DATABASE_URL`: the Supabase **session pooler** (IPv4). The direct host is IPv6-only and fails on most hosts.
  The transaction pooler also works, because prepared statements are turned off.
- `SUPABASE_JWT_SECRET` for legacy HS256 projects. Leave it empty to verify with the project's JWKS
  (asymmetric signing keys).
- Supabase Auth: set the JWT expiry to at least 12 hours, since the panel keeps a 12-hour session with no
  refresh. Add `ADMIN_SITE_URL` to the redirect allow-list.
- Optional: `TURNSTILE_SECRET_KEY` (Cloudflare Turnstile on the enquiry form) and `SENTRY_DSN`.
- Schedule `python -m app.cli cleanup-orphans` daily. It deletes uploaded files that no record uses and that are
  older than 24 hours. Use `--dry-run` to preview.
- Backups: automatic on Supabase Pro. On the free tier, schedule a `pg_dump`.

## Response format

Every JSON response uses the standard envelope (`app/core/responses.py`, `app/core/errors.py`). The body's
`status_code` always matches the HTTP status, and the test suite checks this on every request it makes.

```jsonc
// success: one object (POST returns 201)
{ "success": true, "status_code": 200, "message": "Room details fetched successfully", "data": { ... } }

// success: list (always an array; empty -> "No rooms found", "data": [])
{ "success": true, "status_code": 200, "message": "Rooms fetched successfully", "data": [ ... ] }

// success: paginated (GET /admin/enquiries?page=1&per_page=20)
{ "success": true, "status_code": 200, "message": "Enquiries fetched successfully", "data": [ ... ],
  "meta": { "current_page": 1, "per_page": 20, "total_records": 125, "total_pages": 7 } }

// delete -> data is the deleted id; logout / forgot-password / reset-password -> data is null
{ "success": true, "status_code": 200, "message": "Banner deleted successfully", "data": { "id": "..." } }

// error: validation (several fields -> "Validation failed"; one field -> that field's message)
{ "success": false, "status_code": 422, "message": "Validation failed",
  "errors": [ { "field": "name", "message": "Name is required." }, { "field": "phone", "message": "..." } ] }

// error: auth, permission, not found, rate limit, server
{ "success": false, "status_code": 401, "message": "Session expired. Please log in again.", "errors": [] }
```

- Business-rule errors that belong to a field put it in `errors` too: a duplicate slug (`slug`), a taken hall
  slot (`slot`), an unknown category (`category_id`), or a rejected upload (`file`).
- `GET /admin/enquiries/export.csv` is a file download, so it has no envelope. Its errors still use the format.
- Rate-limited requests (429) send a `Retry-After` header.
- `GET /admin/enquiries` takes `per_page`. The old `page_size` still works.

## Decisions beyond the spec

These are places where the spec left a choice open, or where I added a safeguard. The frontend contract is not
changed.

| Topic | What the API does |
|---|---|
| Double booking | Checks for overlaps inside the transaction under `pg_advisory_xact_lock` per date, on top of `UNIQUE(date, slot)`. `full` ↔ `morning`/`evening` clashes return `409` with the error on field `slot`. |
| PATCH bodies | Every PATCH accepts full **or** partial bodies. The patch is merged onto the stored record and validated against the full schema, so a required field can never be cleared. |
| Bad foreign keys | A `category_id` or `business_id` that points at nothing returns `422` on that field, not a database error. |
| Public hall enquiry | Returns `409` if the slot is already **booked**. Tentative slots still accept enquiries. Dates in the past return `422`. |
| Honeypot | If the `website` field is filled in, the API returns a fake success and saves nothing. |
| Rate limit | In memory, 5 enquiries per IP per 10 minutes (configurable). Use Redis if you run more than one instance. |
| Uploads | Images become WebP (max width 1920) plus a `_thumb.webp` (480). SVGs with scripts or event handlers are rejected. Bucket = first part of `folder` (`menu/items` → bucket `menu`, path `items/…`). |
| CSV export | UTF-8 with BOM (so Excel shows Malayalam correctly). Cells starting with `= + - @` are escaped. Times are in IST. |
| `last_sign_in_at` | Set by `/admin/auth/login`, so no Supabase call is needed when listing users. |
| Admin users | Besides the self-protection rules, the API refuses to remove the **last** active owner. Deleted admins are banned in Supabase Auth, not hard-deleted. |
| Gallery | The first bulk upload into an album with no cover sets the cover automatically. |
| `seo_id` columns | Left out. SEO is keyed by `page_key` (`room/<slug>`, …) as the spec describes. |
| `room_blocks` | Table exists. No endpoints yet, as it is optional in phase 1. |
| Docs | `/docs` is on by default. Set `ENABLE_DOCS=false` to hide it in production. |

Public endpoint shapes are in [docs/public-api.md](docs/public-api.md).
