from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"  # development | staging | production
    api_prefix: str = "/api/v1"
    enable_docs: bool = True  # Swagger at /docs, ReDoc at /redoc

    # postgresql+asyncpg://postgres:<password>@db.<project>.supabase.co:5432/postgres
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    db_echo: bool = False

    supabase_url: str = "http://localhost:54321"
    # Project Settings > API Keys. New-style keys (sb_publishable_..., sb_secret_...) or the legacy anon /
    # service_role JWT keys both work. The secret key must never reach a frontend.
    supabase_anon_key: str = Field(
        "", validation_alias=AliasChoices("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY")
    )
    supabase_service_role_key: str = Field(
        "", validation_alias=AliasChoices("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY")
    )
    # Legacy HS256 JWT secret. Leave empty to verify tokens with the project's JWKS (asymmetric keys).
    supabase_jwt_secret: str = ""
    supabase_jwt_audience: str = "authenticated"
    # Where Supabase sends invite / reset links (the admin panel).
    admin_site_url: str = "http://localhost:3001"

    # Comma-separated list, e.g. "https://admin.sreebhavan.in,https://sreebhavan.in"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # Uploads
    upload_max_bytes: int = 5 * 1024 * 1024
    image_max_width: int = 1920
    thumb_width: int = 480
    webp_quality: int = 82

    # Public enquiry form
    enquiry_rate_limit: int = 5  # requests
    enquiry_rate_window_seconds: int = 600
    turnstile_secret_key: str = ""  # empty = honeypot only
    trust_proxy_headers: bool = True

    # Public cache headers (seconds)
    public_cache_max_age: int = 300
    public_cache_swr: int = 3600
    availability_cache_max_age: int = 30

    sentry_dsn: str = ""

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, v: str) -> str:
        # Accept the plain URL Supabase shows and switch it to the asyncpg driver.
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
