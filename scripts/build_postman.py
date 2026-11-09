"""Builds the Postman collection from the FastAPI app.

    uv run python scripts/build_postman.py

Writes postman/Sreebhavan-API.postman_collection.json. The request list below is curated (order, example
bodies, scripts that save ids), and the script fails if any endpoint in the app's OpenAPI schema is missing
from it, so the collection cannot silently fall behind the API.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402

PREFIX = "/api/v1"
OUT = ROOT / "postman" / "Sreebhavan-API.postman_collection.json"


# ---- script snippets -------------------------------------------------------------------
def expect(*codes: int) -> list[str]:
    if len(codes) == 1:
        return [f'pm.test("Status is {codes[0]}", () => pm.response.to.have.status({codes[0]}));']
    return [
        f'pm.test("Status is one of {list(codes)}", () => '
        f"pm.expect(pm.response.code).to.be.oneOf({list(codes)}));"
    ]


def save(var: str, expr: str = "body.data.id") -> list[str]:
    return [
        "if (pm.response.code < 300) {",
        "  const body = pm.response.json();",
        f'  pm.collectionVariables.set("{var}", {expr});',
        "}",
    ]


def skip_unless(var: str) -> list[str]:
    return [
        f'if (!pm.collectionVariables.get("{var}")) {{',
        f'  console.log("Skipped: run the request that sets {{{{{var}}}}} first.");',
        "  pm.execution.skipRequest();",
        "}",
    ]


# ---- curated requests ------------------------------------------------------------------
# Each entry: folder, name, method, OpenAPI path, URL (with {{vars}}), plus optional body, query,
# tests, prerequest, auth ("none" for public), form (multipart), desc.
R: list[dict] = []


def add(folder, name, method, path, url=None, **kw):
    R.append({"folder": folder, "name": name, "method": method, "path": path, "url": url or path, **kw})


A = "/admin"
# Auth
add(
    "1. Auth",
    "Login",
    "POST",
    f"{A}/auth/login",
    auth="none",
    body={"email": "{{adminEmail}}", "password": "{{adminPassword}}"},
    tests=expect(200) + save("accessToken", "body.data.access_token") + save("adminId", "body.data.admin.id"),
    desc="Signs in through FastAPI (which signs in with Supabase Auth). The access token is saved to "
    "`{{accessToken}}` and sent as a Bearer token by every admin request. Run this first.",
)
add(
    "1. Auth",
    "Forgot password",
    "POST",
    f"{A}/auth/forgot-password",
    auth="none",
    body={"email": "{{adminEmail}}"},
    tests=expect(200),
    desc="Always returns 200, whether or not the email belongs to an admin. "
    "Sends a real Supabase reset email when it does.",
)

# Dashboard
add(
    "2. Dashboard",
    "Dashboard stats",
    "GET",
    f"{A}/dashboard/stats",
    query={"month": "{{month}}"},
    tests=expect(200),
)

# Settings
add(
    "3. Site settings",
    "Get site settings",
    "GET",
    f"{A}/settings",
    tests=expect(200) + save("settingsBody", "JSON.stringify(body.data, null, 2)"),
    desc="Also copies the current settings into `{{settingsBody}}` for the next request.",
)
add(
    "3. Site settings",
    "Save site settings",
    "PUT",
    f"{A}/settings",
    raw="{{settingsBody}}",
    tests=expect(200),
    prerequest=skip_unless("settingsBody"),
    desc="Receives the whole settings object. The body is the copy taken by *Get site settings*, so running "
    "the collection changes nothing. To edit, replace the body with JSON such as:\n\n```json\n"
    + json.dumps(
        {
            "brand_logo_url": None,
            "favicon_url": None,
            "contact_phone": "9847000001",
            "contact_email": "hello@example.com",
            "address": "MC Road, Town, Kerala",
            "map_embed_url": None,
            "map_link_url": None,
            "facebook_url": None,
            "instagram_url": None,
            "youtube_url": None,
            "footer_text": "© Sreebhavan",
            "google_analytics_id": None,
            "search_console_verification": None,
        },
        indent=2,
        ensure_ascii=False,
    )
    + "\n```",
)

# Businesses
add(
    "4. Businesses",
    "List businesses",
    "GET",
    f"{A}/businesses",
    tests=expect(200)
    + [
        "const list = pm.response.json().data || [];",
        'const stays = list.find(b => b.slug === "sreebhavanam");',
        'const hotel = list.find(b => b.slug === "sreebhavan-veg-hotel");',
        "if (stays) {",
        '  pm.collectionVariables.set("businessId", stays.id);',
        "  const { id, slug, ...editable } = stays;",
        '  pm.collectionVariables.set("businessBody", JSON.stringify(editable, null, 2));',
        "}",
        'if (hotel) pm.collectionVariables.set("hotelBusinessId", hotel.id);',
    ],
    desc="Saves `{{businessId}}` (Sreebhavanam), `{{hotelBusinessId}}` and a copy of Sreebhavanam's "
    "editable fields.",
)
add(
    "4. Businesses",
    "Update business",
    "PATCH",
    f"{A}/businesses/{{business_id}}",
    url=f"{A}/businesses/{{{{businessId}}}}",
    raw="{{businessBody}}",
    prerequest=skip_unless("businessBody"),
    tests=expect(200),
    desc="The slug cannot change. `whatsapp` must be a 10-digit Indian mobile number, optionally starting "
    "with 91. The body is the copy taken by *List businesses*, so running it changes nothing. Example:\n\n"
    "```json\n"
    + json.dumps(
        {
            "name": "Sreebhavanam",
            "logo_url": None,
            "about": "Event hall and rooms.",
            "whatsapp": "9847000002",
            "phone": "04712345678",
            "timings": [{"label": "Front desk", "hours": "Open 24 hours"}],
        },
        indent=2,
    )
    + "\n```",
)

# Banners
add(
    "5. Banners",
    "List banners",
    "GET",
    f"{A}/banners",
    tests=expect(200),
)
add(
    "5. Banners",
    "Create banner",
    "POST",
    f"{A}/banners",
    body={
        "business_id": None,
        "image_url": "https://placehold.co/1600x600.webp",
        "title": "Pure vegetarian taste of Kerala",
        "subtitle": "Postman test banner",
        "cta_text": "View menu",
        "cta_link": "/sreebhavan-veg-hotel/menu",
        "sort": 99,
        "active": True,
    },
    tests=expect(201) + save("bannerId"),
    desc="`business_id: null` = home-page banner. Required: `image_url`, `title`.",
)
add(
    "5. Banners",
    "Update banner",
    "PATCH",
    f"{A}/banners/{{obj_id}}",
    url=f"{A}/banners/{{{{bannerId}}}}",
    body={"title": "Pure vegetarian taste of Kerala (edited)", "active": False},
    prerequest=skip_unless("bannerId"),
    tests=expect(200),
    desc="Send all fields or only the ones to change.",
)

# Menu
add("6. Menu", "List categories", "GET", f"{A}/menu/categories", tests=expect(200))
add(
    "6. Menu",
    "Create category",
    "POST",
    f"{A}/menu/categories",
    body={
        "name": "Breakfast",
        "name_ml": "പ്രഭാതഭക്ഷണം",
        "slug": "breakfast-{{runId}}",
        "image_url": None,
        "sort": 1,
        "active": True,
    },
    tests=expect(201) + save("categoryId") + save("categorySlug", "body.data.slug"),
    desc="`slug` must be unique and look like `breakfast` (lowercase, numbers, single hyphens).",
)
add(
    "6. Menu",
    "Update category",
    "PATCH",
    f"{A}/menu/categories/{{obj_id}}",
    url=f"{A}/menu/categories/{{{{categoryId}}}}",
    body={"name": "Breakfast & Tiffin"},
    prerequest=skip_unless("categoryId"),
    tests=expect(200),
)
add("6. Menu", "List food items", "GET", f"{A}/menu/items", tests=expect(200))
add(
    "6. Menu",
    "Create food item",
    "POST",
    f"{A}/menu/items",
    body={
        "category_id": "{{categoryId}}",
        "name": "Masala Dosa",
        "name_ml": "മസാല ദോശ",
        "slug": "masala-dosa-{{runId}}",
        "price": 70,
        "image_url": None,
        "description": "Crispy dosa with potato masala, sambar and chutney.",
        "is_special": True,
        "is_available": True,
        "sort": 1,
    },
    prerequest=skip_unless("categoryId"),
    tests=expect(201) + save("itemId"),
)
add(
    "6. Menu",
    "Toggle item available (partial)",
    "PATCH",
    f"{A}/menu/items/{{obj_id}}",
    url=f"{A}/menu/items/{{{{itemId}}}}",
    body={"is_available": True},
    prerequest=skip_unless("itemId"),
    tests=expect(200),
    desc="The list's quick toggles send only `is_available` or `is_special`.",
)
add("6. Menu", "List menu cards", "GET", f"{A}/menu/cards", tests=expect(200))
add(
    "6. Menu",
    "Create menu card",
    "POST",
    f"{A}/menu/cards",
    body={"title": "Full menu (Postman)", "file_url": "https://example.com/menu.pdf", "active": True},
    tests=expect(201) + save("cardId"),
    desc="Upload the PDF first with *Uploads › Upload file* (folder `menu/cards`) and use the returned URL.",
)
add(
    "6. Menu",
    "Update menu card",
    "PATCH",
    f"{A}/menu/cards/{{obj_id}}",
    url=f"{A}/menu/cards/{{{{cardId}}}}",
    body={"active": False},
    prerequest=skip_unless("cardId"),
    tests=expect(200),
)

# Rooms
add("7. Rooms", "List rooms", "GET", f"{A}/rooms", tests=expect(200))
add(
    "7. Rooms",
    "Create room",
    "POST",
    f"{A}/rooms",
    body={
        "slug": "deluxe-ac-room-{{runId}}",
        "name": "Deluxe AC Room",
        "price": 2200,
        "capacity": 2,
        "amenities": ["AC", "Wi-Fi", "TV"],
        "description": "Postman test room.",
        "active": True,
    },
    tests=expect(201) + save("roomId") + save("roomSlug", "body.data.slug"),
)
add(
    "7. Rooms",
    "Update room",
    "PATCH",
    f"{A}/rooms/{{room_id}}",
    url=f"{A}/rooms/{{{{roomId}}}}",
    body={"price": 2400},
    prerequest=skip_unless("roomId"),
    tests=expect(200),
)
add(
    "7. Rooms",
    "Add room photo",
    "POST",
    f"{A}/rooms/{{room_id}}/images",
    url=f"{A}/rooms/{{{{roomId}}}}/images",
    body={"url": "https://placehold.co/1200x800.webp", "alt": "Deluxe room with double bed", "sort": 0},
    prerequest=skip_unless("roomId"),
    tests=expect(201) + save("roomImageId"),
    desc="`alt` is required. Upload the image first with *Uploads › Upload file* (folder `rooms`).",
)

# Hall
add(
    "8. Event hall",
    "Get hall",
    "GET",
    f"{A}/hall",
    tests=expect(200, 404)
    + [
        "if (pm.response.code === 200) {",
        '  pm.collectionVariables.set("hallBody", JSON.stringify(pm.response.json().data, null, 2));',
        "} else {",
        '  pm.collectionVariables.set("hallBody", JSON.stringify({',
        '    name: "Sreebhavanam Hall", capacity_seating: 600, capacity_floating: 900,',
        '    facilities: ["AC", "Stage", "Parking"], rules: "No outside catering.\\nMusic till 10 pm."',
        "  }, null, 2));",
        "}",
    ],
    desc="404 until the hall has been saved once. Copies the current hall (or a sample) into `{{hallBody}}`.",
)
add(
    "8. Event hall",
    "Save hall",
    "PUT",
    f"{A}/hall",
    raw="{{hallBody}}",
    prerequest=skip_unless("hallBody"),
    tests=expect(200),
    desc="Creates or replaces the hall. The body comes from *Get hall*, so existing details are kept.",
)
add("8. Event hall", "List packages", "GET", f"{A}/hall/packages", tests=expect(200))
add(
    "8. Event hall",
    "Create package",
    "POST",
    f"{A}/hall/packages",
    body={
        "name": "Wedding – full day (Postman)",
        "price": 85000,
        "inclusions": ["Hall for 12 hours", "Stage decoration"],
        "sort": 99,
    },
    tests=expect(201) + save("packageId"),
)
add(
    "8. Event hall",
    "Update package",
    "PATCH",
    f"{A}/hall/packages/{{obj_id}}",
    url=f"{A}/hall/packages/{{{{packageId}}}}",
    body={"price": 90000},
    prerequest=skip_unless("packageId"),
    tests=expect(200),
)
add("8. Event hall", "List hall photos", "GET", f"{A}/hall/images", tests=expect(200))
add(
    "8. Event hall",
    "Add hall photo",
    "POST",
    f"{A}/hall/images",
    body={"url": "https://placehold.co/1200x800.webp", "alt": "Hall stage with lights", "sort": 99},
    tests=expect(201) + save("hallImageId"),
)
add(
    "8. Event hall",
    "List bookings (month)",
    "GET",
    f"{A}/hall/bookings",
    query={"month": "{{month}}"},
    tests=expect(200),
)
add(
    "8. Event hall",
    "Create booking",
    "POST",
    f"{A}/hall/bookings",
    body={
        "date": "{{futureDate}}",
        "slot": "evening",
        "status": "tentative",
        "customer_name": "Arun (Postman)",
        "phone": "9847012345",
        "event_type": "Wedding",
        "notes": None,
    },
    tests=expect(201) + save("bookingId"),
    desc="`slot`: morning, evening or full. `status`: booked or tentative. A `full` booking blocks morning and "
    "evening on the same date (and vice versa): the API returns 409 with the error on field `slot`. "
    "`{{futureDate}}` is a random date 1–2 years ahead.",
)
add(
    "8. Event hall",
    "Double booking is refused (409)",
    "POST",
    f"{A}/hall/bookings",
    body={"date": "{{futureDate}}", "slot": "full", "status": "booked", "customer_name": "Clash"},
    prerequest=skip_unless("bookingId"),
    tests=expect(409),
    desc="Same date as *Create booking*: a full-day booking clashes with the evening one.",
)
add(
    "8. Event hall",
    "Update booking",
    "PATCH",
    f"{A}/hall/bookings/{{booking_id}}",
    url=f"{A}/hall/bookings/{{{{bookingId}}}}",
    body={"status": "booked", "notes": "Advance paid"},
    prerequest=skip_unless("bookingId"),
    tests=expect(200),
)

# Uploads
add(
    "9. Uploads",
    "Upload file",
    "POST",
    f"{A}/uploads",
    form=[("folder", "text", "gallery"), ("file", "file", "postman/sample.png")],
    tests=expect(201) + save("uploadUrl", "body.data.url") + save("uploadThumbUrl", "body.data.thumb_url"),
    desc="multipart/form-data. `folder`: logos, banners, menu/items, menu/cards, rooms, hall, gallery, "
    "testimonials, seo. Images (JPEG, PNG, WebP) are resized and converted to WebP with a thumbnail; "
    "`menu/cards` also takes PDF; `logos` also takes SVG and ICO. Max 5 MB. In the Postman app, pick the file "
    "in the Body tab (`postman/sample.png` is included). Saves `{{uploadUrl}}` and `{{uploadThumbUrl}}`.",
)

# Gallery
add("10. Gallery", "List albums", "GET", f"{A}/gallery/albums", tests=expect(200))
add(
    "10. Gallery",
    "Create album",
    "POST",
    f"{A}/gallery/albums",
    body={
        "slug": "wedding-arun-meera-{{runId}}",
        "title": "Wedding of Arun & Meera",
        "category": "past-events",
        "cover_url": None,
        "sort": 99,
        "active": True,
    },
    tests=expect(201) + save("albumId") + save("albumSlug", "body.data.slug"),
    desc="`category`: rooms, hall, past-events, food, exterior.",
)
add(
    "10. Gallery",
    "Get album",
    "GET",
    f"{A}/gallery/albums/{{album_id}}",
    url=f"{A}/gallery/albums/{{{{albumId}}}}",
    prerequest=skip_unless("albumId"),
    tests=expect(200),
)
add(
    "10. Gallery",
    "Add photos (bulk)",
    "POST",
    f"{A}/gallery/images",
    body={
        "album_id": "{{albumId}}",
        "images": [
            {
                "url": "{{uploadUrl}}",
                "thumb_url": "{{uploadThumbUrl}}",
                "alt": "Bride and groom on stage",
                "caption": None,
                "sort": 1,
            }
        ],
    },
    prerequest=skip_unless("albumId")
    + [
        'if (!pm.collectionVariables.get("uploadUrl")) {',
        '  pm.collectionVariables.set("uploadUrl", "https://placehold.co/1600x1000.webp");',
        '  pm.collectionVariables.set("uploadThumbUrl", "https://placehold.co/480x300.webp");',
        "}",
    ],
    tests=expect(201) + save("galleryImageId", "body.data[0].id"),
    desc="Files are uploaded first with *Uploads › Upload file*; this saves their URLs. `alt` is required on "
    "every photo.",
)
add(
    "10. Gallery",
    "List album photos",
    "GET",
    f"{A}/gallery/images",
    query={"album_id": "{{albumId}}"},
    prerequest=skip_unless("albumId"),
    tests=expect(200),
)
add(
    "10. Gallery",
    "Update photo",
    "PATCH",
    f"{A}/gallery/images/{{image_id}}",
    url=f"{A}/gallery/images/{{{{galleryImageId}}}}",
    body={"alt": "Couple on the decorated stage", "caption": "Reception", "sort": 1},
    prerequest=skip_unless("galleryImageId"),
    tests=expect(200),
)
add(
    "10. Gallery",
    "Set album cover (partial)",
    "PATCH",
    f"{A}/gallery/albums/{{album_id}}",
    url=f"{A}/gallery/albums/{{{{albumId}}}}",
    body={"cover_url": "{{uploadThumbUrl}}"},
    prerequest=skip_unless("albumId"),
    tests=expect(200),
)

# Testimonials / FAQs / SEO
add("11. Testimonials & FAQs", "List testimonials", "GET", f"{A}/testimonials", tests=expect(200))
add(
    "11. Testimonials & FAQs",
    "Create testimonial",
    "POST",
    f"{A}/testimonials",
    body={
        "name": "Lakshmi",
        "text": "Best masala dosa in town.",
        "rating": 5,
        "business_id": "{{hotelBusinessId}}",
        "sort": 99,
        "active": False,
    },
    tests=expect(201) + save("testimonialId"),
    desc="`rating` 1–5. `business_id: null` = shown for both businesses. Created inactive so it never appears "
    "on the live site.",
)
add(
    "11. Testimonials & FAQs",
    "Update testimonial",
    "PATCH",
    f"{A}/testimonials/{{obj_id}}",
    url=f"{A}/testimonials/{{{{testimonialId}}}}",
    body={"rating": 4},
    prerequest=skip_unless("testimonialId"),
    tests=expect(200),
)
add("11. Testimonials & FAQs", "List FAQs", "GET", f"{A}/faqs", tests=expect(200))
add(
    "11. Testimonials & FAQs",
    "Create FAQ",
    "POST",
    f"{A}/faqs",
    body={
        "business_id": None,
        "question": "How many guests does the hall seat? (Postman)",
        "answer": "600 seated.",
        "sort": 99,
    },
    tests=expect(201) + save("faqId"),
)
add(
    "11. Testimonials & FAQs",
    "Update FAQ",
    "PATCH",
    f"{A}/faqs/{{obj_id}}",
    url=f"{A}/faqs/{{{{faqId}}}}",
    body={"answer": "600 seated, 900 floating."},
    prerequest=skip_unless("faqId"),
    tests=expect(200),
)
add("12. SEO", "List SEO entries", "GET", f"{A}/seo", tests=expect(200))
add(
    "12. SEO",
    "Create SEO entry",
    "POST",
    f"{A}/seo",
    body={
        "page_key": "room/postman-{{runId}}",
        "title": "Rooms in Town | Sreebhavanam",
        "description": "Clean AC and non-AC rooms near the town centre.",
        "og_image": None,
        "keywords": "rooms in town, ac rooms",
        "noindex": True,
    },
    tests=expect(201) + save("seoId") + save("seoPageKey", "body.data.page_key"),
    desc="`page_key`: a page (`home`, `rooms`, `event-hall`, ...) or an item (`room/<slug>`, `menu/<slug>`, "
    "`gallery/<slug>`). `title` up to 60 characters, `description` up to 160.",
)
add(
    "12. SEO",
    "Update SEO entry",
    "PATCH",
    f"{A}/seo/{{obj_id}}",
    url=f"{A}/seo/{{{{seoId}}}}",
    body={"description": "Clean AC rooms near the town centre, free Wi-Fi."},
    prerequest=skip_unless("seoId"),
    tests=expect(200),
)

# Users
OWNER = "Owner only: staff get 403."
add("13. Admin users", "List admin users", "GET", f"{A}/users", tests=expect(200), desc=OWNER)
add(
    "13. Admin users",
    "Invite admin user",
    "POST",
    f"{A}/users",
    body={"name": "Front Desk", "email": "{{inviteEmail}}", "role": "staff", "active": True},
    tests=expect(201) + save("userId"),
    desc=OWNER + " Sends a Supabase invite email to `{{inviteEmail}}` (default: a throwaway "
    "`postman-<run>@example.com`). 409 if the email is already an admin.",
)
add(
    "13. Admin users",
    "Update admin user",
    "PATCH",
    f"{A}/users/{{user_id}}",
    url=f"{A}/users/{{{{userId}}}}",
    body={"name": "Front Desk (evening)", "email": "{{inviteEmail}}", "role": "staff", "active": True},
    prerequest=skip_unless("userId"),
    tests=expect(200),
    desc=OWNER + " Changes to `email` are ignored. You cannot demote, deactivate or delete yourself (409).",
)
add(
    "13. Admin users",
    "Send password reset",
    "POST",
    f"{A}/users/{{user_id}}/reset-password",
    url=f"{A}/users/{{{{userId}}}}/reset-password",
    prerequest=skip_unless("userId"),
    tests=expect(200),
    desc=OWNER,
)

# Public website
P = "/public"
pub = {"auth": "none"}
add("14. Public website", "Site settings", "GET", f"{P}/settings", tests=expect(200), **pub)
add("14. Public website", "Business by slug", "GET", f"{P}/businesses/{{slug}}",
    url=f"{P}/businesses/sreebhavanam", tests=expect(200), **pub)  # fmt: skip
add("14. Public website", "Home banners", "GET", f"{P}/banners", tests=expect(200), **pub,
    desc="Add `?business=sreebhavan-veg-hotel` for a business's banners.")  # fmt: skip
add("14. Public website", "Menu categories", "GET", f"{P}/menu/categories", tests=expect(200), **pub)
add("14. Public website", "Menu items", "GET", f"{P}/menu/items",
    query={"category": "{{categorySlug}}", "special": "true"}, tests=expect(200), **pub,
    desc="Both filters are optional. `special=true` gives today's specials.")  # fmt: skip
add("14. Public website", "Menu cards", "GET", f"{P}/menu/cards", tests=expect(200), **pub)
add("14. Public website", "Rooms", "GET", f"{P}/rooms", tests=expect(200), **pub)
add("14. Public website", "Room by slug", "GET", f"{P}/rooms/{{slug}}",
    url=f"{P}/rooms/{{{{roomSlug}}}}", tests=expect(200, 404), **pub)  # fmt: skip
add("14. Public website", "Hall", "GET", f"{P}/hall", tests=expect(200, 404), **pub)
add("14. Public website", "Hall packages", "GET", f"{P}/hall/packages", tests=expect(200), **pub)
add("14. Public website", "Hall availability", "GET", f"{P}/hall/availability",
    query={"month": "{{month}}"}, tests=expect(200), **pub,
    desc="Only `{ date, slot, status }`: never customer details.")  # fmt: skip
add("14. Public website", "Gallery albums", "GET", f"{P}/gallery/albums", tests=expect(200), **pub)
add("14. Public website", "Album by slug", "GET", f"{P}/gallery/albums/{{slug}}",
    url=f"{P}/gallery/albums/{{{{albumSlug}}}}", tests=expect(200, 404), **pub)  # fmt: skip
add("14. Public website", "Testimonials", "GET", f"{P}/testimonials", tests=expect(200), **pub)
add("14. Public website", "FAQs", "GET", f"{P}/faqs", query={"business": "sreebhavanam"},
    tests=expect(200), **pub)  # fmt: skip
add("14. Public website", "SEO for a page", "GET", f"{P}/seo/{{page_key}}",
    url=f"{P}/seo/{{{{seoPageKey}}}}", tests=expect(200, 404), **pub,
    desc="Item keys contain a slash, e.g. `/public/seo/room/deluxe-ac-room`.")  # fmt: skip
add("14. Public website", "Sitemap data", "GET", f"{P}/sitemap-data", tests=expect(200), **pub)
add(
    "14. Public website",
    "Send enquiry (hall)",
    "POST",
    f"{P}/enquiries",
    body={
        "type": "hall",
        "name": "Arun (Postman)",
        "phone": "9847012345",
        "email": None,
        "date_from": "{{enquiryDate}}",
        "date_to": None,
        "slot": "morning",
        "guests": 400,
        "event_type": "Wedding",
        "message": "Postman test enquiry.",
        "website": "",
    },
    tests=expect(201) + save("enquiryId"),
    desc="Saves the enquiry, then returns `data.whatsapp_url` (a wa.me link with the message filled in). "
    "`hall` needs `date_from` + `slot`; `room` needs `room_id` or `room_slug`; `hotel` needs neither. "
    "`website` is a honeypot and must stay empty. Rate limited per IP (429 with `Retry-After`).",
    **pub,
)

# Enquiries (admin)
add(
    "15. Enquiries",
    "List enquiries (paginated)",
    "GET",
    f"{A}/enquiries",
    query={"type": "", "status": "", "q": "", "page": "1", "per_page": "20"},
    tests=expect(200),
    desc="All filters are optional (empty values are ignored). `q` searches name and phone. "
    "Pagination is in `meta`.",
)
add(
    "15. Enquiries",
    "Update enquiry status",
    "PATCH",
    f"{A}/enquiries/{{enquiry_id}}",
    url=f"{A}/enquiries/{{{{enquiryId}}}}",
    body={"status": "contacted", "admin_notes": "Called back, visiting Saturday."},
    prerequest=skip_unless("enquiryId"),
    tests=expect(200),
    desc="Partial: only `status` (new, contacted, confirmed, cancelled) and `admin_notes`.",
)
add(
    "15. Enquiries",
    "Export enquiries (CSV)",
    "GET",
    f"{A}/enquiries/export.csv",
    query={"status": "contacted"},
    tests=expect(200)
    + [
        'pm.test("Is a CSV file", () => pm.expect(pm.response.headers.get("Content-Type")).to.include("text/csv"));'
    ],
    desc="A file download (no JSON envelope). Same filters as the list, not paginated. "
    "Use *Send and Download* in the Postman app.",
)

# Cleanup
C = "16. Cleanup (deletes test data)"
for name, opath, url, var in [
    ("Delete hall booking", f"{A}/hall/bookings/{{booking_id}}", f"{A}/hall/bookings/{{{{bookingId}}}}", "bookingId"),
    ("Delete hall photo", f"{A}/hall/images/{{image_id}}", f"{A}/hall/images/{{{{hallImageId}}}}", "hallImageId"),
    ("Delete hall package", f"{A}/hall/packages/{{obj_id}}", f"{A}/hall/packages/{{{{packageId}}}}", "packageId"),
    ("Delete room photo", f"{A}/rooms/{{room_id}}/images/{{image_id}}",
     f"{A}/rooms/{{{{roomId}}}}/images/{{{{roomImageId}}}}", "roomImageId"),
    ("Delete room", f"{A}/rooms/{{room_id}}", f"{A}/rooms/{{{{roomId}}}}", "roomId"),
    ("Delete gallery photo", f"{A}/gallery/images/{{image_id}}",
     f"{A}/gallery/images/{{{{galleryImageId}}}}", "galleryImageId"),
    ("Delete album (and its photos)", f"{A}/gallery/albums/{{album_id}}", f"{A}/gallery/albums/{{{{albumId}}}}", "albumId"),
    ("Delete food item", f"{A}/menu/items/{{obj_id}}", f"{A}/menu/items/{{{{itemId}}}}", "itemId"),
    ("Delete category", f"{A}/menu/categories/{{obj_id}}", f"{A}/menu/categories/{{{{categoryId}}}}", "categoryId"),
    ("Delete menu card", f"{A}/menu/cards/{{obj_id}}", f"{A}/menu/cards/{{{{cardId}}}}", "cardId"),
    ("Delete banner", f"{A}/banners/{{obj_id}}", f"{A}/banners/{{{{bannerId}}}}", "bannerId"),
    ("Delete testimonial", f"{A}/testimonials/{{obj_id}}", f"{A}/testimonials/{{{{testimonialId}}}}", "testimonialId"),
    ("Delete FAQ", f"{A}/faqs/{{obj_id}}", f"{A}/faqs/{{{{faqId}}}}", "faqId"),
    ("Delete SEO entry", f"{A}/seo/{{obj_id}}", f"{A}/seo/{{{{seoId}}}}", "seoId"),
    ("Delete admin user", f"{A}/users/{{user_id}}", f"{A}/users/{{{{userId}}}}", "userId"),
]:  # fmt: skip
    add(
        C,
        name,
        "DELETE",
        opath,
        url=url,
        prerequest=skip_unless(var),
        tests=expect(200, 404) + [f'pm.collectionVariables.unset("{var}");'],
        desc="Deleting a category that still has food items returns 409." if "category" in name else None,
    )

add(
    "17. Sign out",
    "Logout",
    "POST",
    f"{A}/auth/logout",
    tests=expect(200, 401) + ['pm.collectionVariables.unset("accessToken");'],
    desc="Revokes the Supabase session and clears `{{accessToken}}`.",
)
add(
    "17. Sign out", "Health check", "GET", "/health", url="{{rootUrl}}/health", auth="none", tests=expect(200)
)


# ---- collection-level scripts ------------------------------------------------------------
PRE = [
    "// Values every request can use. Set once per run; override any of them in the collection variables.",
    "const v = pm.collectionVariables;",
    'if (!v.get("runId")) v.set("runId", Date.now().toString(36));',
    "const pad = n => String(n).padStart(2, '0');",
    "const ymd = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;",
    'if (!v.get("month")) { const d = new Date(); v.set("month", `${d.getFullYear()}-${pad(d.getMonth() + 1)}`); }',
    'if (!v.get("futureDate")) {',
    "  const d = new Date(); d.setDate(d.getDate() + 365 + Math.floor(Math.random() * 365));",
    '  v.set("futureDate", ymd(d));',
    "}",
    'if (!v.get("enquiryDate")) {',
    "  const d = new Date(); d.setDate(d.getDate() + 365 + Math.floor(Math.random() * 365));",
    '  v.set("enquiryDate", ymd(d));',
    "}",
    'if (!v.get("inviteEmail")) v.set("inviteEmail", `postman-${v.get("runId")}@example.com`);',
    'if (!pm.environment.get("rootUrl") && !v.get("rootUrl")) {',
    '  v.set("rootUrl", pm.variables.get("baseUrl").replace(/\\/api\\/v1\\/?$/, ""));',
    "}",
]
TEST = [
    "// Every JSON response must use the standard format.",
    'const ct = pm.response.headers.get("Content-Type") || "";',
    'if (ct.includes("application/json")) {',
    "  const b = pm.response.json();",
    '  pm.test("Standard response format", () => {',
    '    pm.expect(b).to.be.an("object");',
    '    pm.expect(b.success, "success").to.be.a("boolean");',
    '    pm.expect(b.status_code, "status_code matches HTTP status").to.eql(pm.response.code);',
    '    pm.expect(b.message, "message").to.be.a("string").and.not.empty;',
    '    if (b.success) { pm.expect(b).to.have.property("data"); }',
    '    else { pm.expect(b.errors, "errors").to.be.an("array"); }',
    "  });",
    "  if (!b.success) console.log(`${pm.response.code} ${b.message}`, JSON.stringify(b.errors));",
    "}",
]


def script(listen: str, lines: list[str]) -> dict:
    return {"listen": listen, "script": {"type": "text/javascript", "exec": lines}}


def url_obj(url: str, query: dict | None) -> dict:
    is_root = url.startswith("{{rootUrl}}")
    raw_path = url.removeprefix("{{rootUrl}}") if is_root else url
    host = "{{rootUrl}}" if is_root else "{{baseUrl}}"
    q = [{"key": k, "value": v, **({"disabled": True} if v == "" else {})} for k, v in (query or {}).items()]
    qs = "&".join(f"{x['key']}={x['value']}" for x in q if not x.get("disabled"))
    return {
        "raw": f"{host}{raw_path}" + (f"?{qs}" if qs else ""),
        "host": [host],
        "path": [p for p in raw_path.split("/") if p],
        **({"query": q} if q else {}),
    }


def item(r: dict, summaries: dict) -> dict:
    req: dict = {"method": r["method"], "header": [], "url": url_obj(r["url"], r.get("query"))}
    if "body" in r or "raw" in r:
        raw = r.get("raw") or json.dumps(r["body"], indent=2, ensure_ascii=False)
        req["header"].append({"key": "Content-Type", "value": "application/json"})
        req["body"] = {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}
    if "form" in r:
        req["body"] = {
            "mode": "formdata",
            "formdata": [
                {"key": k, "type": t, **({"src": v} if t == "file" else {"value": v})}
                for k, t, v in r["form"]
            ],
        }
    if r.get("auth") == "none":
        req["auth"] = {"type": "noauth"}
    desc = r.get("desc") or summaries.get((r["method"], r["path"])) or ""
    if desc:
        req["description"] = desc
    events = []
    if r.get("prerequest"):
        events.append(script("prerequest", r["prerequest"]))
    if r.get("tests"):
        events.append(script("test", r["tests"]))
    return {"name": r["name"], "event": events, "request": req}


FOLDER_DOCS = {
    "1. Auth": "Run **Login** first. It saves the token used by every admin request.",
    "14. Public website": "No login. These are the endpoints the user website calls.",
    "16. Cleanup (deletes test data)": "Deletes only the records this collection created (by saved id).",
}


def build() -> dict:
    schema = app.openapi()
    ops = {
        (m.upper(), p.removeprefix(PREFIX))
        for p, methods in schema["paths"].items()
        for m in methods
        if m in {"get", "post", "put", "patch", "delete"}
    }
    summaries = {
        (m.upper(), p.removeprefix(PREFIX)): op.get("summary", "")
        for p, methods in schema["paths"].items()
        for m, op in methods.items()
        if isinstance(op, dict)
    }
    covered = {(r["method"], r["path"]) for r in R}
    unknown = covered - ops
    missing = ops - covered
    if unknown or missing:
        for m, p in sorted(missing):
            print(f"MISSING from collection: {m} {p}", file=sys.stderr)
        for m, p in sorted(unknown):
            print(f"NOT IN API: {m} {p}", file=sys.stderr)
        raise SystemExit(1)

    folders: dict[str, list] = {}
    for r in R:
        folders.setdefault(r["folder"], []).append(item(r, summaries))
    variables = [
        "accessToken", "adminId", "runId", "month", "futureDate", "enquiryDate", "inviteEmail", "rootUrl",
        "settingsBody", "businessId", "hotelBusinessId", "businessBody", "bannerId", "categoryId",
        "categorySlug", "itemId", "cardId", "roomId", "roomSlug", "roomImageId", "hallBody", "packageId",
        "hallImageId", "bookingId", "uploadUrl", "uploadThumbUrl", "albumId", "albumSlug", "galleryImageId",
        "testimonialId", "faqId", "seoId", "seoPageKey", "userId", "enquiryId",
    ]  # fmt: skip
    readme = (ROOT / "postman" / "README.md").read_text() if (ROOT / "postman" / "README.md").exists() else ""
    return {
        "info": {
            "name": "Sreebhavan API",
            "_postman_id": "6c1f3f7e-6b7e-4d43-9a8e-5b1f2d1c9a01",
            "description": readme
            or "FastAPI backend for Sreebhavan Veg Hotel and Sreebhavanam. See postman/README.md.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "auth": {
            "type": "bearer",
            "bearer": [{"key": "token", "value": "{{accessToken}}", "type": "string"}],
        },
        "event": [script("prerequest", PRE), script("test", TEST)],
        "variable": [{"key": k, "value": "", "type": "string"} for k in variables],
        "item": [
            {
                "name": name,
                **({"description": FOLDER_DOCS[name]} if name in FOLDER_DOCS else {}),
                "item": items,
            }
            for name, items in folders.items()
        ],
    }


if __name__ == "__main__":
    collection = build()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(collection, indent=2, ensure_ascii=False) + "\n")
    n = sum(len(f["item"]) for f in collection["item"])
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(collection['item'])} folders, {n} requests")
