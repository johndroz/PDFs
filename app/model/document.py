"""Document model for source PDF metadata and handles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(slots=True)
class PdfDocument:
    path: Path
    handle: fitz.Document

    @property
    def page_count(self) -> int:
        return self.handle.page_count

    def close(self) -> None:
        if not self.handle.is_closed:
            self.handle.close()
