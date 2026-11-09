import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import not_found
from app.core.responses import ApiResponse, DeletedOut, created, deleted, listed, ok
from app.core.security import AdminContext, get_current_admin
from app.models import Room, RoomImage
from app.schemas.admin import ImageIn, ImageOut, RoomIn, RoomOut
from app.services.crud import create_record, delete_record, get_or_404, make_partial, update_record

router = APIRouter(prefix="/rooms", tags=["Admin: rooms"])
RoomPatch = make_partial(RoomIn)
UNIQUE = ("slug",)


@router.get("", response_model=ApiResponse[list[RoomOut]])
async def list_rooms(db: AsyncSession = Depends(get_db), _: AdminContext = Depends(get_current_admin)):
    return listed((await db.scalars(select(Room).order_by(Room.price, Room.name))).all(), "rooms")


@router.post("", response_model=ApiResponse[RoomOut], status_code=201)
async def create_room(
    body: RoomIn, db: AsyncSession = Depends(get_db), ctx: AdminContext = Depends(get_current_admin)
):
    room = await create_record(db, Room, body.model_dump(), ctx, "rooms", "Room", UNIQUE, images=[])
    return created(room, "Room created successfully")


@router.patch("/{room_id}", response_model=ApiResponse[RoomOut])
async def update_room(
    room_id: uuid.UUID,
    body: RoomPatch,  # type: ignore[valid-type]
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(get_current_admin),
):
    room = await get_or_404(db, Room, room_id, "Room")
    room = await update_record(
        db, room, RoomIn, body.model_dump(exclude_unset=True), ctx, "rooms", "Room", UNIQUE
    )
    return ok(room, "Room updated successfully")


@router.delete("/{room_id}", response_model=ApiResponse[DeletedOut])
async def delete_room(
    room_id: uuid.UUID, db: AsyncSession = Depends(get_db), ctx: AdminContext = Depends(get_current_admin)
):
    room = await get_or_404(db, Room, room_id, "Room")
    await delete_record(db, room, ctx, "rooms")
    return deleted(room_id, "Room")


@router.post("/{room_id}/images", response_model=ApiResponse[ImageOut], status_code=201)
async def add_room_image(
    room_id: uuid.UUID,
    body: ImageIn,
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(get_current_admin),
):
    await get_or_404(db, Room, room_id, "Room")
    image = await create_record(
        db, RoomImage, body.model_dump(), ctx, "room_images", "Room photo", room_id=room_id
    )
    return created(image, "Room photo added successfully")


@router.delete("/{room_id}/images/{image_id}", response_model=ApiResponse[DeletedOut])
async def delete_room_image(
    room_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(get_current_admin),
):
    image = await db.get(RoomImage, image_id)
    if image is None or image.room_id != room_id:
        raise not_found("Room photo")
    await delete_record(db, image, ctx, "room_images")
    return deleted(image_id, "Room photo")
