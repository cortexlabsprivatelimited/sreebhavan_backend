import io

from PIL import Image

from tests.conftest import API, data, error_fields


def png_bytes(w=2400, h=1200) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue()


async def upload(client, headers, folder, name, content, ctype):
    return await client.post(
        f"{API}/admin/uploads",
        data={"folder": folder},
        files={"file": (name, content, ctype)},
        headers=headers,
    )


async def test_image_is_resized_to_webp_with_thumbnail(client, seeded, supabase):
    r = await upload(client, seeded["staff"], "rooms", "room.png", png_bytes(), "image/png")
    assert r.status_code == 201, r.text
    body = data(r)
    assert body["url"].startswith("https://test.supabase.co/storage/v1/object/public/rooms/")
    assert body["url"].endswith(".webp") and body["thumb_url"].endswith("_thumb.webp")
    stored = {k: v for k, v in supabase.uploads.items()}
    full = Image.open(io.BytesIO(stored[body["url"].split("/public/")[1]][0]))
    thumb = Image.open(io.BytesIO(stored[body["thumb_url"].split("/public/")[1]][0]))
    assert full.format == "WEBP" and full.width == 1920 and full.height == 960
    assert thumb.width == 480


async def test_subfolder_goes_into_bucket_prefix(client, seeded, supabase):
    r = await upload(client, seeded["owner"], "menu/items", "dosa.png", png_bytes(100, 100), "image/png")
    assert "/public/menu/items/" in data(r)["url"]


async def test_pdf_only_for_menu_cards(client, seeded):
    pdf = b"%PDF-1.4\n%fake\n"
    r = await upload(client, seeded["owner"], "menu/cards", "menu.pdf", pdf, "application/pdf")
    assert r.status_code == 201 and data(r)["thumb_url"] is None and data(r)["url"].endswith(".pdf")
    r = await upload(client, seeded["owner"], "rooms", "menu.pdf", pdf, "application/pdf")
    assert r.status_code == 422


async def test_svg_only_for_logos_and_scripts_rejected(client, seeded):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="4"/></svg>'
    assert (await upload(client, seeded["owner"], "logos", "l.svg", svg, "image/svg+xml")).status_code == 201
    assert (
        await upload(client, seeded["owner"], "gallery", "l.svg", svg, "image/svg+xml")
    ).status_code == 422
    bad = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>'
    assert (await upload(client, seeded["owner"], "logos", "l.svg", bad, "image/svg+xml")).status_code == 422


async def test_real_type_checked_not_extension(client, seeded):
    r = await upload(
        client, seeded["owner"], "gallery", "photo.jpg", b"MZ\x90\x00 not an image", "image/jpeg"
    )
    assert r.status_code == 422
    assert error_fields(r)["file"].startswith("Upload a JPEG")


async def test_too_large_and_bad_folder(client, seeded):
    big = b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024 + 10)
    r = await upload(client, seeded["owner"], "gallery", "big.jpg", big, "image/jpeg")
    assert r.status_code == 422 and "larger than 5 MB" in error_fields(r)["file"]
    r = await upload(client, seeded["owner"], "secret", "a.png", png_bytes(10, 10), "image/png")
    assert r.status_code == 422


async def test_upload_requires_login(client, seeded):
    r = await upload(client, {}, "rooms", "a.png", png_bytes(10, 10), "image/png")
    assert r.status_code == 401
