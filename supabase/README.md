# Supabase setup

These steps set up project `gfelfsrogwtxjhstjcbu` (region `ap-south-1`) for the Sreebhavan API. Do them once,
in this order.

| File | What it does |
|---|---|
| `01_schema.sql` | Creates the 21 tables with row-level security on, removes direct table access for the `anon` and `authenticated` roles, seeds the two businesses, creates the 8 storage buckets, and records the migration version. Generated from the Alembic migrations. |
| `02_first_owner.sql` | Makes a Supabase Auth user the admin panel's owner |
| `03_verify.sql` | Read-only health check. Every row should say **OK**. |

## 1. Create the database objects

Choose **one** of these options.

**Option A: SQL Editor (no tools needed)**

1. Open Supabase dashboard › **SQL Editor** › **New query**.
2. Paste the whole of `01_schema.sql` and click **Run**. It runs in one transaction, so it either fully
   succeeds or changes nothing.

**Option B: Alembic, from this repo**

```bash
uv run alembic upgrade head     # uses DATABASE_URL from .env
```

Both options give the same result. Either way, later schema changes are applied with
`uv run alembic upgrade head`.

## 2. Create the owner account

1. Open **Authentication** › **Users** › **Add user** › **Create new user**.
2. Enter the owner's email and a strong password, and tick **Auto Confirm User**.
3. In `02_first_owner.sql`, change the email and name, then run it in the SQL Editor.

If you have the secret key in `.env`, you can do steps 1–3 in one command instead:
`uv run python -m app.cli create-owner --email … --name … --password …`

## 3. Dashboard settings

| Where | Setting | Value |
|---|---|---|
| **Project Settings › API Keys › Secret keys** | Copy the `sb_secret_…` key into `.env` as `SUPABASE_SECRET_KEY` | Needed for uploads, invites and admin-user management. Never put it in a frontend. |
| **Project Settings › JWT Keys** (older dashboards: **Authentication › Settings**) | Access token expiry | `43200` (12 hours). The panel keeps a 12-hour session and has no refresh. |
| **Authentication › URL Configuration** | Site URL | The admin panel URL, e.g. `https://admin.example.com` |
| **Authentication › URL Configuration** | Redirect URLs | `<admin URL>/reset-password` and `<admin URL>/set-password`. Add `http://localhost:3001/**` for development. |
| **Authentication › Sign In / Providers** | Allow new users to sign up | **Off**. Admins are invited; nobody should self-register. |
| **Project Settings › Data API** (optional) | Enable Data API | **Off**. Only this API talks to the database, so the auto-generated REST API isn't needed. RLS already blocks it, so this is extra hardening. |

## 4. Check it

Run `03_verify.sql` in the SQL Editor:

```
check               | result
--------------------+-------
tables              | OK
row level security  | OK
no public grants    | OK
businesses          | OK
storage buckets     | OK
owner account       | OK
migration version   | OK
```

Then sign in to the admin panel and set the **real WhatsApp numbers** for both businesses. The seed uses the
placeholder `9000000000`, and every enquiry link goes to that number until you change it.

## Connection string

Use the **session pooler**, not the direct host:

```
postgresql+asyncpg://postgres.gfelfsrogwtxjhstjcbu:<password>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```

- The direct host `db.gfelfsrogwtxjhstjcbu.supabase.co` only has an IPv6 address. It doesn't resolve on
  networks without IPv6, or on most hosting platforms.
- URL-encode special characters in the password: `@` → `%40`, `#` → `%23`, `/` → `%2F`.
- The real values for local development are in `.env`, which is git-ignored. On a hosting platform, set them
  as environment variables.

## Regenerating `01_schema.sql`

After adding a migration, regenerate the file:

```bash
uv run python scripts/export_supabase_sql.py
```

CI fails if the committed file doesn't match the migrations. On an existing database, apply new migrations
with `uv run alembic upgrade head`. Don't re-run the full file.
