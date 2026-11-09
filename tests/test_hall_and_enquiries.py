from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from app.core.ratelimit import enquiry_limiter
from tests.conftest import API, TEST_DATABASE_URL, data, error_fields

FUTURE = date.today() + timedelta(days=40)
MONTH = FUTURE.strftime("%Y-%m")


def booking(slot: str, day: date = FUTURE, status: str = "booked", **extra):
    return {"date": day.isoformat(), "slot": slot, "status": status, "customer_name": "Arun",
            "phone": "9847012345", "event_type": "Wedding", "notes": None, **extra}  # fmt: skip


async def test_hall_404_until_saved_then_put(client, seeded):
    h = seeded["owner"]
    assert (await client.get(f"{API}/admin/hall", headers=h)).status_code == 404
    assert (await client.get(f"{API}/public/hall")).status_code == 404
    body = {"name": "Sreebhavanam Hall", "capacity_seating": 600, "capacity_floating": 900,
            "facilities": ["AC", "Stage"], "rules": "No outside catering."}  # fmt: skip
    r = await client.put(f"{API}/admin/hall", json=body, headers=h)
    assert r.status_code == 200 and data(r) == body
    r = await client.put(f"{API}/admin/hall", json={**body, "capacity_seating": 650}, headers=h)
    assert data(await client.get(f"{API}/admin/hall", headers=h))["capacity_seating"] == 650
    await client.post(
        f"{API}/admin/hall/images", json={"url": "https://x/h.webp", "alt": "Stage", "sort": 0}, headers=h
    )
    pub = data(await client.get(f"{API}/public/hall"))
    assert pub["capacity_seating"] == 650 and pub["images"][0]["alt"] == "Stage"


async def test_hall_packages(client, seeded):
    h = seeded["owner"]
    p = {"name": "Wedding – full day", "price": 85000, "inclusions": ["Hall for 12 hours"], "sort": 1}
    r = await client.post(f"{API}/admin/hall/packages", json=p, headers=h)
    assert r.status_code == 201
    r = await client.patch(
        f"{API}/admin/hall/packages/{data(r)['id']}", json={**p, "price": 90000}, headers=h
    )
    assert data(r)["price"] == 90000
    assert data(await client.get(f"{API}/public/hall/packages"))[0]["price"] == 90000


async def test_double_booking_rules(client, seeded):
    h = seeded["staff"]
    url = f"{API}/admin/hall/bookings"
    r = await client.post(url, json=booking("morning"), headers=h)
    assert r.status_code == 201, r.text
    morning_id = data(r)["id"]
    # same slot
    r = await client.post(url, json=booking("morning", status="tentative"), headers=h)
    assert r.status_code == 409 and "already booked" in error_fields(r)["slot"]
    # morning blocks full
    r = await client.post(url, json=booking("full"), headers=h)
    assert r.status_code == 409
    # morning + evening can coexist
    r = await client.post(url, json=booking("evening", status="tentative"), headers=h)
    assert r.status_code == 201
    evening_id = data(r)["id"]
    # full blocks morning/evening on another day
    other = FUTURE + timedelta(days=1)
    assert (await client.post(url, json=booking("full", day=other), headers=h)).status_code == 201
    assert (await client.post(url, json=booking("evening", day=other), headers=h)).status_code == 409

    # PATCH ignores the booking being edited
    r = await client.patch(
        f"{url}/{morning_id}", json=booking("morning", status="tentative", notes="Advance due"), headers=h
    )
    assert r.status_code == 200 and data(r)["notes"] == "Advance due"
    # ...but still checks the others
    r = await client.patch(f"{url}/{morning_id}", json=booking("full"), headers=h)
    assert r.status_code == 409
    # free the evening, then morning -> full works
    assert (await client.delete(f"{url}/{evening_id}", headers=h)).status_code == 200
    r = await client.patch(f"{url}/{morning_id}", json=booking("full"), headers=h)
    assert r.status_code == 200 and data(r)["slot"] == "full"

    listed = data(await client.get(url, params={"month": MONTH}, headers=h))
    assert {b["slot"] for b in listed if b["date"] == FUTURE.isoformat()} == {"full"}
    assert (await client.get(url, params={"month": "2026-13"}, headers=h)).status_code == 422


async def test_public_availability_hides_customer_details(client, seeded):
    await client.post(f"{API}/admin/hall/bookings", json=booking("evening"), headers=seeded["owner"])
    r = await client.get(f"{API}/public/hall/availability", params={"month": MONTH})
    assert r.status_code == 200
    assert data(r) == [{"date": FUTURE.isoformat(), "slot": "evening", "status": "booked"}]
    assert "max-age=30" in r.headers["cache-control"]


def hall_enquiry(**extra):
    return {"type": "hall", "name": "Arun", "phone": "98470 12345", "date_from": FUTURE.isoformat(),
            "slot": "evening", "guests": 400, "event_type": "Wedding", **extra}  # fmt: skip


async def test_public_hall_enquiry_saves_and_returns_whatsapp(client, seeded):
    r = await client.post(f"{API}/public/enquiries", json=hall_enquiry())
    assert r.status_code == 201, r.text
    url = urlparse(data(r)["whatsapp_url"])
    assert url.netloc == "wa.me" and url.path == "/919847000002"
    text = parse_qs(url.query)["text"][0]
    assert text == (
        f"Hi Sreebhavanam, I'd like to enquire about the Event Hall on {FUTURE:%d-%b-%Y} (Evening) "
        "for a Wedding, about 400 guests. Name: Arun, Phone: 9847012345."
    )
    listed = (await client.get(f"{API}/admin/enquiries", headers=seeded["staff"])).json()
    assert listed["meta"]["total_records"] == 1 and listed["data"][0]["status"] == "new"
    assert listed["data"][0]["phone"] == "9847012345"


async def test_enquiry_validation(client, seeded):
    post = lambda body: client.post(f"{API}/public/enquiries", json=body)  # noqa: E731
    assert (await post(hall_enquiry(slot=None))).status_code == 422
    assert (
        await post(hall_enquiry(date_from=(date.today() - timedelta(days=1)).isoformat()))
    ).status_code == 422
    assert (await post({"type": "room", "name": "A", "phone": "9847012345"})).status_code == 422
    r = await post({"type": "room", "name": "A", "phone": "9847012345", "room_slug": "nope"})
    assert r.status_code == 422 and "room_id" in error_fields(r)


async def test_room_and_hotel_enquiries(client, seeded):
    h = seeded["owner"]
    await client.post(
        f"{API}/admin/rooms",
        json={"slug": "deluxe-ac-room", "name": "Deluxe AC Room", "price": 2200, "capacity": 2},
        headers=h,
    )
    r = await client.post(
        f"{API}/public/enquiries",
        json={
            "type": "room",
            "name": "Meera",
            "phone": "9847011111",
            "room_slug": "deluxe-ac-room",
            "date_from": FUTURE.isoformat(),
            "date_to": (FUTURE + timedelta(days=2)).isoformat(),
            "guests": 2,
        },
    )
    assert r.status_code == 201, r.text
    assert "Deluxe%20AC%20Room" in data(r)["whatsapp_url"]
    r = await client.post(
        f"{API}/public/enquiries",
        json={"type": "hotel", "name": "Ravi", "phone": "9847022222", "message": "Party order for 50"},
    )
    assert data(r)["whatsapp_url"].startswith("https://wa.me/919847000001?")
    items = data(await client.get(f"{API}/admin/enquiries", params={"type": "room"}, headers=h))
    assert items[0]["room_name"] == "Deluxe AC Room"


async def test_enquiry_for_booked_slot_is_409_tentative_is_ok(client, seeded):
    await client.post(f"{API}/admin/hall/bookings", json=booking("full"), headers=seeded["owner"])
    r = await client.post(f"{API}/public/enquiries", json=hall_enquiry())
    assert r.status_code == 409
    other = FUTURE + timedelta(days=3)
    await client.post(
        f"{API}/admin/hall/bookings",
        json=booking("evening", day=other, status="tentative"),
        headers=seeded["owner"],
    )
    r = await client.post(f"{API}/public/enquiries", json=hall_enquiry(date_from=other.isoformat()))
    assert r.status_code == 201


async def test_honeypot_saves_nothing(client, seeded):
    r = await client.post(f"{API}/public/enquiries", json=hall_enquiry(website="http://spam"))
    assert r.status_code == 201
    r = await client.get(f"{API}/admin/enquiries", headers=seeded["owner"])
    assert r.json()["data"] == [] and r.json()["message"] == "No enquiries found"
    assert r.json()["meta"] == {"current_page": 1, "per_page": 20, "total_records": 0, "total_pages": 0}


async def test_rate_limit(client, seeded, monkeypatch):
    monkeypatch.setattr(enquiry_limiter, "limit", 2)
    for _ in range(2):
        assert (await client.post(f"{API}/public/enquiries", json=hall_enquiry())).status_code == 201
    r = await client.post(f"{API}/public/enquiries", json=hall_enquiry())
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


async def test_admin_enquiry_list_filters_patch_and_csv(client, seeded):
    h = seeded["owner"]
    for i, name in enumerate(["Arun", "Meera", "Arjun"]):
        await client.post(f"{API}/public/enquiries", json=hall_enquiry(name=name, phone=f"984700000{i}"))
    url = f"{API}/admin/enquiries"
    page = (await client.get(url, params={"page": 2, "per_page": 2}, headers=h)).json()
    assert page["message"] == "Enquiries fetched successfully"
    assert page["meta"] == {"current_page": 2, "per_page": 2, "total_records": 3, "total_pages": 2}
    assert len(page["data"]) == 1
    old = (await client.get(url, params={"page_size": 2}, headers=h)).json()  # old param name still works
    assert old["meta"]["per_page"] == 2 and len(old["data"]) == 2
    found = data(await client.get(url, params={"q": "ar"}, headers=h))
    assert {e["name"] for e in found} == {"Arun", "Arjun"}
    by_phone = data(await client.get(url, params={"q": "9847000001"}, headers=h))
    assert [e["name"] for e in by_phone] == ["Meera"]

    eid = by_phone[0]["id"]
    r = await client.patch(
        f"{url}/{eid}", json={"status": "contacted", "admin_notes": "Visiting Saturday"}, headers=h
    )
    assert r.status_code == 200 and data(r)["status"] == "contacted"
    r = await client.patch(f"{url}/{eid}", json={"status": "bogus"}, headers=h)
    assert r.status_code == 422
    assert len(data(await client.get(url, params={"status": "contacted"}, headers=h))) == 1

    r = await client.get(f"{url}/export.csv", params={"status": "new"}, headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.lstrip("﻿").strip().splitlines()
    assert lines[0].startswith("created_at,type,status,name,phone")
    assert len(lines) == 3


async def test_dashboard_stats(client, seeded):
    h = seeded["owner"]
    await client.post(f"{API}/public/enquiries", json=hall_enquiry())
    await client.post(f"{API}/admin/hall/bookings", json=booking("morning"), headers=h)
    r = await client.get(f"{API}/admin/dashboard/stats", params={"month": MONTH}, headers=h)
    assert r.status_code == 200, r.text
    s = data(r)
    assert s["new_enquiries"] == 1 and s["open_enquiries"] == 1
    assert s["hall_bookings_this_month"] == 1
    assert s["upcoming_bookings"][0]["customer_name"] == "Arun"
    assert s["recent_enquiries"][0]["name"] == "Arun"
    assert s["month_bookings"] == [{"date": FUTURE.isoformat(), "slot": "morning", "status": "booked"}]
    assert (await client.get(f"{API}/admin/dashboard/stats", headers=h)).status_code == 200


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="needs PostgreSQL (advisory locks)")
async def test_concurrent_conflicting_bookings_only_one_wins(client, seeded):
    import asyncio

    url = f"{API}/admin/hall/bookings"
    day = FUTURE + timedelta(days=7)
    results = await asyncio.gather(
        client.post(url, json=booking("full", day=day), headers=seeded["owner"]),
        client.post(url, json=booking("morning", day=day), headers=seeded["staff"]),
        client.post(url, json=booking("evening", day=day), headers=seeded["staff"]),
    )
    codes = sorted(r.status_code for r in results)
    # Either "full" wins (201, 409, 409) or morning + evening win (201, 201, 409) — never all three.
    assert codes in ([201, 409, 409], [201, 201, 409]), [r.text for r in results]
