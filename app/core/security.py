"""Verifies Supabase access tokens and loads the admin from admin_users."""

import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import AdminUser

bearer_scheme = HTTPBearer(auto_error=False, description="Supabase access token from /admin/auth/login")


def _unauthorized(message: str = "Please sign in again.") -> AppError:
    return AppError(401, "unauthorized", message)


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    base = get_settings().supabase_url.rstrip("/")
    return jwt.PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json", cache_keys=True, lifespan=3600)


async def decode_access_token(token: str) -> dict:
    settings = get_settings()
    options = {"require": ["sub", "exp"]}
    try:
        if settings.supabase_jwt_secret:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=settings.supabase_jwt_audience,
                options=options,
            )
        signing_key = await run_in_threadpool(_jwks_client().get_signing_key_from_jwt, token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.supabase_jwt_audience,
            options=options,
        )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Your session has expired. Please sign in again.") from exc
    except (jwt.PyJWTError, ValueError) as exc:
        raise _unauthorized() from exc


@dataclass
class AdminContext:
    admin: AdminUser
    token: str

    @property
    def id(self) -> uuid.UUID:
        return self.admin.id

    @property
    def is_owner(self) -> bool:
        return self.admin.role == "owner"


async def get_current_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminContext:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise _unauthorized()
    claims = await decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise _unauthorized() from exc
    admin = await db.get(AdminUser, user_id)
    if admin is None or not admin.active:
        raise _unauthorized("Your account does not have admin access.")
    ctx = AdminContext(admin=admin, token=credentials.credentials)
    request.state.admin = ctx
    return ctx


async def require_owner(ctx: AdminContext = Depends(get_current_admin)) -> AdminContext:
    if not ctx.is_owner:
        raise AppError(403, "forbidden", "Only the owner can do this.")
    return ctx
