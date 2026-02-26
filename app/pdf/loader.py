"""PDF loading helpers."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile

import fitz

from app.model.document import PdfDocument


class PdfLoadError(RuntimeError):
    """Raised when a PDF cannot be opened."""


def load_pdf(path: str | Path) -> PdfDocument:
    source_path = Path(path)
    if not source_path.exists():
        raise PdfLoadError(f"File not found: {source_path}")

    fd, temp_path = tempfile.mkstemp(prefix=".pdf_work_", suffix=".pdf")
    os.close(fd)
    shutil.copy2(source_path, temp_path)

    try:
        handle = fitz.open(temp_path)
    except Exception as exc:  # pragma: no cover - defensive for PyMuPDF errors
        raise PdfLoadError(f"Failed to open PDF: {source_path}") from exc

    return PdfDocument(path=source_path, working_path=Path(temp_path), handle=handle)
