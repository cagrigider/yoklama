# Developer Profile

<!-- factory-version: 1.3.0 -->
> developer-agent tuning (stack/structure come from project-profile).
> Last updated: 2026-09-08

## Coding Style
- Python 3 with type hints (`from __future__ import annotations`); snake_case functions; `Path` for filesystem; parameterized SQL only
- Keep the server as stdlib (`http.server`, `sqlite3`, `json`, `pathlib`) — no pip for core paths, including roster import
- Product UI copy is Turkish; specs may be English — do not paste spec English onto the screen
- Externalize user-facing strings in the existing STATUS_TR / TAG_TR / JS label maps; prefer existing CSS tokens in `static/css/app.css`
- Calendar dates are ISO `YYYY-MM-DD` via `datetime.date`, never timestamps
- Document public HTTP paths next to the handler (no OpenAPI)

## Conventions
- New backend behavior goes in `app.py` (`Handler` + helpers) unless a split is required by an ADR
- New UI goes in `static/js/app.js`, `static/index.html`, `static/css/app.css` (hash routes `#/…`)
- Schema changes are additive only: `CREATE TABLE IF NOT EXISTS` or `ALTER TABLE … ADD COLUMN` — never DROP, never rebuild DB from seed
- Live attendance tick stays a single-row upsert (`PUT /api/meetings/{id}/attendance/{personId}`)
- File import is JSON body (text or base64), not multipart
- Decisions: `docs/adr/NNNN-short-title.md` using `.factory/adr_template.md`
- PII stays off git: never commit `data/*.db` or a real `seed/people.json`
- Standing rules: `.factory/ARCHITECTURAL_PRINCIPLES.md` (architect-owned)
