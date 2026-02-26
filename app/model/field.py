"""Form field model definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FieldType(str, Enum):
    TEXT = "text"
    CHECKBOX = "checkbox"


@dataclass(slots=True)
class FormField:
    page_index: int
    name: str
    field_type: FieldType
    x: float
    y: float
    width: float
    height: float
    required: bool = False
    default_value: str = ""
    checked: bool = False
