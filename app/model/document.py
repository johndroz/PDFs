"""Document model for source PDF metadata and handles."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

import fitz


@dataclass(slots=True)
class PdfDocument:
    path: Path
    working_path: Path
    handle: fitz.Document

    @property
    def page_count(self) -> int:
        return self.handle.page_count

    def close_handle(self) -> None:
        if not self.handle.is_closed:
            self.handle.close()

    def reopen_handle(self) -> None:
        if self.handle.is_closed:
            self.handle = fitz.open(self.working_path)

    def close(self) -> None:
        self.close_handle()
        if self.working_path != self.path and self.working_path.exists():
            try:
                os.remove(self.working_path)
            except OSError:
                pass
