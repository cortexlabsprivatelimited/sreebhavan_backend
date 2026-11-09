from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SiteSetting
from app.schemas.admin import SETTINGS_KEYS, SiteSettingsBody


async def read_settings(db: AsyncSession) -> SiteSettingsBody:
    rows = (await db.scalars(select(SiteSetting).where(SiteSetting.key.in_(SETTINGS_KEYS)))).all()
    return SiteSettingsBody.model_validate({r.key: r.value for r in rows})


async def write_settings(db: AsyncSession, body: SiteSettingsBody) -> SiteSettingsBody:
    existing = {
        r.key: r
        for r in (await db.scalars(select(SiteSetting).where(SiteSetting.key.in_(SETTINGS_KEYS)))).all()
    }
    for key, value in body.model_dump().items():
        row = existing.get(key)
        if row is None:
            db.add(SiteSetting(key=key, value=value))
        elif row.value != value:
            row.value = value
    await db.flush()
    return await read_settings(db)
