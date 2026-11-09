"""The standard response format: one example per case in the API guidelines."""

from tests.conftest import API, error_fields


async def test_success_single_object(client, seeded):
    r = await client.get(f"{API}/public/businesses/sreebhavanam")
    body = r.json()
    assert body["success"] is True and body["status_code"] == 200
    assert body["message"] == "Business details fetched successfully"
    assert body["data"]["slug"] == "sreebhavanam"


async def test_success_list_and_empty_list(client, seeded):
    empty = (await client.get(f"{API}/public/rooms")).json()
    assert empty == {"success": True, "status_code": 200, "message": "No rooms found", "data": []}
    await client.post(
        f"{API}/admin/rooms",
        json={"slug": "a", "name": "A", "price": 1, "capacity": 1},
        headers=seeded["owner"],
    )
    full = (await client.get(f"{API}/public/rooms")).json()
    assert full["message"] == "Rooms fetched successfully" and len(full["data"]) == 1


async def test_create_is_201_in_body_and_http(client, seeded):
    r = await client.post(
        f"{API}/admin/faqs", json={"question": "Q?", "answer": "A."}, headers=seeded["owner"]
    )
    assert r.status_code == 201
    assert r.json()["status_code"] == 201 and r.json()["message"] == "FAQ created successfully"


async def test_delete_returns_deleted_id(client, seeded):
    h = seeded["owner"]
    faq = (await client.post(f"{API}/admin/faqs", json={"question": "Q?", "answer": "A."}, headers=h)).json()
    r = await client.delete(f"{API}/admin/faqs/{faq['data']['id']}", headers=h)
    assert r.json() == {
        "success": True,
        "status_code": 200,
        "message": "FAQ deleted successfully",
        "data": {"id": faq["data"]["id"]},
    }


async def test_validation_error_lists_every_field(client, seeded):
    r = await client.post(f"{API}/admin/rooms", json={"name": "", "price": -1}, headers=seeded["owner"])
    body = r.json()
    assert r.status_code == 422 and body["status_code"] == 422
    assert body["success"] is False and body["message"] == "Validation failed"
    fields = error_fields(r)
    assert fields["slug"] == "Slug is required."
    assert fields["name"] == "Name is required."
    assert fields["capacity"] == "Capacity is required."
    assert fields["price"] == "Price should be greater than or equal to 0."


async def test_single_validation_error_uses_its_message(client, seeded):
    r = await client.get(f"{API}/admin/hall/bookings", params={"month": "2026-13"}, headers=seeded["owner"])
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "month"
    assert r.json()["message"] == r.json()["errors"][0]["message"]


async def test_business_rule_error_names_the_field(client, seeded):
    r = await client.post(
        f"{API}/public/enquiries",
        json={"type": "hall", "name": "Arun", "phone": "9847012345", "date_from": None},
    )
    assert r.status_code == 422
    assert error_fields(r) == {"date_from": "Pick the date for the event hall."}


async def test_auth_error(client, seeded):
    r = await client.get(f"{API}/admin/enquiries")
    assert r.json() == {
        "success": False,
        "status_code": 401,
        "message": "Please sign in again.",
        "errors": [],
    }


async def test_unknown_route_wrong_method_and_bad_json(client, seeded):
    r = await client.get(f"{API}/public/nope")
    assert r.status_code == 404 and r.json()["message"] == "The requested resource was not found."
    r = await client.delete(f"{API}/public/rooms")
    assert r.status_code == 405 and r.json()["success"] is False
    r = await client.post(
        f"{API}/admin/faqs",
        content=b"{not json",
        headers={**seeded["owner"], "content-type": "application/json"},
    )
    assert r.status_code == 422 and r.json()["message"] == "The request body is not valid JSON."


async def test_health(client):
    r = await client.get("/health")
    assert r.json() == {
        "success": True,
        "status_code": 200,
        "message": "Service is running",
        "data": {"status": "ok"},
    }
