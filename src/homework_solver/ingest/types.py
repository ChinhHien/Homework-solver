from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EmbeddedImage:
    page: int
    mime: str
    data: bytes
    filename: str = "image"


@dataclass
class AssignmentPage:
    index: int
    text: str
    images: list[EmbeddedImage] = field(default_factory=list)


@dataclass
class AssignmentDocument:
    source_path: Path
    pages: list[AssignmentPage] = field(default_factory=list)
    extra_images: list[EmbeddedImage] = field(default_factory=list)

    @property
    def combined_text(self) -> str:
        chunks: list[str] = []
        for page in self.pages:
            header = f"--- Page {page.index} ---"
            body = page.text.strip()
            chunks.append(f"{header}\n{body}" if body else header)
        return "\n\n".join(chunks).strip()

    @property
    def all_images(self) -> list[EmbeddedImage]:
        images: list[EmbeddedImage] = []
        for page in self.pages:
            images.extend(page.images)
        images.extend(self.extra_images)
        return images
