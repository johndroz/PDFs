"""Import existing AcroForm fields from a PDF into in-memory models."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from app.model.field import FieldType, FormField


class PdfImportError(RuntimeError):
    """Raised when existing form fields cannot be imported."""


def import_pdf_fields(source_path: str | Path) -> list[FormField]:
    source = Path(source_path)
    imported: list[FormField] = []

    try:
        reader = PdfReader(str(source))
        for page_index, page in enumerate(reader.pages):
            annots = page.get("/Annots") or []
            for annot_ref in annots:
                annot = annot_ref.get_object()
                if annot.get("/Subtype") != "/Widget":
                    continue

                parent = annot.get("/Parent")
                parent_obj = parent.get_object() if parent is not None else None

                field_type = annot.get("/FT") or (parent_obj.get("/FT") if parent_obj else None)
                rect = annot.get("/Rect")
                if field_type is None or rect is None:
                    continue

                llx = float(rect[0])
                lly = float(rect[1])
                urx = float(rect[2])
                ury = float(rect[3])
                width = max(0.0, urx - llx)
                height = max(0.0, ury - lly)

                name = str(annot.get("/T") or (parent_obj.get("/T") if parent_obj else "") or "")
                flags = annot.get("/Ff")
                if flags is None and parent_obj is not None:
                    flags = parent_obj.get("/Ff")
                required = bool(int(flags or 0) & 2)

                if field_type == "/Tx":
                    text_value = annot.get("/V")
                    if text_value is None and parent_obj is not None:
                        text_value = parent_obj.get("/V")
                    default_value = str(text_value or "")
                    imported.append(
                        FormField(
                            page_index=page_index,
                            name=name,
                            field_type=FieldType.TEXT,
                            x=llx,
                            y=lly,
                            width=width,
                            height=height,
                            required=required,
                            default_value=default_value,
                        )
                    )
                elif field_type == "/Btn":
                    value_obj = annot.get("/V")
                    if value_obj is None and parent_obj is not None:
                        value_obj = parent_obj.get("/V")
                    value = str(value_obj or "")
                    appearance = str(annot.get("/AS") or "")
                    checked = value not in {"", "/Off", "Off"} or appearance not in {
                        "",
                        "/Off",
                        "Off",
                    }
                    imported.append(
                        FormField(
                            page_index=page_index,
                            name=name,
                            field_type=FieldType.CHECKBOX,
                            x=llx,
                            y=lly,
                            width=width,
                            height=height,
                            required=required,
                            checked=checked,
                        )
                    )
    except Exception as exc:
        raise PdfImportError(f"Failed to import form fields from: {source}") from exc

    return imported
