from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import conflict
from app.models import MenuCard, MenuCategory, MenuItem
from app.schemas.admin import (
    MenuCardIn,
    MenuCardOut,
    MenuCategoryIn,
    MenuCategoryOut,
    MenuItemIn,
    MenuItemOut,
)
from app.services.crud import crud_router, fk_check

router = APIRouter(prefix="/menu")


async def _category_must_be_empty(db: AsyncSession, category: MenuCategory) -> None:
    n = await db.scalar(select(func.count()).select_from(MenuItem).where(MenuItem.category_id == category.id))
    if n:
        noun = "item" if n == 1 else "items"
        raise conflict(
            "category_not_empty",
            f"'{category.name}' still has {n} food {noun}. Move or delete them before deleting the category.",
        )


categories = crud_router(
    prefix="/categories",
    tag="Admin: menu",
    model=MenuCategory,
    schema_in=MenuCategoryIn,
    schema_out=MenuCategoryOut,
    entity="menu_categories",
    label="Menu category",
    plural="menu categories",
    unique=("slug",),
    order_by=(MenuCategory.sort, MenuCategory.name),
    before_delete=_category_must_be_empty,
)

items = crud_router(
    prefix="/items",
    tag="Admin: menu",
    model=MenuItem,
    schema_in=MenuItemIn,
    schema_out=MenuItemOut,
    entity="menu_items",
    label="Food item",
    unique=("slug",),
    order_by=(MenuItem.sort, MenuItem.name),
    before_save=fk_check(("category_id", MenuCategory, "Menu category")),
)

cards = crud_router(
    prefix="/cards",
    tag="Admin: menu",
    model=MenuCard,
    schema_in=MenuCardIn,
    schema_out=MenuCardOut,
    entity="menu_cards",
    label="Menu card",
    order_by=(MenuCard.created_at,),
)

router.include_router(categories)
router.include_router(items)
router.include_router(cards)
