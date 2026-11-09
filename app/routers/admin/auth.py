import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.responses import ApiResponse, ok
from app.core.security import AdminContext, get_current_admin
from app.core.supabase import SupabaseClient, get_supabase
from app.models import AdminUser
from app.models.base import utcnow
from app.schemas.admin import ForgotPasswordIn, LoginIn, LoginOut
from app.services.crud import log_activity

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Admin: auth"])


@router.post("/login", response_model=ApiResponse[LoginOut])
async def login(
    body: LoginIn, db: AsyncSession = Depends(get_db), supabase: SupabaseClient = Depends(get_supabase)
):
    session = await supabase.sign_in_with_password(body.email, body.password)
    try:
        user_id = uuid.UUID(session["user"]["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(401, "invalid_credentials", "Wrong email or password.") from exc

    admin = await db.get(AdminUser, user_id)
    if admin is None or not admin.active:
        await supabase.sign_out(session["access_token"])
        raise AppError(401, "invalid_credentials", "This account does not have admin access.")

    admin.last_sign_in_at = utcnow()
    await log_activity(db, AdminContext(admin, ""), "login", "admin_users", admin.id)
    data = LoginOut(access_token=session["access_token"], admin=admin)
    return ok(data, "Logged in successfully")


@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    ctx: AdminContext = Depends(get_current_admin), supabase: SupabaseClient = Depends(get_supabase)
):
    await supabase.sign_out(ctx.token)
    return ok(None, "Logged out successfully")


@router.post("/forgot-password", response_model=ApiResponse[None])
async def forgot_password(
    body: ForgotPasswordIn,
    db: AsyncSession = Depends(get_db),
    supabase: SupabaseClient = Depends(get_supabase),
):
    # Always 200 so the form cannot be used to discover admin emails.
    stmt = select(AdminUser).where(
        func.lower(AdminUser.email) == body.email.lower(), AdminUser.active.is_(True)
    )
    admin = (await db.scalars(stmt)).first()
    if admin is not None:
        try:
            await supabase.send_password_reset(admin.email)
        except AppError:
            log.exception("Password reset email failed for admin %s", admin.id)
    return ok(None, "If this email belongs to an admin, a reset link has been sent.")
