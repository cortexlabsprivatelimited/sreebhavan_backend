"""Management commands.

uv run python -m app.cli create-owner --email owner@example.com --name "Sajith" --password "..."
uv run python -m app.cli create-buckets
uv run python -m app.cli cleanup-orphans [--older-than-hours 24] [--dry-run]
"""

import argparse
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal, engine
from app.core.supabase import close_supabase, get_supabase
from app.models import (
    AdminUser,
    Banner,
    Business,
    GalleryAlbum,
    GalleryImage,
    HallImage,
    MenuCard,
    MenuCategory,
    MenuItem,
    RoomImage,
    SeoMeta,
    SiteSetting,
)
from app.services.uploads import BUCKETS


async def create_owner(email: str, name: str, password: str) -> None:
    sb = get_supabase()
    user_id = uuid.UUID(await sb.create_user(email.lower(), password, name))
    async with SessionLocal() as db:
        admin = await db.get(AdminUser, user_id)
        if admin is None:
            db.add(AdminUser(id=user_id, name=name, email=email.lower(), role="owner", active=True))
        else:
            admin.role, admin.active, admin.name = "owner", True, name
        await db.commit()
    print(f"Owner ready: {email} ({user_id})")


async def create_buckets() -> None:
    sb = get_supabase()
    for bucket in BUCKETS:
        await sb.create_bucket(bucket)
        print(f"bucket ok: {bucket}")


async def _referenced_urls() -> set[str]:
    cols = [
        Business.logo_url, Banner.image_url, MenuCategory.image_url, MenuItem.image_url, MenuCard.file_url,
        RoomImage.url, HallImage.url, GalleryAlbum.cover_url, GalleryImage.url, GalleryImage.thumb_url,
        SeoMeta.og_image,
    ]  # fmt: skip
    urls: set[str] = set()
    async with SessionLocal() as db:
        for col in cols:
            urls.update(u for u in (await db.scalars(select(col))).all() if u)
        for value in (await db.scalars(select(SiteSetting.value))).all():
            if isinstance(value, str) and value.startswith("http"):
                urls.add(value)
    return urls


async def _walk(bucket: str, prefix: str = ""):
    sb = get_supabase()
    offset = 0
    while True:
        batch = await sb.list_objects(bucket, prefix, limit=1000, offset=offset)
        if not batch:
            return
        for obj in batch:
            path = f"{prefix}{obj['name']}"
            if obj.get("id") is None:  # a folder
                async for child in _walk(bucket, path + "/"):
                    yield child
            else:
                yield path, obj
        if len(batch) < 1000:
            return
        offset += 1000


async def cleanup_orphans(older_than_hours: int, dry_run: bool) -> None:
    """Deletes stored files no record points to (uploaded but never saved), older than the grace period."""
    sb = get_supabase()
    referenced = await _referenced_urls()
    cutoff = datetime.now(UTC) - timedelta(hours=older_than_hours)
    total = 0
    for bucket in BUCKETS:
        orphans = []
        async for path, obj in _walk(bucket):
            created = obj.get("created_at")
            if created and datetime.fromisoformat(created.replace("Z", "+00:00")) > cutoff:
                continue
            url = sb.public_url(bucket, path)
            # A thumbnail is kept while its full-size image is referenced, and vice versa.
            sibling = (
                url.replace("_thumb.webp", ".webp")
                if url.endswith("_thumb.webp")
                else url.replace(".webp", "_thumb.webp")
            )
            if url not in referenced and sibling not in referenced:
                orphans.append(path)
        total += len(orphans)
        print(f"{bucket}: {len(orphans)} orphan file(s)")
        if orphans and not dry_run:
            for i in range(0, len(orphans), 100):
                await sb.delete_objects(bucket, orphans[i : i + 100])
    print(f"{'Would delete' if dry_run else 'Deleted'} {total} file(s).")


async def _main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-owner", help="Create (or promote) the owner account")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--password", required=True)
    sub.add_parser("create-buckets", help="Create the public Supabase Storage buckets")
    p = sub.add_parser("cleanup-orphans", help="Delete uploaded files that no record uses")
    p.add_argument("--older-than-hours", type=int, default=24)
    p.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.cmd == "create-owner":
            await create_owner(args.email, args.name, args.password)
        elif args.cmd == "create-buckets":
            await create_buckets()
        elif args.cmd == "cleanup-orphans":
            await cleanup_orphans(args.older_than_hours, args.dry_run)
    finally:
        await close_supabase()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
