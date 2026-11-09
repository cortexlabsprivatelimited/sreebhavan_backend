"""Hall calendar rules.

A `full` booking blocks `morning` and `evening` on the same date, and a `morning` or `evening` booking blocks
`full`. UNIQUE(date, slot) alone cannot express that, so the check runs here inside the request transaction,
serialised per date with a Postgres advisory lock so two admins cannot race each other.
"""

import calendar
import uuid
from datetime import date

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, conflict
from app.models import HallBooking

SLOT_LABELS = {"morning": "Morning", "evening": "Evening", "full": "Full day"}


def month_range(month: str) -> tuple[date, date]:
    """'2026-11' -> (2026-11-01, 2026-11-30)."""
    try:
        year, mon = (int(p) for p in month.split("-"))
        last = calendar.monthrange(year, mon)[1]
        return date(year, mon, 1), date(year, mon, last)
    except (ValueError, TypeError) as exc:
        raise AppError(422, "invalid_month", "Month must look like 2026-11.", "month") from exc


def blocking_slots(slot: str) -> tuple[str, ...]:
    """Slots that cannot coexist with `slot` on the same date."""
    if slot == "full":
        return ("morning", "evening", "full")
    return (slot, "full")


async def lock_date(db: AsyncSession, day: date) -> None:
    if db.bind.dialect.name == "postgresql":
        # Transaction-scoped; released on commit/rollback. Key namespace 7101 = hall bookings.
        await db.execute(text("SELECT pg_advisory_xact_lock(7101, :k)"), {"k": day.toordinal()})


async def ensure_slot_free(
    db: AsyncSession, day: date, slot: str, exclude_id: uuid.UUID | None = None
) -> None:
    await lock_date(db, day)
    stmt = select(HallBooking).where(HallBooking.date == day, HallBooking.slot.in_(blocking_slots(slot)))
    if exclude_id is not None:
        stmt = stmt.where(HallBooking.id != exclude_id)
    clash = (await db.scalars(stmt.limit(1))).first()
    if clash is not None:
        when = day.strftime("%d-%b-%Y")
        if clash.slot == slot:
            msg = f"{when} ({SLOT_LABELS[slot]}) is already {clash.status}."
        else:
            msg = (
                f"{when} already has a {SLOT_LABELS[clash.slot].lower()} booking ({clash.status}), "
                f"so the {SLOT_LABELS[slot].lower()} slot is not free."
            )
        raise conflict("slot_taken", msg, "slot")


async def bookings_in_month(db: AsyncSession, month: str) -> list[HallBooking]:
    start, end = month_range(month)
    stmt = (
        select(HallBooking)
        .where(HallBooking.date >= start, HallBooking.date <= end)
        .order_by(HallBooking.date, HallBooking.slot)
    )
    return list((await db.scalars(stmt)).all())


async def count_bookings_in_month(db: AsyncSession, month: str) -> int:
    start, end = month_range(month)
    stmt = (
        select(func.count())
        .select_from(HallBooking)
        .where(HallBooking.date >= start, HallBooking.date <= end)
    )
    return int(await db.scalar(stmt) or 0)
