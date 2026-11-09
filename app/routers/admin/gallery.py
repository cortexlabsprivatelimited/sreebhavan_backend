import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import ApiResponse, DeletedOut, created, deleted, listed, ok
from app.core.security import AdminContext, get_current_admin
from app.models import GalleryAlbum, GalleryImage
from app.schemas.admin import (
    GalleryAlbumIn,
    GalleryAlbumOut,
    GalleryImageOut,
    GalleryImagePatch,
    GalleryImagesBulkIn,
)
from app.services.crud import (
    create_record,
    delete_record,
    get_or_404,
    log_activity,
    make_partial,
    update_record,
)

router = APIRouter(prefix="/gallery", tags=["Admin: gallery"])
AlbumPatch = make_partial(GalleryAlbumIn)
UNIQUE = ("slug",)


async def image_counts(db: AsyncSession, album_ids: list[uuid.UUID] | None = None) -> dict[uuid.UUID, int]:
    stmt = select(GalleryImage.album_id, func.count()).group_by(GalleryImage.album_id)
    if album_ids is not None:
        stmt = stmt.where(GalleryImage.album_id.in_(album_ids))
    return {aid: n for aid, n in (await db.execute(stmt)).all()}


def album_out(album: GalleryAlbum, count: int) -> GalleryAlbumOut:
    out = GalleryAlbumOut.model_validate(album)
    out.image_count = count
    return out


# ---- Albums --------------------------------------------------------------------------
@router.get("/albums", response_model=ApiResponse[list[GalleryAlbumOut]])
async def list_albums(db: AsyncSession = Depends(get_db), _: AdminContext = Depends(get_current_admin)):
    albums = (await db.scalars(select(GalleryAlbum).order_by(GalleryAlbum.sort, GalleryAlbum.title))).all()
    counts = await image_counts(db)
    return listed([album_out(a, counts.get(a.id, 0)) for a in albums], "albums")


@router.get("/albums/{album_id}", response_model=ApiResponse[GalleryAlbumOut])
async def read_album(
    album_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: AdminContext = Depends(get_current_admin)
):
    album = await get_or_404(db, GalleryAlbum, album_id, "Album")
    count = (await image_counts(db, [album.id])).get(album.id, 0)
    return ok(album_out(album, count), "Album fetched successfully")


@router.post("/albums", response_model=ApiResponse[GalleryAlbumOut], status_code=201)
async def create_album(
    body: GalleryAlbumIn, db: AsyncSession = Depends(get_db), ctx: AdminContext = Depends(get_current_admin)
):
    album = await create_record(db, GalleryAlbum, body.model_dump(), ctx, "gallery_albums", "Album", UNIQUE)
    return created(album_out(album, 0), "Album created successfully")


@router.patch("/albums/{album_id}", response_model=ApiResponse[GalleryAlbumOut])
async def update_album(
    album_id: uuid.UUID,
    body: AlbumPatch,  # type: ignore[valid-type]
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(get_current_admin),
):
    album = await get_or_404(db, GalleryAlbum, album_id, "Album")
    album = await update_record(
        db, album, GalleryAlbumIn, body.model_dump(exclude_unset=True), ctx, "gallery_albums", "Album", UNIQUE
    )
    count = (await image_counts(db, [album.id])).get(album.id, 0)
    return ok(album_out(album, count), "Album updated successfully")


@router.delete("/albums/{album_id}", response_model=ApiResponse[DeletedOut])
async def delete_album(
    album_id: uuid.UUID, db: AsyncSession = Depends(get_db), ctx: AdminContext = Depends(get_current_admin)
):
    album = await get_or_404(db, GalleryAlbum, album_id, "Album")
    # Explicit delete so it works without ON DELETE CASCADE support (e.g. SQLite in tests).
    await db.execute(delete(GalleryImage).where(GalleryImage.album_id == album.id))
    await delete_record(db, album, ctx, "gallery_albums")
    return deleted(album_id, "Album")


# ---- Images --------------------------------------------------------------------------
@router.get("/images", response_model=ApiResponse[list[GalleryImageOut]])
async def list_images(
    album_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: AdminContext = Depends(get_current_admin),
):
    stmt = (
        select(GalleryImage)
        .where(GalleryImage.album_id == album_id)
        .order_by(GalleryImage.sort, GalleryImage.created_at)
    )
    return listed((await db.scalars(stmt)).all(), "photos")


@router.post("/images", response_model=ApiResponse[list[GalleryImageOut]], status_code=201)
async def add_images(
    body: GalleryImagesBulkIn,
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(get_current_admin),
):
    album = await get_or_404(db, GalleryAlbum, body.album_id, "Album")
    images = [GalleryImage(album_id=album.id, **img.model_dump()) for img in body.images]
    db.add_all(images)
    if not album.cover_url and images:
        album.cover_url = images[0].thumb_url or images[0].url
    await db.flush()
    await log_activity(db, ctx, f"bulk_create:{len(images)}", "gallery_images", album.id)
    noun = "photo" if len(images) == 1 else "photos"
    return created(images, f"{len(images)} {noun} added successfully")


@router.patch("/images/{image_id}", response_model=ApiResponse[GalleryImageOut])
async def update_image(
    image_id: uuid.UUID,
    body: GalleryImagePatch,
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(get_current_admin),
):
    image = await get_or_404(db, GalleryImage, image_id, "Photo")
    image = await update_record(
        db, image, GalleryImagePatch, body.model_dump(exclude_unset=True), ctx, "gallery_images", "Photo"
    )
    return ok(image, "Photo updated successfully")


@router.delete("/images/{image_id}", response_model=ApiResponse[DeletedOut])
async def delete_image(
    image_id: uuid.UUID, db: AsyncSession = Depends(get_db), ctx: AdminContext = Depends(get_current_admin)
):
    image = await get_or_404(db, GalleryImage, image_id, "Photo")
    await delete_record(db, image, ctx, "gallery_images")
    return deleted(image_id, "Photo")
