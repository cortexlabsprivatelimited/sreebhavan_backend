"""Thin async client for the Supabase Auth (GoTrue) and Storage REST APIs.

Only FastAPI talks to Supabase. The service-role key never leaves this process.
"""

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import AppError

log = logging.getLogger(__name__)

BAN_FOREVER = "876000h"  # ~100 years


class SupabaseError(AppError):
    def __init__(self, message: str = "The sign-in service is unavailable. Please try again."):
        super().__init__(502, "upstream_error", message)


class SupabaseClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base = settings.supabase_url.rstrip("/")
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(20.0))

    async def aclose(self) -> None:
        await self._http.aclose()

    # ---- headers -------------------------------------------------------------------
    @staticmethod
    def _headers(key: str, bearer: str | None = None) -> dict[str, str]:
        """New keys (sb_publishable_..., sb_secret_...) are not JWTs: send them only as `apikey` and let the
        gateway attach the role. Legacy anon/service_role keys are JWTs and also go in Authorization."""
        headers = {"apikey": key}
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        elif not key.startswith("sb_"):
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def _anon_headers(self, bearer: str | None = None) -> dict[str, str]:
        key = self.settings.supabase_anon_key or self.settings.supabase_service_role_key
        return self._headers(key, bearer)

    def _service_headers(self) -> dict[str, str]:
        if not self.settings.supabase_service_role_key:
            log.error("SUPABASE_SECRET_KEY is not set; admin invites, user management and uploads will fail")
        return self._headers(self.settings.supabase_service_role_key)

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            return await self._http.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            log.error("Supabase request failed: %s %s: %s", method, url, exc)
            raise SupabaseError() from exc

    # ---- auth ----------------------------------------------------------------------
    async def sign_in_with_password(self, email: str, password: str) -> dict[str, Any]:
        """Returns the GoTrue session ({access_token, user, ...}) or raises 401."""
        r = await self._request(
            "POST",
            f"{self.base}/auth/v1/token",
            params={"grant_type": "password"},
            json={"email": email, "password": password},
            headers=self._anon_headers(),
        )
        if r.status_code in (400, 401, 403, 422):
            raise AppError(401, "invalid_credentials", "Wrong email or password.")
        if r.status_code >= 300:
            log.error("Supabase sign-in error %s: %s", r.status_code, r.text)
            raise SupabaseError()
        return r.json()

    async def sign_out(self, access_token: str) -> None:
        r = await self._request(
            "POST", f"{self.base}/auth/v1/logout", headers=self._anon_headers(bearer=access_token)
        )
        if r.status_code >= 300 and r.status_code not in (401, 403, 404):
            log.warning("Supabase sign-out error %s: %s", r.status_code, r.text)

    async def send_password_reset(self, email: str) -> None:
        r = await self._request(
            "POST",
            f"{self.base}/auth/v1/recover",
            params={"redirect_to": f"{self.settings.admin_site_url.rstrip('/')}/reset-password"},
            json={"email": email},
            headers=self._anon_headers(),
        )
        if r.status_code >= 300:
            log.error("Supabase recover error %s: %s", r.status_code, r.text)
            raise SupabaseError("Could not send the reset email. Please try again.")

    async def invite_user(self, email: str, name: str) -> str:
        """Invites a user by email and returns the new auth user id."""
        r = await self._request(
            "POST",
            f"{self.base}/auth/v1/invite",
            params={"redirect_to": f"{self.settings.admin_site_url.rstrip('/')}/set-password"},
            json={"email": email, "data": {"name": name}},
            headers=self._service_headers(),
        )
        if r.status_code >= 400 and (r.status_code == 422 or "already" in r.text.lower()):
            existing = await self.find_user_by_email(email)
            if existing:
                return existing["id"]
        if r.status_code >= 300:
            log.error("Supabase invite error %s: %s", r.status_code, r.text)
            raise SupabaseError("Could not send the invite email. Please try again.")
        return r.json()["id"]

    async def create_user(self, email: str, password: str, name: str) -> str:
        """Creates a confirmed user with a password (used by the create-owner CLI)."""
        r = await self._request(
            "POST",
            f"{self.base}/auth/v1/admin/users",
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"name": name},
            },
            headers=self._service_headers(),
        )
        if r.status_code >= 300:
            existing = await self.find_user_by_email(email)
            if existing:
                await self.update_user(existing["id"], {"password": password, "ban_duration": "none"})
                return existing["id"]
            raise SupabaseError(f"Could not create the user: {r.text}")
        return r.json()["id"]

    async def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        page = 1
        while True:
            r = await self._request(
                "GET",
                f"{self.base}/auth/v1/admin/users",
                params={"page": page, "per_page": 200},
                headers=self._service_headers(),
            )
            if r.status_code >= 300:
                return None
            users = r.json().get("users", [])
            for u in users:
                if (u.get("email") or "").lower() == email.lower():
                    return u
            if len(users) < 200:
                return None
            page += 1

    async def update_user(self, user_id: str, attrs: dict[str, Any]) -> None:
        r = await self._request(
            "PUT", f"{self.base}/auth/v1/admin/users/{user_id}", json=attrs, headers=self._service_headers()
        )
        if r.status_code >= 300 and r.status_code != 404:
            log.error("Supabase update user error %s: %s", r.status_code, r.text)
            raise SupabaseError()

    async def disable_user(self, user_id: str) -> None:
        await self.update_user(user_id, {"ban_duration": BAN_FOREVER})

    async def enable_user(self, user_id: str) -> None:
        await self.update_user(user_id, {"ban_duration": "none"})

    # ---- storage -------------------------------------------------------------------
    def public_url(self, bucket: str, path: str) -> str:
        return f"{self.base}/storage/v1/object/public/{bucket}/{path}"

    def _storage_write_headers(self, user_token: str | None) -> dict[str, str]:
        """Storage writes use the secret key when it is set. Without it, they go in as the signed-in admin
        (publishable key + the admin's access token), and Storage policies on storage.objects that check
        public.is_active_admin() allow active admins to write to the site buckets."""
        if self.settings.supabase_service_role_key or not user_token:
            return self._service_headers()
        return self._anon_headers(user_token)

    async def upload(
        self, bucket: str, path: str, content: bytes, content_type: str, user_token: str | None = None
    ) -> str:
        r = await self._request(
            "POST",
            f"{self.base}/storage/v1/object/{bucket}/{path}",
            content=content,
            headers={
                **self._storage_write_headers(user_token),
                "Content-Type": content_type,
                "Cache-Control": "max-age=31536000",
                "x-upsert": "true",
            },
        )
        if r.status_code >= 300:
            log.error("Supabase storage upload error %s: %s", r.status_code, r.text)
            raise SupabaseError("Could not store the file. Please try again.")
        return self.public_url(bucket, path)

    async def list_objects(
        self, bucket: str, prefix: str = "", limit: int = 1000, offset: int = 0
    ) -> list[dict]:
        r = await self._request(
            "POST",
            f"{self.base}/storage/v1/object/list/{bucket}",
            json={"prefix": prefix, "limit": limit, "offset": offset},
            headers=self._service_headers(),
        )
        if r.status_code >= 300:
            log.error("Supabase storage list error %s: %s", r.status_code, r.text)
            return []
        return r.json()

    async def delete_objects(self, bucket: str, paths: list[str]) -> None:
        if not paths:
            return
        r = await self._request(
            "DELETE",
            f"{self.base}/storage/v1/object/{bucket}",
            json={"prefixes": paths},
            headers=self._service_headers(),
        )
        if r.status_code >= 300:
            log.error("Supabase storage delete error %s: %s", r.status_code, r.text)

    async def create_bucket(self, bucket: str) -> None:
        r = await self._request(
            "POST",
            f"{self.base}/storage/v1/bucket",
            json={"id": bucket, "name": bucket, "public": True},
            headers=self._service_headers(),
        )
        if r.status_code >= 300 and "already exists" not in r.text.lower():
            raise SupabaseError(f"Could not create bucket {bucket}: {r.text}")


_client: SupabaseClient | None = None


def get_supabase() -> SupabaseClient:
    global _client
    if _client is None:
        _client = SupabaseClient(get_settings())
    return _client


async def close_supabase() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
