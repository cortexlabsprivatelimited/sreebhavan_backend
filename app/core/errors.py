"""Every error uses the standard envelope:

{"success": false, "status_code": 409, "message": "...", "errors": [{"field": "slug", "message": "..."}]}
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)


class AppError(Exception):
    """A handled error. `code` is for logs only; `field` puts the message in `errors[]` under that field."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        field: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.status = status
        self.code = code
        self.message = message
        self.field = field
        self.headers = headers
        super().__init__(message)


def not_found(entity: str = "Record") -> AppError:
    return AppError(404, "not_found", f"{entity} not found.")


def conflict(code: str, message: str, field: str | None = None) -> AppError:
    return AppError(409, code, message, field)


def unprocessable(code: str, message: str, field: str | None = None) -> AppError:
    return AppError(422, code, message, field)


def error_body(status: int, message: str, errors: list[dict] | None = None) -> dict:
    return {"success": False, "status_code": status, "message": message, "errors": errors or []}


def error_response(status: int, message: str, errors: list[dict] | None = None, headers=None) -> JSONResponse:
    return JSONResponse(error_body(status, message, errors), status_code=status, headers=headers)


_HTTP_MESSAGES = {
    400: "The request could not be processed.",
    401: "Session expired. Please log in again.",
    403: "You do not have permission to do this.",
    404: "The requested resource was not found.",
    405: "This method is not allowed here.",
    413: "The request is too large.",
    415: "This content type is not supported.",
    429: "Too many requests. Please try again later.",
}

# Pydantic messages start with a generic noun ("Input should be ..."); swap in the field's label.
_GENERIC_NOUNS = ("Input ", "String ", "Value ", "List ", "Dictionary ", "Decimal ", "Integer ")


def _label(loc: tuple) -> str:
    names = [str(p) for p in loc if not isinstance(p, int) and p not in ("body", "query", "path", "header")]
    if not names:
        return "This field"
    name = names[-1].replace("_", " ")
    return name[:1].upper() + name[1:]


def _field(loc: tuple) -> str | None:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header")]
    return ".".join(parts) or None


def _friendly(err: dict) -> str:
    kind = err.get("type", "")
    msg = err.get("msg", "Invalid value.")
    label = _label(tuple(err.get("loc", ())))
    if kind == "missing":
        return f"{label} is required."
    if kind in ("string_too_short", "too_short") and (err.get("ctx") or {}).get("min_length") == 1:
        if isinstance(err.get("input"), list):
            return f"{label}: add at least one."
        return f"{label} is required."
    if kind == "value_error":
        return msg.removeprefix("Value error, ")
    if kind == "uuid_parsing":
        return f"{label} is not a valid ID."
    if kind == "json_invalid":
        return "The request body is not valid JSON."
    for noun in _GENERIC_NOUNS:
        if msg.startswith(noun):
            msg = f"{label} {msg[len(noun) :]}"
            break
    else:
        msg = f"{label}: {msg[:1].lower()}{msg[1:]}"
    return msg if msg.endswith(".") else msg + "."


def validation_errors(raw: list[dict]) -> list[dict]:
    return [{"field": _field(tuple(e.get("loc", ()))), "message": _friendly(e)} for e in raw]


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        errors = [{"field": exc.field, "message": exc.message}] if exc.field else []
        return error_response(exc.status, exc.message, errors, exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        default = _HTTP_MESSAGES.get(exc.status_code, "Request failed.")
        detail = exc.detail if isinstance(exc.detail, str) else None
        # Starlette's defaults ("Not Found", ...) are replaced with readable sentences.
        message = detail if detail and detail.endswith(".") else default
        return error_response(exc.status_code, message, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        errors = validation_errors(list(exc.errors()))
        message = errors[0]["message"] if len(errors) == 1 else "Validation failed"
        return error_response(422, message, errors)

    @app.exception_handler(IntegrityError)
    async def _integrity_error(_: Request, exc: IntegrityError):
        log.warning("Integrity error: %s", exc.orig)
        return error_response(409, "This change conflicts with an existing record.")

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error", exc_info=exc)
        return error_response(500, "Something went wrong. Please try again.")
