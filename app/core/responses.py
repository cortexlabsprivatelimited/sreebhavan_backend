"""Standard response envelope used by every JSON endpoint.

Success:   {"success": true,  "status_code": 200, "message": "...", "data": {...} | [...]}
Paginated: {"success": true,  "status_code": 200, "message": "...", "data": [...], "meta": {...}}
Error:     {"success": false, "status_code": 422, "message": "...", "errors": [{"field", "message"}]}

`status_code` in the body always equals the HTTP status. Lists are always arrays, never null.
"""

import math
import uuid
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: Literal[True] = True
    status_code: int = 200
    message: str
    data: T


class PageMeta(BaseModel):
    current_page: int
    per_page: int
    total_records: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    success: Literal[True] = True
    status_code: int = 200
    message: str
    data: list[T] = Field(default_factory=list)
    meta: PageMeta


class ErrorItem(BaseModel):
    field: str | None = Field(
        None, description="Request field the error belongs to; null for form-level errors"
    )
    message: str


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    status_code: int
    message: str
    errors: list[ErrorItem] = Field(default_factory=list)


class DeletedOut(BaseModel):
    id: uuid.UUID | str


# ---- helpers used by the routers -----------------------------------------------------
def ok(data: Any, message: str, status_code: int = 200) -> dict[str, Any]:
    return {"success": True, "status_code": status_code, "message": message, "data": data}


def created(data: Any, message: str) -> dict[str, Any]:
    return ok(data, message, 201)


def listed(items: Any, plural: str) -> dict[str, Any]:
    """`plural` is lower-case, e.g. "banners" -> "Banners fetched successfully" / "No banners found"."""
    items = list(items)
    if not items:
        return ok([], f"No {plural} found")
    return ok(items, f"{plural[:1].upper()}{plural[1:]} fetched successfully")


def deleted(obj_id: Any, label: str) -> dict[str, Any]:
    return ok({"id": obj_id}, f"{label} deleted successfully")


def paginated(items: Any, *, page: int, per_page: int, total: int, plural: str) -> dict[str, Any]:
    items = list(items)
    meta = {
        "current_page": page,
        "per_page": per_page,
        "total_records": total,
        "total_pages": math.ceil(total / per_page) if per_page else 0,
    }
    if total == 0:
        message = f"No {plural} found"
    else:
        message = f"{plural[:1].upper()}{plural[1:]} fetched successfully"
    return {"success": True, "status_code": 200, "message": message, "data": items, "meta": meta}


# Documented on every router so Swagger shows the error envelope instead of FastAPI's default.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorResponse, "description": desc}
    for code, desc in {
        401: "Missing, invalid or expired token",
        403: "Not allowed for this role",
        404: "Not found",
        409: "Conflict",
        422: "Validation failed",
        429: "Rate limited",
    }.items()
}
