"""Admin users (Owner only). Accounts live in Supabase Auth; roles live in admin_users."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import conflict
from app.core.responses import ApiResponse, DeletedOut, created, deleted, listed, ok
from app.core.security import AdminContext, require_owner
from app.core.supabase import SupabaseClient, get_supabase
from app.models import AdminUser
from app.schemas.admin import AdminUserIn, AdminUserOut
from app.services.crud import get_or_404, log_activity

router = APIRouter(prefix="/users", tags=["Admin: users (owner only)"])


async def _active_owner_count(db: AsyncSession) -> int:
    stmt = (
        select(func.count())
        .select_from(AdminUser)
        .where(AdminUser.role == "owner", AdminUser.active.is_(True))
    )
    return int(await db.scalar(stmt) or 0)


@router.get("", response_model=ApiResponse[list[AdminUserOut]])
async def list_users(db: AsyncSession = Depends(get_db), _: AdminContext = Depends(require_owner)):
    rows = (await db.scalars(select(AdminUser).order_by(AdminUser.role, AdminUser.name))).all()
    return listed(rows, "admin users")


@router.post("", response_model=ApiResponse[AdminUserOut], status_code=201)
async def invite_user(
    body: AdminUserIn,
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(require_owner),
    supabase: SupabaseClient = Depends(get_supabase),
):
    exists = await db.scalar(
        select(func.count()).select_from(AdminUser).where(func.lower(AdminUser.email) == body.email)
    )
    if exists:
        raise conflict("duplicate_email", f"An admin with the email {body.email} already exists.", "email")
    user_id = uuid.UUID(await supabase.invite_user(body.email, body.name))
    if await db.get(AdminUser, user_id) is not None:
        raise conflict("duplicate_email", f"An admin with the email {body.email} already exists.", "email")
    if body.active:
        await supabase.enable_user(str(user_id))
    else:
        await supabase.disable_user(str(user_id))
    admin = AdminUser(id=user_id, **body.model_dump())
    db.add(admin)
    await db.flush()
    await log_activity(db, ctx, "create", "admin_users", admin.id)
    return created(admin, f"Invite sent to {admin.email}")


@router.patch("/{user_id}", response_model=ApiResponse[AdminUserOut])
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserIn,
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(require_owner),
    supabase: SupabaseClient = Depends(get_supabase),
):
    admin = await get_or_404(db, AdminUser, user_id, "Admin user")
    if admin.id == ctx.id and (body.role != "owner" or not body.active):
        raise conflict("cannot_change_self", "You cannot demote or deactivate your own account.")
    if admin.role == "owner" and admin.active and (body.role != "owner" or not body.active):
        if await _active_owner_count(db) <= 1:
            raise conflict("last_owner", "There must always be at least one active owner.")

    if body.active != admin.active:
        if body.active:
            await supabase.enable_user(str(admin.id))
        else:
            await supabase.disable_user(str(admin.id))
    admin.name = body.name  # email is locked: changes are ignored
    admin.role = body.role
    admin.active = body.active
    await db.flush()
    await log_activity(db, ctx, "update", "admin_users", admin.id)
    return ok(admin, "Admin user updated successfully")


@router.delete("/{user_id}", response_model=ApiResponse[DeletedOut])
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(require_owner),
    supabase: SupabaseClient = Depends(get_supabase),
):
    admin = await get_or_404(db, AdminUser, user_id, "Admin user")
    if admin.id == ctx.id:
        raise conflict("cannot_delete_self", "You cannot delete your own account.")
    if admin.role == "owner" and admin.active and await _active_owner_count(db) <= 1:
        raise conflict("last_owner", "There must always be at least one active owner.")
    await supabase.disable_user(str(admin.id))
    await db.delete(admin)
    await db.flush()
    await log_activity(db, ctx, "delete", "admin_users", user_id)
    return deleted(user_id, "Admin user")


@router.post("/{user_id}/reset-password", response_model=ApiResponse[None])
async def reset_password(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(require_owner),
    supabase: SupabaseClient = Depends(get_supabase),
):
    admin = await get_or_404(db, AdminUser, user_id, "Admin user")
    await supabase.send_password_reset(admin.email)
    await log_activity(db, ctx, "reset_password", "admin_users", admin.id)
    return ok(None, f"A password reset email has been sent to {admin.email}.")
