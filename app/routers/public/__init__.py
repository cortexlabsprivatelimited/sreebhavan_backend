"""Public endpoints for the user website: no login, read-only (except the enquiry form), cacheable."""

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import not_found
from app.core.ratelimit import client_ip, limit_enquiries
from app.core.responses import ERROR_RESPONSES, ApiResponse, created, listed, ok
from app.models import (
    Banner,
    Business,
    Faq,
    GalleryAlbum,
    GalleryImage,
    Hall,
    HallImage,
    HallPackage,
    MenuCard,
    MenuCategory,
    MenuItem,
    Room,
    SeoMeta,
    Testimonial,
)
from app.routers.admin.gallery import image_counts
from app.schemas.admin import SiteSettingsBody
from app.schemas.common import Month
from app.schemas.public import (
    Availability,
    EnquiryCreated,
    EnquiryIn,
    PublicAlbum,
    PublicAlbumDetail,
    PublicBanner,
    PublicBusiness,
    PublicFaq,
    PublicGalleryImage,
    PublicHall,
    PublicHallPackage,
    PublicImage,
    PublicMenuCard,
    PublicMenuCategory,
    PublicMenuItem,
    PublicRoom,
    PublicSeo,
    PublicTestimonial,
    SitemapData,
    SitemapEntry,
)
from app.services.booking import bookings_in_month
from app.services.enquiry import create_enquiry, honeypot_response, verify_turnstile
from app.services.site_settings import read_settings


def cache(max_age: int | None = None, swr: int | None = None):
    async def _set(response: Response) -> None:
        s = get_settings()
        ma = s.public_cache_max_age if max_age is None else max_age
        sw = s.public_cache_swr if swr is None else swr
        response.headers["Cache-Control"] = (
            f"public, max-age={ma}, s-maxage={ma}, stale-while-revalidate={sw}"
        )

    return _set


cached = APIRouter(dependencies=[Depends(cache())])
router = APIRouter(prefix="/public", tags=["Public"], responses=ERROR_RESPONSES)


async def _business_id(db: AsyncSession, slug: str | None):
    """?business=<slug>: that business's rows plus the shared ones (business_id null)."""
    if not slug:
        return None
    business = (await db.scalars(select(Business).where(Business.slug == slug))).first()
    if business is None:
        raise not_found("Business")
    return business.id


# ---- Site ----------------------------------------------------------------------------
@cached.get("/settings", response_model=ApiResponse[SiteSettingsBody])
async def settings(db: AsyncSession = Depends(get_db)):
    return ok(await read_settings(db), "Site settings fetched successfully")


@cached.get("/businesses/{slug}", response_model=ApiResponse[PublicBusiness])
async def business(slug: str, db: AsyncSession = Depends(get_db)):
    obj = (await db.scalars(select(Business).where(Business.slug == slug))).first()
    if obj is None:
        raise not_found("Business")
    return ok(obj, "Business details fetched successfully")


@cached.get("/banners", response_model=ApiResponse[list[PublicBanner]])
async def banners(
    business: str | None = Query(None, description="Business slug; omit for home-page banners"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Banner).where(Banner.active.is_(True))
    bid = await _business_id(db, business)
    stmt = stmt.where(Banner.business_id == bid) if bid else stmt.where(Banner.business_id.is_(None))
    return listed((await db.scalars(stmt.order_by(Banner.sort, Banner.created_at))).all(), "banners")


# ---- Menu ----------------------------------------------------------------------------
@cached.get("/menu/categories", response_model=ApiResponse[list[PublicMenuCategory]])
async def menu_categories(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MenuCategory)
        .where(MenuCategory.active.is_(True))
        .order_by(MenuCategory.sort, MenuCategory.name)
    )
    return listed((await db.scalars(stmt)).all(), "menu categories")


@cached.get("/menu/items", response_model=ApiResponse[list[PublicMenuItem]])
async def menu_items(
    category: str | None = Query(None, description="Category slug"),
    special: bool | None = Query(None, description="true = today's specials only"),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(MenuItem)
        .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
        .where(MenuItem.is_available.is_(True), MenuCategory.active.is_(True))
    )
    if category:
        stmt = stmt.where(MenuCategory.slug == category)
    if special is not None:
        stmt = stmt.where(MenuItem.is_special.is_(special))
    rows = (await db.scalars(stmt.order_by(MenuCategory.sort, MenuItem.sort, MenuItem.name))).all()
    return listed(rows, "menu items")


@cached.get("/menu/cards", response_model=ApiResponse[list[PublicMenuCard]])
async def menu_cards(db: AsyncSession = Depends(get_db)):
    stmt = select(MenuCard).where(MenuCard.active.is_(True)).order_by(MenuCard.created_at)
    return listed((await db.scalars(stmt)).all(), "menu cards")


# ---- Rooms ---------------------------------------------------------------------------
@cached.get("/rooms", response_model=ApiResponse[list[PublicRoom]])
async def rooms(db: AsyncSession = Depends(get_db)):
    stmt = select(Room).where(Room.active.is_(True)).order_by(Room.price, Room.name)
    return listed((await db.scalars(stmt)).all(), "rooms")


@cached.get("/rooms/{slug}", response_model=ApiResponse[PublicRoom])
async def room(slug: str, db: AsyncSession = Depends(get_db)):
    obj = (await db.scalars(select(Room).where(Room.slug == slug, Room.active.is_(True)))).first()
    if obj is None:
        raise not_found("Room")
    return ok(obj, "Room details fetched successfully")


# ---- Hall ----------------------------------------------------------------------------
@cached.get("/hall", response_model=ApiResponse[PublicHall])
async def hall(db: AsyncSession = Depends(get_db)):
    obj = (await db.scalars(select(Hall).order_by(Hall.created_at).limit(1))).first()
    if obj is None:
        raise not_found("Hall details")
    images = (await db.scalars(select(HallImage).order_by(HallImage.sort, HallImage.created_at))).all()
    out = PublicHall.model_validate(obj)
    out.images = [PublicImage.model_validate(i) for i in images]
    return ok(out, "Hall details fetched successfully")


@cached.get("/hall/packages", response_model=ApiResponse[list[PublicHallPackage]])
async def hall_packages(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(HallPackage).order_by(HallPackage.sort, HallPackage.created_at))).all()
    return listed(rows, "hall packages")


@router.get("/hall/availability", response_model=ApiResponse[list[Availability]])
async def hall_availability(
    response: Response, month: Month = Query(...), db: AsyncSession = Depends(get_db)
):
    ma = get_settings().availability_cache_max_age
    response.headers["Cache-Control"] = (
        f"public, max-age={ma}, s-maxage={ma}, stale-while-revalidate={ma * 4}"
    )
    rows = [Availability.model_validate(b) for b in await bookings_in_month(db, month)]
    if not rows:
        return ok([], "All dates are available this month")
    return ok(rows, "Hall availability fetched successfully")


# ---- Gallery -------------------------------------------------------------------------
@cached.get("/gallery/albums", response_model=ApiResponse[list[PublicAlbum]])
async def albums(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(GalleryAlbum)
        .where(GalleryAlbum.active.is_(True))
        .order_by(GalleryAlbum.sort, GalleryAlbum.title)
    )
    rows = (await db.scalars(stmt)).all()
    counts = await image_counts(db, [a.id for a in rows])
    out = []
    for a in rows:
        item = PublicAlbum.model_validate(a)
        item.image_count = counts.get(a.id, 0)
        out.append(item)
    return listed(out, "albums")


@cached.get("/gallery/albums/{slug}", response_model=ApiResponse[PublicAlbumDetail])
async def album(slug: str, db: AsyncSession = Depends(get_db)):
    stmt = select(GalleryAlbum).where(GalleryAlbum.slug == slug, GalleryAlbum.active.is_(True))
    obj = (await db.scalars(stmt)).first()
    if obj is None:
        raise not_found("Album")
    images = (
        await db.scalars(
            select(GalleryImage)
            .where(GalleryImage.album_id == obj.id)
            .order_by(GalleryImage.sort, GalleryImage.created_at)
        )
    ).all()
    out = PublicAlbumDetail.model_validate(obj)
    out.images = [PublicGalleryImage.model_validate(i) for i in images]
    out.image_count = len(images)
    return ok(out, "Album fetched successfully")


# ---- Content -------------------------------------------------------------------------
@cached.get("/testimonials", response_model=ApiResponse[list[PublicTestimonial]])
async def testimonials(
    business: str | None = Query(None, description="Business slug; shared testimonials are always included"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Testimonial).where(Testimonial.active.is_(True))
    if bid := await _business_id(db, business):
        stmt = stmt.where(or_(Testimonial.business_id == bid, Testimonial.business_id.is_(None)))
    rows = (await db.scalars(stmt.order_by(Testimonial.sort, Testimonial.created_at))).all()
    return listed(rows, "testimonials")


@cached.get("/faqs", response_model=ApiResponse[list[PublicFaq]])
async def faqs(
    business: str | None = Query(None, description="Business slug; general FAQs are always included"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Faq)
    if bid := await _business_id(db, business):
        stmt = stmt.where(or_(Faq.business_id == bid, Faq.business_id.is_(None)))
    return listed((await db.scalars(stmt.order_by(Faq.sort, Faq.created_at))).all(), "FAQs")


@cached.get("/seo/{page_key:path}", response_model=ApiResponse[PublicSeo])
async def seo(page_key: str, db: AsyncSession = Depends(get_db)):
    obj = (await db.scalars(select(SeoMeta).where(SeoMeta.page_key == page_key))).first()
    if obj is None:
        raise not_found("SEO entry")
    return ok(obj, "SEO details fetched successfully")


@cached.get("/sitemap-data", response_model=ApiResponse[SitemapData])
async def sitemap_data(db: AsyncSession = Depends(get_db)):
    async def entries(model, *where):
        stmt = select(model.slug, model.updated_at).where(*where).order_by(model.slug)
        return [SitemapEntry(slug=s, updated_at=u) for s, u in (await db.execute(stmt)).all()]

    data = SitemapData(
        rooms=await entries(Room, Room.active.is_(True)),
        menu_categories=await entries(MenuCategory, MenuCategory.active.is_(True)),
        albums=await entries(GalleryAlbum, GalleryAlbum.active.is_(True)),
    )
    return ok(data, "Sitemap data fetched successfully")


# ---- Enquiry form --------------------------------------------------------------------
ENQUIRY_SAVED = "Enquiry received. Continue on WhatsApp to chat with us."


@router.post(
    "/enquiries",
    response_model=ApiResponse[EnquiryCreated],
    status_code=201,
    dependencies=[Depends(limit_enquiries)],
    summary="Save an enquiry and get the pre-filled WhatsApp link",
)
async def enquiry(body: EnquiryIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    if body.website:
        return created(honeypot_response(), ENQUIRY_SAVED)
    await verify_turnstile(body.turnstile_token, client_ip(request))
    return created(await create_enquiry(db, body), ENQUIRY_SAVED)


router.include_router(cached)
