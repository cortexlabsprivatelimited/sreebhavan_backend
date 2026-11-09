import os

# Configure before the app is imported.
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite+aiosqlite://",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "anon",
        "SUPABASE_SERVICE_ROLE_KEY": "service",
        "SUPABASE_JWT_SECRET": "test-secret-test-secret-test-secret-123",
        "ENQUIRY_RATE_LIMIT": "100",
        "TURNSTILE_SECRET_KEY": "",
    }
)

import uuid  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402

import httpx  # noqa: E402
import jwt  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool, StaticPool  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.core.ratelimit import enquiry_limiter  # noqa: E402
from app.core.supabase import get_supabase  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AdminUser, Base, Business  # noqa: E402

SECRET = os.environ["SUPABASE_JWT_SECRET"]
API = "/api/v1"


class FakeSupabase:
    def __init__(self):
        self.users: dict[str, dict] = {}  # email -> {id, password}
        self.uploads: dict[str, tuple[bytes, str]] = {}
        self.calls: list[tuple] = []
        self.base = "https://test.supabase.co"

    def add_user(self, email: str, password: str, user_id: uuid.UUID | None = None) -> uuid.UUID:
        uid = user_id or uuid.uuid4()
        self.users[email] = {"id": str(uid), "password": password}
        return uid

    async def sign_in_with_password(self, email, password):
        u = self.users.get(email)
        if not u or u["password"] != password:
            raise AppError(401, "invalid_credentials", "Wrong email or password.")
        return {"access_token": make_token(uuid.UUID(u["id"])), "user": {"id": u["id"]}}

    async def sign_out(self, token):
        self.calls.append(("sign_out",))

    async def send_password_reset(self, email):
        self.calls.append(("reset", email))

    async def invite_user(self, email, name):
        self.calls.append(("invite", email))
        if email in self.users:
            return self.users[email]["id"]
        return str(self.add_user(email, "x"))

    async def disable_user(self, user_id):
        self.calls.append(("disable", user_id))

    async def enable_user(self, user_id):
        self.calls.append(("enable", user_id))

    def public_url(self, bucket, path):
        return f"{self.base}/storage/v1/object/public/{bucket}/{path}"

    async def upload(self, bucket, path, content, content_type, user_token=None):
        self.uploads[f"{bucket}/{path}"] = (content, content_type)
        return self.public_url(bucket, path)


def make_token(user_id: uuid.UUID, expires_in: int = 3600) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": str(user_id), "aud": "authenticated", "exp": now + timedelta(seconds=expires_in), "iat": now},
        SECRET,
        algorithm="HS256",
    )


def check_envelope(response: httpx.Response) -> None:
    """Every JSON response must follow the standard format (runs on every test request)."""
    if not response.headers.get("content-type", "").startswith("application/json"):
        return
    body = response.json()
    path = response.request.url.path
    assert isinstance(body, dict), path
    assert body["status_code"] == response.status_code, f"{path}: body status != HTTP status"
    assert isinstance(body["message"], str) and body["message"], path
    if response.status_code < 400:
        assert body["success"] is True, path
        assert "data" in body and "errors" not in body, path
        if "meta" in body:
            assert isinstance(body["data"], list), path
            assert set(body["meta"]) == {"current_page", "per_page", "total_records", "total_pages"}, path
    else:
        assert body["success"] is False, path
        assert "data" not in body, path
        assert isinstance(body["errors"], list), path
        for e in body["errors"]:
            assert set(e) == {"field", "message"}, path


def data(response: httpx.Response):
    """The `data` of a successful response."""
    body = response.json()
    assert body["success"] is True, body
    return body["data"]


def error_fields(response: httpx.Response) -> dict[str | None, str]:
    """{field: message} from an error response."""
    body = response.json()
    assert body["success"] is False, body
    return {e["field"]: e["message"] for e in body["errors"]}


# Set TEST_DATABASE_URL (postgresql+asyncpg://...) to run the suite against PostgreSQL instead of SQLite.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")


@pytest.fixture
async def engine():
    if TEST_DATABASE_URL:
        eng = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    else:
        eng = create_async_engine(
            "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
        )
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
def supabase():
    return FakeSupabase()


@pytest.fixture
async def client(session_factory, supabase):
    async def _get_db():
        async with session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_supabase] = lambda: supabase
    enquiry_limiter.reset()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        event_hooks={"response": [_async_check]},
    ) as c:
        yield c
    app.dependency_overrides.clear()


async def _async_check(response: httpx.Response) -> None:
    await response.aread()
    check_envelope(response)


@pytest.fixture
async def seeded(session_factory, supabase):
    """Two businesses, an owner and a staff admin. Returns ids and auth headers."""
    owner_id = supabase.add_user("owner@example.com", "secret")
    staff_id = supabase.add_user("staff@example.com", "secret")
    async with session_factory() as s:
        hotel = Business(
            slug="sreebhavan-veg-hotel", name="Sreebhavan Veg Hotel", whatsapp="9847000001", timings=[]
        )
        stays = Business(slug="sreebhavanam", name="Sreebhavanam", whatsapp="9847000002", timings=[])
        s.add_all(
            [
                hotel,
                stays,
                AdminUser(id=owner_id, name="Owner", email="owner@example.com", role="owner", active=True),
                AdminUser(id=staff_id, name="Staff", email="staff@example.com", role="staff", active=True),
            ]
        )
        await s.commit()
    return {
        "owner_id": owner_id,
        "staff_id": staff_id,
        "hotel_id": hotel.id,
        "stays_id": stays.id,
        "owner": {"Authorization": f"Bearer {make_token(owner_id)}"},
        "staff": {"Authorization": f"Bearer {make_token(staff_id)}"},
    }
