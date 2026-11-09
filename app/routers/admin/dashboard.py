from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import ApiResponse, ok
from app.core.security import AdminContext, get_current_admin
from app.models import Enquiry, HallBooking
from app.schemas.admin import DashboardStats
from app.schemas.common import Month
from app.services.booking import bookings_in_month, month_range

IST = ZoneInfo("Asia/Kolkata")
router = APIRouter(prefix="/dashboard", tags=["Admin: dashboard"])


def today_ist() -> date:
    return datetime.now(IST).date()


@router.get("/stats", response_model=ApiResponse[DashboardStats])
async def stats(
    month: Month | None = Query(None, description="YYYY-MM; defaults to the current month"),
    db: AsyncSession = Depends(get_db),
    _: AdminContext = Depends(get_current_admin),
):
    today = today_ist()
    month = month or today.strftime("%Y-%m")
    start, end = month_range(month)
    start_ts = datetime.combine(start, time.min, IST)
    end_ts = datetime.combine(end + timedelta(days=1), time.min, IST)

    async def count(*where) -> int:
        return int(await db.scalar(select(func.count()).select_from(Enquiry).where(*where)) or 0)

    month_bookings = await bookings_in_month(db, month)
    upcoming = (
        await db.scalars(
            select(HallBooking)
            .where(HallBooking.date >= today)
            .order_by(HallBooking.date, HallBooking.slot)
            .limit(5)
        )
    ).all()
    recent = (await db.scalars(select(Enquiry).order_by(Enquiry.created_at.desc()).limit(5))).all()

    stats = DashboardStats(
        new_enquiries=await count(Enquiry.status == "new"),
        open_enquiries=await count(Enquiry.status.in_(("new", "contacted"))),
        enquiries_this_month=await count(Enquiry.created_at >= start_ts, Enquiry.created_at < end_ts),
        hall_bookings_this_month=len(month_bookings),
        upcoming_bookings=upcoming,
        recent_enquiries=recent,
        month_bookings=month_bookings,
    )
    return ok(stats, "Dashboard stats fetched successfully")
