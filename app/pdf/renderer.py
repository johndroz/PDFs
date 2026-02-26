"""PDF rendering helpers using PyMuPDF."""

from __future__ import annotations

import fitz
from PySide6.QtGui import QImage


class PdfRenderError(RuntimeError):
    """Raised when a page cannot be rendered."""


def render_page_image(document: fitz.Document, page_index: int, zoom: float = 1.25) -> QImage:
    if page_index < 0 or page_index >= document.page_count:
        raise PdfRenderError(f"Page index out of range: {page_index}")

    try:
        page = document.load_page(page_index)
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False, annots=False)
    except Exception as exc:  # pragma: no cover - defensive for PyMuPDF errors
        raise PdfRenderError(f"Failed to render page {page_index + 1}") from exc

    image_format = QImage.Format_RGB888
    image = QImage(pix.samples, pix.width, pix.height, pix.stride, image_format)
    return image.copy()
