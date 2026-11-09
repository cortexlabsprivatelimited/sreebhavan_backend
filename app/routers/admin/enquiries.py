import csv
import io
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import ApiResponse, PaginatedResponse, ok, paginated
from app.core.security import AdminContext, get_current_admin
from app.models import Enquiry
from app.schemas.admin import EnquiryOut, EnquiryPatch
from app.schemas.common import EnquiryStatus, EnquiryType
from app.services.crud import get_or_404, log_activity

IST = ZoneInfo("Asia/Kolkata")
router = APIRouter(prefix="/enquiries", tags=["Admin: enquiries"])


def _filtered(type: str | None, status: str | None, q: str | None) -> Select:
    stmt = select(Enquiry)
    if type:
        stmt = stmt.where(Enquiry.type == type)
    if status:
        stmt = stmt.where(Enquiry.status == status)
    if q and q.strip():
        term = q.strip()
        like = f"%{term.replace('%', r'\%').replace('_', r'\_')}%"
        digits = "".join(ch for ch in term if ch.isdigit())
        conds = [Enquiry.name.ilike(like, escape="\\")]
        if digits:
            conds.append(Enquiry.phone.like(f"%{digits}%"))
        stmt = stmt.where(or_(*conds))
    return stmt


@router.get("", response_model=PaginatedResponse[EnquiryOut])
async def list_enquiries(
    type: EnquiryType | None = None,
    status: EnquiryStatus | None = None,
    q: str | None = Query(None, max_length=100, description="Search name or phone"),
    page: int = Query(1, ge=1),
    per_page: int | None = Query(None, ge=1, le=100, description="Records per page (default 20)"),
    page_size: int | None = Query(None, ge=1, le=100, deprecated=True, description="Old name for per_page"),
    db: AsyncSession = Depends(get_db),
    _: AdminContext = Depends(get_current_admin),
):
    size = per_page or page_size or 20
    base = _filtered(type, status, q)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = (
        await db.scalars(
            base.order_by(Enquiry.created_at.desc(), Enquiry.id).offset((page - 1) * size).limit(size)
        )
    ).all()
    return paginated(rows, page=page, per_page=size, total=total, plural="enquiries")


CSV_COLUMNS = [
    "created_at", "type", "status", "name", "phone", "email", "date_from", "date_to", "slot", "guests",
    "event_type", "room_name", "message", "admin_notes", "id",
]  # fmt: skip


def _csv_value(v) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.astimezone(IST).strftime("%Y-%m-%d %H:%M")
    s = str(v)
    # Stop spreadsheet formula injection.
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


@router.get("/export.csv", response_class=StreamingResponse)
async def export_enquiries(
    type: EnquiryType | None = None,
    status: EnquiryStatus | None = None,
    q: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db),
    _: AdminContext = Depends(get_current_admin),
):
    rows = (await db.scalars(_filtered(type, status, q).order_by(Enquiry.created_at.desc()))).all()
    buf = io.StringIO()
    buf.write("﻿")  # BOM so Excel reads Malayalam names correctly
    writer = csv.writer(buf)
    writer.writerow(CSV_COLUMNS)
    for r in rows:
        writer.writerow([_csv_value(getattr(r, c)) for c in CSV_COLUMNS])
    filename = f"enquiries-{datetime.now(IST).strftime('%Y-%m-%d')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{enquiry_id}", response_model=ApiResponse[EnquiryOut])
async def update_enquiry(
    enquiry_id: uuid.UUID,
    body: EnquiryPatch,
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(get_current_admin),
):
    enquiry = await get_or_404(db, Enquiry, enquiry_id, "Enquiry")
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "status" and v is None:
            continue
        setattr(enquiry, k, v)
    await db.flush()
    await log_activity(db, ctx, "update", "enquiries", enquiry.id)
    return ok(enquiry, "Enquiry updated successfully")
