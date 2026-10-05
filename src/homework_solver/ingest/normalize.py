from __future__ import annotations

from io import BytesIO

from PIL import Image

from homework_solver.ingest.types import EmbeddedImage

MIN_PIXELS = 40
MAX_SIDE = 1280
MAX_IMAGES = 24
JPEG_QUALITY = 80


def should_keep_image(data: bytes) -> bool:
    try:
        with Image.open(BytesIO(data)) as img:
            w, h = img.size
            return w >= MIN_PIXELS and h >= MIN_PIXELS
    except Exception:
        return len(data) >= 2048


def compress_image(data: bytes, mime: str) -> tuple[bytes, str]:
    try:
        with Image.open(BytesIO(data)) as img:
            img = img.convert("RGB")
            w, h = img.size
            scale = min(1.0, MAX_SIDE / max(w, h))
            if scale < 1.0:
                img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return buf.getvalue(), "image/jpeg"
    except Exception:
        return data, mime


def normalize_images(images: list[EmbeddedImage]) -> list[EmbeddedImage]:
    kept: list[EmbeddedImage] = []
    for image in images:
        if not should_keep_image(image.data):
            continue
        data, mime = compress_image(image.data, image.mime)
        kept.append(
            EmbeddedImage(
                page=image.page,
                mime=mime,
                data=data,
                filename=image.filename,
            )
        )
        if len(kept) >= MAX_IMAGES:
            break
    return kept
