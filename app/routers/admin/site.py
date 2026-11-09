"""Site settings, businesses, banners, testimonials, FAQs and SEO."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import ApiResponse, listed, ok
from app.core.security import AdminContext, get_current_admin
from app.models import Banner, Business, Faq, SeoMeta, Testimonial
from app.schemas.admin import (
    BannerIn,
    BannerOut,
    BusinessIn,
    BusinessOut,
    FaqIn,
    FaqOut,
    SeoIn,
    SeoOut,
    SiteSettingsBody,
    TestimonialIn,
    TestimonialOut,
)
from app.services.crud import crud_router, fk_check, get_or_404, log_activity, make_partial, update_record
from app.services.site_settings import read_settings, write_settings

router = APIRouter()

# ---- Settings ------------------------------------------------------------------------
settings_router = APIRouter(prefix="/settings", tags=["Admin: site settings"])


@settings_router.get("", response_model=ApiResponse[SiteSettingsBody])
async def get_settings(db: AsyncSession = Depends(get_db), _: AdminContext = Depends(get_current_admin)):
    return ok(await read_settings(db), "Site settings fetched successfully")


@settings_router.put("", response_model=ApiResponse[SiteSettingsBody])
async def put_settings(
    body: SiteSettingsBody, db: AsyncSession = Depends(get_db), ctx: AdminContext = Depends(get_current_admin)
):
    saved = await write_settings(db, body)
    await log_activity(db, ctx, "update", "site_settings")
    return ok(saved, "Site settings saved successfully")


# ---- Businesses (list + edit only) ---------------------------------------------------
businesses_router = APIRouter(prefix="/businesses", tags=["Admin: businesses"])
BusinessPatch = make_partial(BusinessIn)


@businesses_router.get("", response_model=ApiResponse[list[BusinessOut]])
async def list_businesses(db: AsyncSession = Depends(get_db), _: AdminContext = Depends(get_current_admin)):
    return listed(
        (await db.scalars(select(Business).order_by(Business.created_at, Business.slug))).all(), "businesses"
    )


@businesses_router.patch("/{business_id}", response_model=ApiResponse[BusinessOut])
async def update_business(
    business_id: uuid.UUID,
    body: BusinessPatch,  # type: ignore[valid-type]
    db: AsyncSession = Depends(get_db),
    ctx: AdminContext = Depends(get_current_admin),
):
    business = await get_or_404(db, Business, business_id, "Business")
    business = await update_record(
        db, business, BusinessIn, body.model_dump(exclude_unset=True), ctx, "businesses", "Business"
    )
    return ok(business, "Business updated successfully")


router.include_router(settings_router)
router.include_router(businesses_router)
router.include_router(
    crud_router(
        prefix="/banners",
        tag="Admin: banners",
        model=Banner,
        schema_in=BannerIn,
        schema_out=BannerOut,
        entity="banners",
        label="Banner",
        order_by=(Banner.sort, Banner.created_at),
        before_save=fk_check(("business_id", Business, "Business")),
    )
)
router.include_router(
    crud_router(
        prefix="/testimonials",
        tag="Admin: testimonials",
        model=Testimonial,
        schema_in=TestimonialIn,
        schema_out=TestimonialOut,
        entity="testimonials",
        label="Testimonial",
        order_by=(Testimonial.sort, Testimonial.created_at),
        before_save=fk_check(("business_id", Business, "Business")),
    )
)
router.include_router(
    crud_router(
        prefix="/faqs",
        tag="Admin: FAQs",
        model=Faq,
        schema_in=FaqIn,
        schema_out=FaqOut,
        entity="faqs",
        label="FAQ",
        plural="FAQs",
        order_by=(Faq.sort, Faq.created_at),
        before_save=fk_check(("business_id", Business, "Business")),
    )
)
router.include_router(
    crud_router(
        prefix="/seo",
        tag="Admin: SEO",
        model=SeoMeta,
        schema_in=SeoIn,
        schema_out=SeoOut,
        entity="seo_meta",
        label="SEO entry",
        plural="SEO entries",
        unique=("page_key",),
        order_by=(SeoMeta.page_key,),
    )
)
