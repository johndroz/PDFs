"""In-memory session state for placed fields."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.model.field import FormField


@dataclass(slots=True)
class DocumentSession:
    fields_by_page: dict[int, list[FormField]] = field(default_factory=dict)

    def get_page_fields(self, page_index: int) -> list[FormField]:
        return self.fields_by_page.get(page_index, [])

    def all_fields(self) -> list[FormField]:
        merged: list[FormField] = []
        for page_fields in self.fields_by_page.values():
            merged.extend(page_fields)
        return merged
