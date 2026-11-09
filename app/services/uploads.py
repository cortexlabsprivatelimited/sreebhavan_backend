"""Upload pipeline: check the real file type, resize, convert to WebP, make a thumbnail, store in Supabase."""

import asyncio
import io
import re
import uuid
from dataclasses import dataclass

from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import unprocessable
from app.core.supabase import SupabaseClient

Image.MAX_IMAGE_PIXELS = 50_000_000

# folder (API enum) -> Supabase bucket. Sub-folders become a path prefix inside the bucket.
BUCKETS = ("logos", "banners", "menu", "rooms", "hall", "gallery", "testimonials", "seo")
RASTER_FORMATS = {"JPEG", "PNG", "WEBP"}


def split_folder(folder: str) -> tuple[str, str]:
    bucket, _, prefix = folder.partition("/")
    return bucket, (prefix + "/" if prefix else "")


@dataclass
class Stored:
    url: str
    thumb_url: str | None


def sniff(content: bytes) -> str | None:
    """Returns 'pdf', 'ico', 'svg' or 'image' from the bytes themselves; None if unknown."""
    if content.startswith(b"%PDF-"):
        return "pdf"
    if content[:4] == b"\x00\x00\x01\x00":
        return "ico"
    head = content[:1024].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<?xml") or head.startswith(b"<svg"):
        if b"<svg" in content[:4096].lower():
            return "svg"
    if content[:3] == b"\xff\xd8\xff" or content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image"
    return None


_SVG_DANGER = re.compile(rb"<script|javascript:|\son[a-z]+\s*=|<foreignobject", re.IGNORECASE)


def _process_image(content: bytes, max_width: int, thumb_width: int, quality: int) -> tuple[bytes, bytes]:
    try:
        with Image.open(io.BytesIO(content)) as probe:
            fmt = probe.format
            probe.verify()
        if fmt not in RASTER_FORMATS:
            raise unprocessable("unsupported_file", "Upload a JPEG, PNG or WebP image.")
        img = Image.open(io.BytesIO(content))
        img = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise unprocessable("invalid_image", "This image could not be read. Try another file.") from exc

    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA" if has_alpha else "RGB")

    def encode(im: Image.Image, width: int) -> bytes:
        if im.width > width:
            h = round(im.height * width / im.width)
            im = im.resize((width, h), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=quality, method=4)
        return buf.getvalue()

    return encode(img, max_width), encode(img, thumb_width)


async def store_upload(
    supabase: SupabaseClient,
    folder: str,
    content: bytes,
    filename: str | None,
    user_token: str | None = None,
) -> Stored:
    """`user_token` is the signed-in admin's access token, used for Storage when no secret key is set."""
    settings = get_settings()
    if not content:
        raise unprocessable("empty_file", "The file is empty.")
    if len(content) > settings.upload_max_bytes:
        mb = settings.upload_max_bytes // (1024 * 1024)
        raise unprocessable("file_too_large", f"The file is larger than {mb} MB.")

    kind = sniff(content)
    bucket, prefix = split_folder(folder)
    key = uuid.uuid4().hex

    if kind == "pdf":
        if folder != "menu/cards":
            raise unprocessable("unsupported_file", "PDF files can only be uploaded as menu cards.")
        url = await supabase.upload(
            bucket, f"{prefix}{key}.pdf", content, "application/pdf", user_token=user_token
        )
        return Stored(url, None)

    if kind in ("svg", "ico"):
        if folder != "logos":
            raise unprocessable("unsupported_file", "SVG and ICO files can only be uploaded as logos.")
        if kind == "svg":
            if _SVG_DANGER.search(content):
                raise unprocessable("unsafe_svg", "This SVG contains scripts and cannot be uploaded.")
            url = await supabase.upload(
                bucket, f"{prefix}{key}.svg", content, "image/svg+xml", user_token=user_token
            )
        else:
            url = await supabase.upload(
                bucket, f"{prefix}{key}.ico", content, "image/x-icon", user_token=user_token
            )
        return Stored(url, None)

    if kind != "image":
        raise unprocessable(
            "unsupported_file",
            "Upload a JPEG, PNG or WebP image"
            + (", or a PDF" if folder == "menu/cards" else "")
            + (", SVG or ICO" if folder == "logos" else "")
            + ".",
        )

    full, thumb = await run_in_threadpool(
        _process_image, content, settings.image_max_width, settings.thumb_width, settings.webp_quality
    )
    # Both files go to Storage at the same time: the admin waits for one round trip, not two.
    url, thumb_url = await asyncio.gather(
        supabase.upload(bucket, f"{prefix}{key}.webp", full, "image/webp", user_token=user_token),
        supabase.upload(bucket, f"{prefix}{key}_thumb.webp", thumb, "image/webp", user_token=user_token),
    )
    return Stored(url, thumb_url)
