# ARCHITECTURAL PRINCIPLES — Yoklama

> Standing patterns, rules and conventions. Shared contract between the `architect` and the `developer`.
> Bootstrapped 2026-09-08. **Frozen after creation** — content changes only on an explicit user instruction.

## General engineering

1. **YAGNI.** Build what the acceptance criteria require. Do not add login, hosting, multi-group rollup, extra Python packages, or partner APIs.
2. **Single process, stdlib only.** The app is one Python 3 script plus static files. Runtime stays `python3 app.py` with the standard library. No pip dependency for core paths (including roster import).
3. **SQLite is the source of truth.** People, meetings, attendance, and group profile live in `data/attendance.db`. Do not introduce a second durable store for the same facts.
4. **Additive schema only.** Startup may `CREATE TABLE IF NOT EXISTS` or `ALTER TABLE … ADD COLUMN`. Never `DROP TABLE`, never rebuild the database from seed, never delete rows as a side effect of upgrade or series generation.
5. **Bind loopback only.** Listen on `127.0.0.1`. Do not add authentication. Do not become a network service.

## Data and privacy

6. **PII stays off git.** `data/*.db` and real `seed/people.json` remain gitignored. Example seed stays synthetic. Do not copy a real roster into the tracked tree.
7. **Fill-gaps never delete.** Series generation inserts a meeting only when that calendar date has none. Existing meetings and attendance are left unchanged, including when the end date is shortened.
8. **Foreign keys stay on.** `PRAGMA foreign_keys = ON`. Deleting a person cascades that person’s attendance only. Deleting a meeting cascades that meeting’s attendance only.
9. **Person identity is immutable.** `people.id` (sicil) does not change after insert. Wrong id → delete and add. Import upserts on that key and does not delete people absent from the file.

## UI and HTTP

10. **Product UI is Turkish.** Specs may be English; on-screen copy is not copied from the spec language. UTF-8 end to end.
11. **JSON HTTP + hash SPA.** New features follow the existing `/api/…` JSON handlers and `#/` client routes. File upload is JSON (text or base64), not a new multipart stack.
12. **One write, one row for live tick.** Attendance save remains a single-row upsert. Do not reload or rewrite the whole roster to persist one mark.

## Determinism and dates

13. **Calendar dates are dates, never instants.** Meeting dates, first date, and end date are ISO `YYYY-MM-DD` via `datetime.date`. Do not do series arithmetic on timestamps.
14. **All-or-nothing import.** Validate every row first; if any row lacks sicil/`id` or name, change no people.

## Documentation

15. **Decisions live in ADRs.** `docs/adr/NNNN-short-title.md`, MADR minimal, per `.factory/adr_template.md`.
