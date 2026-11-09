"""Settings, businesses, banners, menu, rooms, gallery, testimonials, FAQs, SEO."""

from tests.conftest import API, data, error_fields


async def test_settings_round_trip(client, seeded):
    h = seeded["owner"]
    r = await client.get(f"{API}/admin/settings", headers=h)
    assert r.status_code == 200
    assert all(v is None for v in data(r).values())
    body = {**data(r), "contact_phone": "9847000001", "address": "MC Road", "footer_text": ""}
    r = await client.put(f"{API}/admin/settings", json=body, headers=h)
    assert r.status_code == 200
    assert data(r)["contact_phone"] == "9847000001"
    assert data(r)["footer_text"] is None  # empty text -> null
    r = await client.get(f"{API}/public/settings")
    assert data(r)["address"] == "MC Road"
    assert "max-age" in r.headers["cache-control"]


async def test_businesses_list_and_patch(client, seeded):
    h = seeded["owner"]
    r = await client.get(f"{API}/admin/businesses", headers=h)
    assert [b["slug"] for b in data(r)] == ["sreebhavan-veg-hotel", "sreebhavanam"]
    bid = seeded["hotel_id"]
    body = {
        "slug": "hacked",
        "name": "Sreebhavan Veg Hotel",
        "logo_url": None,
        "about": "Pure vegetarian Kerala meals.",
        "whatsapp": "91 98470 12345",
        "phone": "04712345678",
        "timings": [{"label": "Mon – Sun", "hours": "6:00 am – 10:00 pm"}],
    }
    r = await client.patch(f"{API}/admin/businesses/{bid}", json=body, headers=h)
    assert r.status_code == 200, r.text
    assert data(r)["slug"] == "sreebhavan-veg-hotel"  # slug is fixed
    assert data(r)["whatsapp"] == "919847012345"
    assert data(r)["timings"][0]["hours"] == "6:00 am – 10:00 pm"
    r = await client.patch(f"{API}/admin/businesses/{bid}", json={**body, "whatsapp": "12345"}, headers=h)
    assert r.status_code == 422
    assert "whatsapp" in error_fields(r)
    assert "10-digit" in r.json()["message"]


async def test_banner_crud_and_public_filter(client, seeded):
    h = seeded["staff"]
    home = {"image_url": "https://x/b1.webp", "title": "Home banner", "sort": 2}
    hotel = {"image_url": "https://x/b2.webp", "title": "Hotel", "business_id": str(seeded["hotel_id"])}
    r1 = await client.post(f"{API}/admin/banners", json=home, headers=h)
    assert r1.status_code == 201, r1.text
    assert data(r1)["active"] is True and data(r1)["subtitle"] is None
    await client.post(f"{API}/admin/banners", json=hotel, headers=h)
    r = await client.post(f"{API}/admin/banners", json={"image_url": "x"}, headers=h)
    assert r.status_code == 422
    r = await client.post(
        f"{API}/admin/banners",
        json={**home, "business_id": "00000000-0000-0000-0000-000000000000"},
        headers=h,
    )
    assert r.status_code == 422
    assert data(await client.get(f"{API}/public/banners"))[0]["title"] == "Home banner"
    pub = data(await client.get(f"{API}/public/banners", params={"business": "sreebhavan-veg-hotel"}))
    assert [b["title"] for b in pub] == ["Hotel"]
    bid = data(r1)["id"]
    r = await client.patch(f"{API}/admin/banners/{bid}", json={**home, "active": False}, headers=h)
    assert data(r)["active"] is False
    assert data(await client.get(f"{API}/public/banners")) == []
    assert (await client.delete(f"{API}/admin/banners/{bid}", headers=h)).status_code == 200
    assert (await client.delete(f"{API}/admin/banners/{bid}", headers=h)).status_code == 404


async def test_menu_categories_items_and_rules(client, seeded):
    h = seeded["owner"]
    cat = {"name": "Breakfast", "name_ml": "പ്രഭാതഭക്ഷണം", "slug": "breakfast", "sort": 1}
    r = await client.post(f"{API}/admin/menu/categories", json=cat, headers=h)
    assert r.status_code == 201
    cat_id = data(r)["id"]
    r = await client.post(f"{API}/admin/menu/categories", json=cat, headers=h)
    assert r.status_code == 409
    assert "breakfast" in error_fields(r)["slug"]
    r = await client.post(f"{API}/admin/menu/categories", json={**cat, "slug": "Bad Slug"}, headers=h)
    assert r.status_code == 422

    item = {
        "category_id": cat_id,
        "name": "Masala Dosa",
        "slug": "masala-dosa",
        "price": 70,
        "is_special": True,
    }
    r = await client.post(f"{API}/admin/menu/items", json=item, headers=h)
    assert r.status_code == 201, r.text
    item_id = data(r)["id"]
    assert data(r)["is_available"] is True
    r = await client.post(
        f"{API}/admin/menu/items",
        json={**item, "slug": "x", "category_id": "00000000-0000-0000-0000-000000000000"},
        headers=h,
    )
    assert r.status_code == 422
    assert "category_id" in error_fields(r)

    # Partial quick toggle
    r = await client.patch(f"{API}/admin/menu/items/{item_id}", json={"is_available": False}, headers=h)
    assert r.status_code == 200
    assert data(r)["is_available"] is False and data(r)["name"] == "Masala Dosa"
    # Partial patch cannot clear a required field
    r = await client.patch(f"{API}/admin/menu/items/{item_id}", json={"name": ""}, headers=h)
    assert r.status_code == 422
    assert data(await client.get(f"{API}/public/menu/items")) == []
    await client.patch(f"{API}/admin/menu/items/{item_id}", json={"is_available": True}, headers=h)
    pub = data(
        await client.get(f"{API}/public/menu/items", params={"category": "breakfast", "special": "true"})
    )
    assert [i["slug"] for i in pub] == ["masala-dosa"]
    assert data(await client.get(f"{API}/public/menu/items", params={"special": "false"})) == []

    r = await client.delete(f"{API}/admin/menu/categories/{cat_id}", headers=h)
    assert r.status_code == 409
    assert "still has 1 food item" in r.json()["message"]
    await client.delete(f"{API}/admin/menu/items/{item_id}", headers=h)
    assert (await client.delete(f"{API}/admin/menu/categories/{cat_id}", headers=h)).status_code == 200


async def test_menu_cards(client, seeded):
    h = seeded["owner"]
    r = await client.post(
        f"{API}/admin/menu/cards", json={"title": "Full menu", "file_url": "https://x/m.pdf"}, headers=h
    )
    assert r.status_code == 201
    assert data(await client.get(f"{API}/public/menu/cards"))[0]["title"] == "Full menu"


async def test_rooms_with_images(client, seeded):
    h = seeded["owner"]
    room = {
        "slug": "deluxe-ac-room",
        "name": "Deluxe AC Room",
        "price": 2200,
        "capacity": 2,
        "amenities": ["AC", "TV"],
    }
    r = await client.post(f"{API}/admin/rooms", json=room, headers=h)
    assert r.status_code == 201, r.text
    assert data(r)["images"] == []
    rid = data(r)["id"]
    r = await client.post(
        f"{API}/admin/rooms/{rid}/images",
        json={"url": "https://x/r2.webp", "alt": "Bed", "sort": 2},
        headers=h,
    )
    assert r.status_code == 201
    await client.post(
        f"{API}/admin/rooms/{rid}/images",
        json={"url": "https://x/r1.webp", "alt": "View", "sort": 1},
        headers=h,
    )
    r = await client.post(
        f"{API}/admin/rooms/{rid}/images", json={"url": "https://x/r3.webp", "alt": ""}, headers=h
    )
    assert r.status_code == 422
    rooms = data(await client.get(f"{API}/admin/rooms", headers=h))
    assert [i["alt"] for i in rooms[0]["images"]] == ["View", "Bed"]
    pub = data(await client.get(f"{API}/public/rooms/deluxe-ac-room"))
    assert pub["price"] == 2200 and len(pub["images"]) == 2
    r = await client.patch(f"{API}/admin/rooms/{rid}", json={**room, "active": False}, headers=h)
    assert r.status_code == 200
    assert (await client.get(f"{API}/public/rooms/deluxe-ac-room")).status_code == 404
    img_id = rooms[0]["images"][0]["id"]
    assert (await client.delete(f"{API}/admin/rooms/{rid}/images/{img_id}", headers=h)).status_code == 200
    assert (await client.delete(f"{API}/admin/rooms/{rid}", headers=h)).status_code == 200


async def test_gallery_albums_and_images(client, seeded):
    h = seeded["owner"]
    album = {"slug": "wedding-arun-meera", "title": "Wedding", "category": "past-events", "sort": 1}
    r = await client.post(f"{API}/admin/gallery/albums", json=album, headers=h)
    assert r.status_code == 201
    aid = data(r)["id"]
    assert data(r)["image_count"] == 0
    r = await client.post(
        f"{API}/admin/gallery/albums", json={**album, "slug": "x", "category": "bad"}, headers=h
    )
    assert r.status_code == 422

    imgs = [
        {
            "url": f"https://x/{i}.webp",
            "thumb_url": f"https://x/{i}_thumb.webp",
            "alt": f"Photo {i}",
            "sort": i,
        }
        for i in range(3)
    ]
    r = await client.post(f"{API}/admin/gallery/images", json={"album_id": aid, "images": imgs}, headers=h)
    assert r.status_code == 201
    assert len(data(r)) == 3
    bad = [{"url": "https://x/z.webp", "alt": "  "}]
    r = await client.post(f"{API}/admin/gallery/images", json={"album_id": aid, "images": bad}, headers=h)
    assert r.status_code == 422

    r = await client.get(f"{API}/admin/gallery/albums/{aid}", headers=h)
    assert data(r)["image_count"] == 3
    assert data(r)["cover_url"] == "https://x/0_thumb.webp"
    r = await client.patch(
        f"{API}/admin/gallery/albums/{aid}", json={"cover_url": "https://x/2.webp"}, headers=h
    )
    assert data(r)["cover_url"] == "https://x/2.webp" and data(r)["title"] == "Wedding"

    listed = data(await client.get(f"{API}/admin/gallery/images", params={"album_id": aid}, headers=h))
    r = await client.patch(
        f"{API}/admin/gallery/images/{listed[0]['id']}",
        json={"alt": "New", "caption": "Hi", "sort": 9},
        headers=h,
    )
    assert data(r)["alt"] == "New"

    pub = data(await client.get(f"{API}/public/gallery/albums/wedding-arun-meera"))
    assert len(pub["images"]) == 3
    assert data(await client.get(f"{API}/public/gallery/albums"))[0]["image_count"] == 3

    assert (await client.delete(f"{API}/admin/gallery/albums/{aid}", headers=h)).status_code == 200
    assert data(await client.get(f"{API}/admin/gallery/images", params={"album_id": aid}, headers=h)) == []


async def test_testimonials_faqs_seo(client, seeded):
    h = seeded["owner"]
    t = {"name": "Lakshmi", "text": "Best dosa.", "rating": 5, "business_id": str(seeded["hotel_id"])}
    assert (await client.post(f"{API}/admin/testimonials", json=t, headers=h)).status_code == 201
    assert (
        await client.post(f"{API}/admin/testimonials", json={**t, "rating": 6}, headers=h)
    ).status_code == 422
    await client.post(
        f"{API}/admin/testimonials",
        json={**t, "name": "Ravi", "business_id": str(seeded["stays_id"])},
        headers=h,
    )
    pub = data(await client.get(f"{API}/public/testimonials", params={"business": "sreebhavan-veg-hotel"}))
    assert [x["name"] for x in pub] == ["Lakshmi"]

    await client.post(f"{API}/admin/faqs", json={"question": "Parking?", "answer": "Yes."}, headers=h)
    assert len(data(await client.get(f"{API}/public/faqs", params={"business": "sreebhavanam"}))) == 1

    seo = {
        "page_key": "room/deluxe-ac-room",
        "title": "Deluxe AC Room | Sreebhavanam",
        "description": "Clean rooms",
    }
    r = await client.post(f"{API}/admin/seo", json=seo, headers=h)
    assert r.status_code == 201
    assert (await client.post(f"{API}/admin/seo", json=seo, headers=h)).status_code == 409
    assert (
        await client.post(f"{API}/admin/seo", json={**seo, "page_key": "Bad Key"}, headers=h)
    ).status_code == 422
    assert (
        await client.post(f"{API}/admin/seo", json={**seo, "page_key": "x", "title": "t" * 61}, headers=h)
    ).status_code == 422
    pub = await client.get(f"{API}/public/seo/room/deluxe-ac-room")
    assert pub.status_code == 200 and data(pub)["title"].startswith("Deluxe")
    assert (await client.get(f"{API}/public/seo/nope")).status_code == 404


async def test_sitemap_data(client, seeded):
    h = seeded["owner"]
    await client.post(
        f"{API}/admin/rooms", json={"slug": "a", "name": "A", "price": 1, "capacity": 1}, headers=h
    )
    await client.post(
        f"{API}/admin/rooms",
        json={"slug": "b", "name": "B", "price": 1, "capacity": 1, "active": False},
        headers=h,
    )
    sitemap = data(await client.get(f"{API}/public/sitemap-data"))
    assert [r["slug"] for r in sitemap["rooms"]] == ["a"]
    assert "updated_at" in sitemap["rooms"][0]
