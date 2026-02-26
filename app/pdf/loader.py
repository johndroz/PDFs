"""PDF loading helpers."""

from __future__ import annotations

from pathlib import Path

import fitz

from app.model.document import PdfDocument


class PdfLoadError(RuntimeError):
    """Raised when a PDF cannot be opened."""


def load_pdf(path: str | Path) -> PdfDocument:
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise PdfLoadError(f"File not found: {pdf_path}")

    try:
        handle = fitz.open(pdf_path)
    except Exception as exc:  # pragma: no cover - defensive for PyMuPDF errors
        raise PdfLoadError(f"Failed to open PDF: {pdf_path}") from exc

    return PdfDocument(path=pdf_path, handle=handle)
