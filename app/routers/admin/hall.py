import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import not_found
from app.core.responses import ApiResponse, DeletedOut, created, deleted, listed, ok
from app.core.security import AdminContext, get_current_admin
from app.models import Hall, HallBooking, HallImage, HallPackage
from app.schemas.admin import (
    HallBookingIn,
    HallBookingOut,
    HallIn,
    HallOut,
    HallPackageIn,
    HallPackageOut,
    ImageIn,
    ImageOut,
)
from app.schemas.common import Month
from app.services.booking import bookings_in_month, ensure_slot_free
from app.services.crud import (
    create_record,
    crud_router,
    delete_record,
    get_or_404,
    log_activity,
    make_partial,
    merge_and_validate,
)

router = APIRouter(prefix="/hall", tags=["Admin: event hall"])


async def get_hall(db: AsyncSession) -> Hall | None:
    return (await db.scalars(select(Hall).order_by(Hall.created_at).limit(1))).first()


@router.get("", response_model=ApiResponse[HallOut])
async def read_hall(db: AsyncSession = Depends(get_db), _: AdminContext = Depends(get_current_admin)):
    hall = await get_hall(db)
    if hall is None:
        raise not_found("Hall details")
    return ok(hall, "Hall details fetched successfully")


@router.put("", response_model=ApiResponse[HallOut])
async def save_hall(
    body: HallIn, db: AsyncSession = Depends(get_db), ctx: AdminContext = Depends(get_current_admin)
):
    hall = await get_hall(db)
    if hall is None:
        hall = Hall(**body.model_dump())
        db.add(hall)
    else:
        for k, v in body.model_dump().items():
            setattr(hall, k, v)
    await db.flush()
    await log_activity(db, ctx, "update", "hall", hall.id)
    return ok(hall, "Hall details saved successfully")


# ---- Packages ------------------------------------------------------------------------
router.include_router(
    crud_router(
        prefix="/packages",
        tag="Admin: event hall",
        model=HallPackage,
        schema_in=HallPackageIn,
        schema_out=HallPackageOut,
        entity="hall_packages",
        label="Hall package",
        order_by=(HallPackage.sort, HallPackage.created_at),
    )
)


# ---- Photos --------------------------------------------------------------------------
@router.get("/images", response_model=ApiResponse[list[ImageOut]])
async def list_hall_images(db: AsyncSession = Depends(get_db), _: AdminContext = Depends(get_current_admin)):
    rows = (await db.scalars(select(HallImage).order_by(HallImage.sort, HallImage.created_at))).all()
    return listed(rows, "hall photos")


@router.post("/images", response_model=ApiResponse[ImageOut], status_code=201)
async def add_hall_image(
    body: ImageIn, db: AsyncSession = Depends(get_db), ctx: AdminContext = Depends(get_current_admin)
):
    image = await create_record(db, HallImage, body.model_dump(), ctx, "hall_images", "Hall photo")
    return created(image, "Hall photo added successfully")


@router.delete("/images/{image_id}", response_model=ApiResponse[DeletedOut])
async def delete_hall_image(
    image_id: uuid.UUID, db: AsyncSession = Depends(get_db), ctx: AdminContext = Depends(get_current_admin)
):
    image = await get_or_404(db, HallImage, image_id, "Hall photo")
    await delete_record(db, image, ctx, "hall_images")
    return deleted(image_id, "Hall photo")


# ---- Calendar ------------------------------------------------------------------------
BookingPatch = make_partial(HallBookingIn)


@router.get("/bookings", response_model=ApiResponse[list[HallBookingOut]])
async def list_bookings(
    month: Month = Query(..., description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    _: AdminContext = Depends(get_current_admin),
):
    return listed(await bookings_in_month(db, month), "bookings")


@router.post("/bookings", response_model=ApiResponse[HallBookingOut], status_code=201)
async def create_booking(
    body: HallBookingIn, db: AsyncSession = Depends(get_db), ctx: AdminContext = Depends(get_current_admin)
):
    await ensure_slot_free(db, body.date, body.slot)
    booking = await create_record(
        db, HallBooking, body.model_dump(), ctx, "hall_bookings", "Booking", created_by=ctx.id
    )
    return created(booking, "Booking created successfully")


@router.patch("/bookings/{booking_id}", response_model=ApiResponse[HallBookingOut])
async def update_booking(
    booking_id: uuid.UUID,
    body: BookingPatch,  # type: ignore[valid-type]
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(get_current_admin),
):
    booking = await get_or_404(db, HallBooking, booking_id, "Booking")
    data = merge_and_validate(booking, HallBookingIn, body.model_dump(exclude_unset=True))
    if data["date"] != booking.date or data["slot"] != booking.slot:
        await ensure_slot_free(db, data["date"], data["slot"], exclude_id=booking.id)
    for k, v in data.items():
        setattr(booking, k, v)
    await db.flush()
    await log_activity(db, ctx, "update", "hall_bookings", booking.id)
    return ok(booking, "Booking updated successfully")


@router.delete("/bookings/{booking_id}", response_model=ApiResponse[DeletedOut])
async def delete_booking(
    booking_id: uuid.UUID, db: AsyncSession = Depends(get_db), ctx: AdminContext = Depends(get_current_admin)
):
    booking = await get_or_404(db, HallBooking, booking_id, "Booking")
    await delete_record(db, booking, ctx, "hall_bookings")
    return deleted(booking_id, "Booking")
