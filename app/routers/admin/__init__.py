from fastapi import APIRouter

from app.core.responses import ERROR_RESPONSES
from app.routers.admin import auth, dashboard, enquiries, gallery, hall, menu, rooms, site, uploads, users

router = APIRouter(prefix="/admin", responses=ERROR_RESPONSES)
for module in (auth, dashboard, site, menu, rooms, hall, enquiries, gallery, uploads, users):
    router.include_router(module.router)
