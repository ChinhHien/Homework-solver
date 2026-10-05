from __future__ import annotations

from pathlib import Path

from homework_solver.ingest.docx import load_docx
from homework_solver.ingest.pdf import load_pdf
from homework_solver.ingest.types import AssignmentDocument


def load_assignment(path: Path) -> AssignmentDocument:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Assignment file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path)
    if suffix in {".docx"}:
        return load_docx(path)
    if suffix == ".doc":
        raise ValueError("Legacy .doc is not supported. Convert to .docx or .pdf.")
    raise ValueError(f"Unsupported file type: {suffix}. Use .pdf or .docx.")
