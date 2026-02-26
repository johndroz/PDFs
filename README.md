# PDF Form Builder (Milestones 1-2)

Initial desktop scaffold for opening an existing PDF, rendering page previews, and navigating multi-page documents.

## Setup

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python -m app.main
```

## Implemented

- Project scaffolding under `app/`
- Open existing PDF via file picker
- Render PDF pages using PyMuPDF
- Navigate across all pages with list + Previous/Next actions

## Deferred

- Data validation logic
- Form element placement/editing
- PDF output writing pipeline
