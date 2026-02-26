# PDF Form Builder Desktop App Plan

## Objective
Build a Python desktop application that opens existing PDFs and lets users add editable form fields (text inputs and checkboxes) across multiple pages using visual placement with manual adjustments.

## Scope for V1
- Open and display existing PDF files.
- Navigate across all PDF pages.
- Add form elements:
  - Text field
  - Checkbox
- Visual placement:
  - Click-to-place on page preview
  - Drag to reposition
- Manual precision controls:
  - X/Y position inputs
  - Width/height inputs (for text fields)
- Field properties:
  - Name (required, unique)
  - Required flag
  - Default value (text) / checked state (checkbox, default unchecked)
- Save output as a new PDF with real editable AcroForm fields.

## Recommended Tech Stack
- GUI: `PySide6` (Qt)
- PDF rendering for preview: `PyMuPDF` (`fitz`)
- PDF writing/form field creation: `reportlab` + `pypdf`
- Optional data model validation: `pydantic` (can defer)

## Architecture
- `app/`
  - `main.py` - app entry point
  - `ui/` - main window, toolbar, side panels
  - `viewer/` - page canvas, zoom/pan, selection, drag/resize
  - `model/` - in-memory form-field definitions per page
  - `pdf/`
    - `loader.py` - open/read source PDF metadata
    - `renderer.py` - render page previews
    - `writer.py` - build overlay + merge fields into output PDF
  - `state/` - document/session state and undo-redo actions

## Workflow Design
1. User opens PDF.
2. User selects a page.
3. User chooses field type (text/checkbox).
4. User clicks preview to place field.
5. User fine-tunes via drag and/or numeric controls.
6. User edits field properties in side panel.
7. User saves as new PDF.

## Coordinate Strategy
- Store field coordinates in PDF points (not pixels).
- Convert between preview pixels and PDF points using current zoom + page transform.
- Ensure consistent placement regardless of display zoom level.

## Multi-Page Support
- Page navigator (thumbnail or list).
- Independent field collections per page.
- Save routine iterates through all pages and applies overlays where fields exist.

## Output Generation Strategy
- For each page with fields:
  - Create ReportLab overlay with AcroForm fields at target coordinates.
  - Merge overlay onto the corresponding source page via `pypdf`.
- Preserve untouched pages exactly as-is.
- Write a new output file path to avoid overwriting source by default.

## Validation Rules
- Field names must be unique across entire document.
- Coordinates must remain within page bounds.
- Text fields require minimum width/height.
- Block save when validation fails and show actionable errors.

## Milestones
1. Project scaffolding + dependency setup.
2. PDF open/render + multi-page navigation.
3. Canvas interaction (place/select/move).
4. Side panel property editor + validation.
5. PDF field writing pipeline (text + checkbox).
6. End-to-end save testing on sample multi-page PDFs.
7. Packaging (optional after V1 stabilization).

## Testing Plan
- Unit tests:
  - Coordinate transform math
  - Field schema validation
  - Name uniqueness checks
- Integration tests:
  - Generate output PDF and verify fields exist (using `pypdf` inspection)
  - Multi-page placement correctness
- Manual QA:
  - Open in Adobe Acrobat Reader and confirm fields are editable
  - Confirm newly added checkboxes open unchecked by default in common viewers
  - Verify checkbox behavior and required flags

## Risks and Mitigations
- PDF viewer rendering differences:
  - Test output in Adobe Reader and at least one alternative viewer.
- Coordinate mismatch between preview and output:
  - Add debug mode to visualize bounds and exported coordinates.
- Complex source PDFs (rotations/crop boxes):
  - Normalize page box and account for rotation during transform.

## Immediate Next Step
Create the initial project skeleton and implement Milestone 1-2 (open PDF, render pages, and navigate multi-page documents).
