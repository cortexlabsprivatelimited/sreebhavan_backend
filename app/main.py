import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import register_error_handlers
from app.core.responses import ApiResponse, ok
from app.core.supabase import close_supabase
from app.routers import admin, public

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.1)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_supabase()
    await engine.dispose()


app = FastAPI(
    title="Sreebhavan API",
    version="1.0.0",
    description="Backend for the Sreebhavan Veg Hotel and Sreebhavanam Event Hall & Rooms websites.",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # localhost on any port in development
    allow_origin_regex=None if settings.is_production else r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
register_error_handlers(app)

app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(public.router, prefix=settings.api_prefix)


@app.get("/health", tags=["Health"], response_model=ApiResponse[dict[str, str]])
async def health():
    return ok({"status": "ok"}, "Service is running")
