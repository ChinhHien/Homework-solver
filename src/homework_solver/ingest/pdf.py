from __future__ import annotations

from pathlib import Path

import pymupdf

from homework_solver.ingest.normalize import normalize_images
from homework_solver.ingest.types import AssignmentDocument, AssignmentPage, EmbeddedImage

SPARSE_TEXT_CHARS = 80


def load_pdf(path: Path) -> AssignmentDocument:
    doc = pymupdf.open(path)
    pages: list[AssignmentPage] = []
    try:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            images: list[EmbeddedImage] = []
            for img_index, img in enumerate(page.get_images(full=True), start=1):
                xref = img[0]
                extracted = _pixmap_bytes(doc, xref)
                if extracted is None:
                    continue
                data, mime = extracted
                images.append(
                    EmbeddedImage(
                        page=i,
                        mime=mime,
                        data=data,
                        filename=f"p{i}_img{img_index}",
                    )
                )
            if len(text.strip()) < SPARSE_TEXT_CHARS:
                pix = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
                images.insert(
                    0,
                    EmbeddedImage(
                        page=i,
                        mime="image/png",
                        data=pix.tobytes("png"),
                        filename=f"p{i}_page",
                    ),
                )
            pages.append(
                AssignmentPage(
                    index=i,
                    text=text,
                    images=normalize_images(images),
                )
            )
    finally:
        doc.close()
    return AssignmentDocument(source_path=path, pages=pages)


def _pixmap_bytes(doc: pymupdf.Document, xref: int) -> tuple[bytes, str] | None:
    try:
        pix = pymupdf.Pixmap(doc, xref)
        if pix.n - pix.alpha > 3:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        if pix.alpha:
            pix = pymupdf.Pixmap(pix, 0)
        return pix.tobytes("png"), "image/png"
    except Exception:
        try:
            raw = doc.extract_image(xref)
            data = raw.get("image")
            ext = (raw.get("ext") or "png").lower()
            mime = "image/jpeg" if ext in {"jpg", "jpeg"} else f"image/{ext}"
            if data:
                return data, mime
        except Exception:
            return None
    return None
