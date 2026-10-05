from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from homework_solver.ingest.normalize import normalize_images
from homework_solver.ingest.types import AssignmentDocument, AssignmentPage, EmbeddedImage


def load_docx(path: Path) -> AssignmentDocument:
    doc = Document(str(path))
    text_parts: list[str] = []
    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            if block.text.strip():
                text_parts.append(block.text)
        elif isinstance(block, Table):
            text_parts.append(_table_to_text(block))

    images: list[EmbeddedImage] = []
    for idx, rel in enumerate(doc.part.rels.values(), start=1):
        reltype = getattr(rel, "reltype", "") or ""
        if "image" not in reltype:
            continue
        try:
            blob = rel.target_part.blob
            content_type = rel.target_part.content_type or "image/png"
        except Exception:
            continue
        images.append(
            EmbeddedImage(
                page=1,
                mime=content_type,
                data=blob,
                filename=f"docx_img{idx}",
            )
        )

    page = AssignmentPage(
        index=1,
        text="\n".join(text_parts),
        images=normalize_images(images),
    )
    return AssignmentDocument(source_path=path, pages=[page])


def _iter_block_items(parent):
    body = parent.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def _table_to_text(table: Table) -> str:
    rows: list[str] = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)
