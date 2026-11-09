"""Shared CRUD helpers and a router factory for the simple admin resources."""

import uuid
from collections.abc import Awaitable, Callable, Sequence
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError, create_model
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import conflict, not_found, unprocessable
from app.core.responses import ApiResponse, DeletedOut, created, deleted, listed, ok
from app.core.security import AdminContext, get_current_admin
from app.models import ActivityLog, Base
from app.schemas.common import InSchema

SaveHook = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]


async def log_activity(
    db: AsyncSession, ctx: AdminContext | None, action: str, entity: str, entity_id: Any = None
) -> None:
    db.add(
        ActivityLog(
            user_id=ctx.id if ctx else None,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
        )
    )


async def ensure_exists(db: AsyncSession, model: type[Base], obj_id: Any, field: str, label: str) -> None:
    """422 when a foreign key points at nothing (instead of a database error)."""
    if obj_id is not None and await db.get(model, obj_id) is None:
        raise unprocessable(f"invalid_{field}", f"{label} not found. Pick one from the list.", field)


def fk_check(*checks: tuple[str, type[Base], str]) -> SaveHook:
    """before_save hook: fk_check(("category_id", MenuCategory, "Menu category"), ...)."""

    async def hook(db: AsyncSession, data: dict[str, Any]) -> None:
        for field, model, label in checks:
            await ensure_exists(db, model, data.get(field), field, label)

    return hook


async def get_or_404(db: AsyncSession, model: type[Base], obj_id: Any, label: str):
    obj = await db.get(model, obj_id)
    if obj is None:
        raise not_found(label)
    return obj


async def ensure_unique(
    db: AsyncSession,
    model: type[Base],
    field: str,
    value: Any,
    exclude_id: uuid.UUID | None,
    label: str,
) -> None:
    if value is None:
        return
    col = getattr(model, field)
    stmt = select(func.count()).select_from(model).where(col == value)
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)
    if (await db.scalar(stmt)) > 0:
        nice = field.replace("_", " ")
        raise conflict(
            f"duplicate_{field}", f"Another {label.lower()} already uses the {nice} '{value}'.", field
        )


@lru_cache
def make_partial(schema: type[InSchema]) -> type[InSchema]:
    """Same fields as `schema`, all optional. Only the keys actually sent are applied."""
    fields = {name: (f.annotation | None, None) for name, f in schema.model_fields.items()}
    return create_model(f"{schema.__name__}Patch", __base__=InSchema, **fields)


def merge_and_validate(obj: Base, schema: type[InSchema], patch: dict[str, Any]) -> dict[str, Any]:
    """Merge a (possibly partial) patch onto the stored record and validate the result in full."""
    current = {name: getattr(obj, name) for name in schema.model_fields}
    current.update(patch)
    try:
        return schema.model_validate(current).model_dump()
    except ValidationError as exc:
        errors = [{**e, "loc": ("body", *e["loc"])} for e in exc.errors(include_url=False)]
        raise RequestValidationError(errors) from exc


async def create_record(
    db: AsyncSession,
    model: type[Base],
    data: dict[str, Any],
    ctx: AdminContext | None,
    entity: str,
    label: str,
    unique: Sequence[str] = (),
    before_save: "SaveHook | None" = None,
    **extra: Any,
):
    if before_save:
        await before_save(db, data)
    for field in unique:
        await ensure_unique(db, model, field, data.get(field), None, label)
    obj = model(**data, **extra)
    db.add(obj)
    await db.flush()
    await log_activity(db, ctx, "create", entity, getattr(obj, "id", None))
    return obj


async def update_record(
    db: AsyncSession,
    obj: Base,
    schema: type[InSchema],
    patch: dict[str, Any],
    ctx: AdminContext | None,
    entity: str,
    label: str,
    unique: Sequence[str] = (),
    before_save: "SaveHook | None" = None,
):
    data = merge_and_validate(obj, schema, patch)
    if before_save:
        await before_save(db, data)
    for field in unique:
        await ensure_unique(db, type(obj), field, data.get(field), obj.id, label)
    for k, v in data.items():
        setattr(obj, k, v)
    await db.flush()
    await log_activity(db, ctx, "update", entity, obj.id)
    return obj


async def delete_record(db: AsyncSession, obj: Base, ctx: AdminContext | None, entity: str) -> None:
    obj_id = getattr(obj, "id", None)
    await db.delete(obj)
    await db.flush()
    await log_activity(db, ctx, "delete", entity, obj_id)


def crud_router(
    *,
    prefix: str,
    tag: str,
    model: type[Base],
    schema_in: type[InSchema],
    schema_out: type[BaseModel],
    entity: str,
    label: str,
    plural: str | None = None,
    unique: Sequence[str] = (),
    order_by: Sequence[Any] = (),
    before_delete: Callable[[AsyncSession, Any], Awaitable[None]] | None = None,
    before_save: SaveHook | None = None,
) -> APIRouter:
    """GET list, POST, PATCH /{id} (full or partial), DELETE /{id}, all in the standard envelope."""
    router = APIRouter(prefix=prefix, tags=[tag])
    patch_schema = make_partial(schema_in)
    order = list(order_by) or [model.created_at]
    plural = plural or f"{label.lower()}s"

    @router.get("", response_model=ApiResponse[list[schema_out]], summary=f"List {plural}")
    async def list_records(db: AsyncSession = Depends(get_db), _: AdminContext = Depends(get_current_admin)):
        return listed((await db.scalars(select(model).order_by(*order))).all(), plural)

    @router.post(
        "", response_model=ApiResponse[schema_out], status_code=201, summary=f"Create {label.lower()}"
    )
    async def create(
        body: schema_in,  # type: ignore[valid-type]
        db: AsyncSession = Depends(get_db),
        ctx: AdminContext = Depends(get_current_admin),
    ):
        obj = await create_record(db, model, body.model_dump(), ctx, entity, label, unique, before_save)
        return created(obj, f"{label} created successfully")

    @router.patch("/{obj_id}", response_model=ApiResponse[schema_out], summary=f"Update {label.lower()}")
    async def update(
        obj_id: uuid.UUID,
        body: patch_schema,  # type: ignore[valid-type]
        db: AsyncSession = Depends(get_db),
        ctx: AdminContext = Depends(get_current_admin),
    ):
        obj = await get_or_404(db, model, obj_id, label)
        obj = await update_record(
            db, obj, schema_in, body.model_dump(exclude_unset=True), ctx, entity, label, unique, before_save
        )
        return ok(obj, f"{label} updated successfully")

    @router.delete("/{obj_id}", response_model=ApiResponse[DeletedOut], summary=f"Delete {label.lower()}")
    async def delete(
        obj_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        ctx: AdminContext = Depends(get_current_admin),
    ):
        obj = await get_or_404(db, model, obj_id, label)
        if before_delete:
            await before_delete(db, obj)
        await delete_record(db, obj, ctx, entity)
        return deleted(obj_id, label)

    return router
