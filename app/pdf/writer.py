"""PDF form field writer using reportlab overlay widgets + pypdf."""

from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, BooleanObject, DictionaryObject, NameObject, NumberObject
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from app.model.field import FieldType, FormField


class PdfWriteError(RuntimeError):
    """Raised when output generation fails."""


def write_pdf_with_fields(
    source_path: str | Path,
    output_path: str | Path,
    fields: list[FormField],
) -> None:
    source = Path(source_path)
    output = Path(output_path)

    try:
        reader = PdfReader(str(source))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        _strip_existing_form_widgets(writer)

        if fields:
            overlay_pdf = _build_overlay_pdf(reader, fields)
            overlay_reader = PdfReader(overlay_pdf)
            pages_with_fields = {field.page_index for field in fields}
            _transfer_widget_annotations(overlay_reader, writer, pages_with_fields)

            _hide_widget_borders(writer)

        with output.open("wb") as handle:
            writer.write(handle)
    except Exception as exc:
        raise PdfWriteError(f"Failed to write output PDF: {output}") from exc


def _strip_existing_form_widgets(writer: PdfWriter) -> None:
    for page in writer.pages:
        annots = page.get("/Annots")
        if not annots:
            continue

        kept = ArrayObject()
        for annot_ref in annots:
            annot = annot_ref.get_object()
            if annot.get("/Subtype") == "/Widget":
                continue
            kept.append(annot_ref)

        if kept:
            page[NameObject("/Annots")] = kept
        elif "/Annots" in page:
            del page["/Annots"]

    if "/AcroForm" in writer._root_object:
        del writer._root_object["/AcroForm"]


def _hide_widget_borders(writer: PdfWriter) -> None:
    zero_border = ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0)])
    for page in writer.pages:
        annots = page.get("/Annots")
        if not annots:
            continue
        for annot_ref in annots:
            annot = annot_ref.get_object()
            if annot.get("/Subtype") != "/Widget":
                continue
            annot[NameObject("/Border")] = zero_border


def _transfer_widget_annotations(
    overlay_reader: PdfReader,
    writer: PdfWriter,
    pages_with_fields: set[int],
) -> None:
    field_refs = ArrayObject()

    for page_index in pages_with_fields:
        source_page = overlay_reader.pages[page_index]
        target_page = writer.pages[page_index]
        source_annots = source_page.get("/Annots") or []
        target_annots_obj = target_page.get("/Annots")
        if target_annots_obj is None:
            target_annots = ArrayObject()
        else:
            target_annots = target_annots_obj.get_object()

        for annot_ref in source_annots:
            annot = annot_ref.get_object()
            if annot.get("/Subtype") != "/Widget":
                continue

            cloned_ref = annot.clone(writer)
            cloned_annot = cloned_ref.get_object()
            if getattr(target_page, "indirect_reference", None) is not None:
                cloned_annot[NameObject("/P")] = target_page.indirect_reference
            _clear_widget_background(cloned_annot)

            target_annots.append(cloned_ref)
            field_refs.append(cloned_ref)

        target_page[NameObject("/Annots")] = target_annots

    acroform = DictionaryObject(
        {
            NameObject("/Fields"): field_refs,
            NameObject("/NeedAppearances"): BooleanObject(True),
        }
    )
    writer._root_object[NameObject("/AcroForm")] = writer._add_object(acroform)


def _build_overlay_pdf(reader: PdfReader, fields: list[FormField]) -> BytesIO:
    grouped: dict[int, list[FormField]] = defaultdict(list)
    for field in fields:
        grouped[field.page_index].append(field)

    buffer = BytesIO()

    first_page = reader.pages[0]
    base_w = float(first_page.mediabox.width)
    base_h = float(first_page.mediabox.height)
    report = canvas.Canvas(buffer, pagesize=(base_w, base_h))

    for page_index, page in enumerate(reader.pages):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        report.setPageSize((width, height))

        for field in grouped.get(page_index, []):
            if field.field_type is FieldType.TEXT:
                report.acroForm.textfield(
                    name=field.name,
                    x=field.x,
                    y=field.y,
                    width=field.width,
                    height=field.height,
                    value=field.default_value,
                    forceBorder=False,
                    borderWidth=0,
                    fillColor=None,
                    borderColor=None,
                    textColor=colors.black,
                )
            else:
                size = min(field.width, field.height)
                report.acroForm.checkbox(
                    name=field.name,
                    x=field.x,
                    y=field.y,
                    size=size,
                    checked=field.checked,
                    buttonStyle="check",
                    borderWidth=0,
                    fillColor=None,
                    borderColor=None,
                )

        report.showPage()

    report.save()
    buffer.seek(0)
    return buffer


def _clear_widget_background(widget_annot: DictionaryObject) -> None:
    mk = widget_annot.get("/MK")
    if mk is None:
        return
    mk_dict = mk.get_object()
    if "/BG" in mk_dict:
        del mk_dict["/BG"]
