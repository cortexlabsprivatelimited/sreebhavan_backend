import uuid

from tests.conftest import API, data, make_token


async def test_login_returns_token_and_admin(client, seeded):
    r = await client.post(
        f"{API}/admin/auth/login", json={"email": "owner@example.com", "password": "secret"}
    )
    assert r.status_code == 200, r.text
    body = data(r)
    assert body["token_type"] == "bearer"
    assert body["admin"] == {
        "id": str(seeded["owner_id"]),
        "name": "Owner",
        "email": "owner@example.com",
        "role": "owner",
    }
    me = await client.get(
        f"{API}/admin/settings", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200


async def test_login_wrong_password_is_401_in_standard_error_shape(client, seeded):
    r = await client.post(f"{API}/admin/auth/login", json={"email": "owner@example.com", "password": "nope"})
    assert r.status_code == 401
    assert r.json() == {
        "success": False,
        "status_code": 401,
        "message": "Wrong email or password.",
        "errors": [],
    }


async def test_login_for_non_admin_supabase_user_is_401(client, seeded, supabase):
    supabase.add_user("random@example.com", "pw")
    r = await client.post(f"{API}/admin/auth/login", json={"email": "random@example.com", "password": "pw"})
    assert r.status_code == 401
    assert ("sign_out",) in supabase.calls


async def test_missing_bad_and_expired_tokens_are_401(client, seeded):
    assert (await client.get(f"{API}/admin/banners")).status_code == 401
    bad = {"Authorization": "Bearer not-a-jwt"}
    assert (await client.get(f"{API}/admin/banners", headers=bad)).status_code == 401
    expired = {"Authorization": f"Bearer {make_token(seeded['owner_id'], expires_in=-10)}"}
    r = await client.get(f"{API}/admin/banners", headers=expired)
    assert r.status_code == 401
    assert "expired" in r.json()["message"]
    unknown = {"Authorization": f"Bearer {make_token(uuid.uuid4())}"}
    assert (await client.get(f"{API}/admin/banners", headers=unknown)).status_code == 401


async def test_inactive_admin_is_401(client, seeded):
    r = await client.patch(
        f"{API}/admin/users/{seeded['staff_id']}",
        json={"name": "Staff", "email": "staff@example.com", "role": "staff", "active": False},
        headers=seeded["owner"],
    )
    assert r.status_code == 200, r.text
    assert (await client.get(f"{API}/admin/banners", headers=seeded["staff"])).status_code == 401


async def test_forgot_password_always_200(client, seeded, supabase):
    r1 = await client.post(f"{API}/admin/auth/forgot-password", json={"email": "owner@example.com"})
    r2 = await client.post(f"{API}/admin/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r1.status_code == r2.status_code == 200
    assert supabase.calls.count(("reset", "owner@example.com")) == 1
    assert not any(c == ("reset", "nobody@example.com") for c in supabase.calls)


async def test_logout(client, seeded, supabase):
    r = await client.post(f"{API}/admin/auth/logout", headers=seeded["owner"])
    assert r.status_code == 200
    assert ("sign_out",) in supabase.calls


async def test_users_owner_only(client, seeded):
    r = await client.get(f"{API}/admin/users", headers=seeded["staff"])
    assert r.status_code == 403
    assert r.json()["message"] == "Only the owner can do this."
    r = await client.get(f"{API}/admin/users", headers=seeded["owner"])
    assert r.status_code == 200
    assert {u["email"] for u in data(r)} == {"owner@example.com", "staff@example.com"}
    assert set(data(r)[0]) == {"id", "name", "email", "role", "active", "last_sign_in_at"}


async def test_invite_user_and_duplicate_email(client, seeded, supabase):
    body = {"name": "Front Desk", "email": "Desk@Example.com", "role": "staff", "active": True}
    r = await client.post(f"{API}/admin/users", json=body, headers=seeded["owner"])
    assert r.status_code == 201, r.text
    assert data(r)["email"] == "desk@example.com"
    assert ("invite", "desk@example.com") in supabase.calls
    r = await client.post(f"{API}/admin/users", json=body, headers=seeded["owner"])
    assert r.status_code == 409


async def test_owner_cannot_demote_deactivate_or_delete_self(client, seeded):
    me = seeded["owner_id"]
    base = {"name": "Owner", "email": "owner@example.com"}
    for change in ({"role": "staff", "active": True}, {"role": "owner", "active": False}):
        r = await client.patch(f"{API}/admin/users/{me}", json={**base, **change}, headers=seeded["owner"])
        assert r.status_code == 409
    r = await client.delete(f"{API}/admin/users/{me}", headers=seeded["owner"])
    assert r.status_code == 409


async def test_patch_user_ignores_email_and_delete_disables(client, seeded, supabase):
    staff = seeded["staff_id"]
    r = await client.patch(
        f"{API}/admin/users/{staff}",
        json={"name": "Desk", "email": "changed@example.com", "role": "staff", "active": True},
        headers=seeded["owner"],
    )
    assert data(r)["email"] == "staff@example.com"
    assert data(r)["name"] == "Desk"
    r = await client.delete(f"{API}/admin/users/{staff}", headers=seeded["owner"])
    assert r.status_code == 200
    assert ("disable", str(staff)) in supabase.calls
    r = await client.post(f"{API}/admin/users/{seeded['owner_id']}/reset-password", headers=seeded["owner"])
    assert r.status_code == 200


async def test_activity_log_written(client, seeded, session_factory):
    from sqlalchemy import select

    from app.models import ActivityLog

    await client.post(f"{API}/admin/faqs", json={"question": "Q?", "answer": "A."}, headers=seeded["staff"])
    async with session_factory() as s:
        logs = (await s.scalars(select(ActivityLog).where(ActivityLog.entity == "faqs"))).all()
    assert len(logs) == 1
    assert logs[0].action == "create"
    assert logs[0].user_id == seeded["staff_id"]
