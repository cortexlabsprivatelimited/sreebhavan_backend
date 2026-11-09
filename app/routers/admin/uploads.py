from typing import get_args

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError, unprocessable
from app.core.responses import ApiResponse, created
from app.core.security import AdminContext, get_current_admin
from app.core.supabase import SupabaseClient, get_supabase
from app.schemas.admin import UploadOut
from app.schemas.common import UploadFolder
from app.services.crud import log_activity
from app.services.uploads import store_upload

router = APIRouter(prefix="/uploads", tags=["Admin: uploads"])
FOLDERS = get_args(UploadFolder)


@router.post("", response_model=ApiResponse[UploadOut], status_code=201)
async def upload(
    file: UploadFile = File(...),
    folder: str = Form(..., description=" | ".join(FOLDERS)),
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(get_current_admin),
    supabase: SupabaseClient = Depends(get_supabase),
):
    if folder not in FOLDERS:
        raise unprocessable("invalid_folder", f"Folder must be one of: {', '.join(FOLDERS)}.", "folder")
    limit = get_settings().upload_max_bytes
    content = await file.read(limit + 1)
    try:
        stored = await store_upload(supabase, folder, content, file.filename, user_token=ctx.token)
    except AppError as exc:
        exc.field = exc.field or ("file" if exc.status == 422 else None)
        raise
    await log_activity(db, ctx, "upload", folder, stored.url.rsplit("/", 1)[-1][:64])
    return created(UploadOut(url=stored.url, thumb_url=stored.thumb_url), "File uploaded successfully")
