# 0002 — Stdlib-only Excel/CSV/JSON roster import

- **Status:** accepted
- **Date:** 2026-09-08
- **Deciders:** architect (requirement-feasibility review, yoklama-setup)

## Context and Problem Statement

FR-009 requires Excel, CSV, and `people.json` import. The running app and README are stdlib-only (`python3 app.py`, no pip). Adding `openpyxl` would break that contract and can fail on locked-down machines. `BaseHTTPRequestHandler` has no multipart parser.

## Considered Options

- Add `openpyxl` (or pandas) as a runtime dependency
- CSV/JSON only; tell champions to “Save as CSV” from Excel (rejects FR-009 as written)
- **Stdlib parsers:** `csv` + `json` + first-sheet `.xlsx` via `zipfile` + `xml.etree.ElementTree`; client sends JSON

## Decision Outcome

Chosen option: **stdlib parsers + JSON upload body**, because it keeps the existing run command and still accepts `.xlsx`.

- CSV: `csv` module, UTF-8 (BOM tolerated).
- JSON: existing `people.json` array shape; `id` or `sicil` + `name`; optional `position`, `center`/`yetkinlik`, `email`.
- XLSX: first worksheet only; shared strings and inline strings; numeric sicil coerced to a string without a trailing `.0`. Exotic workbooks (macros, multiple header rows, password) → reject the whole file with an error that says to save as CSV (FR-010 all-or-nothing).
- Transport: the SPA reads the file and `POST`s JSON `{ "filename", "text" }` or `{ "filename", "contentBase64" }`. No multipart library.
- Upsert by `people.id`; do not delete people missing from the file. Validate all rows before any write.

## Consequences

- Positive: no pip; one HTTP style; README “Python 3 is enough” stays true.
- Negative / accepted cost: not a full Excel engine; complex sheets fail closed to CSV.
- Follow-up: README lists required columns (FR-016) and that Excel means a simple first sheet.
