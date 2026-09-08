# Reviewer Profile

<!-- factory-version: 1.3.0 -->
> reviewer-agent tuning.
> Last updated: 2026-09-09

## Project Review Context
- Yoklama is a single-user local attendance app. Review for YAGNI (no login, hosting, extra packages), loopback bind, additive SQLite, Turkish UI, and PII staying off git. Incoming work: shareable group setup (wizard, Settings, series fill-gaps, roster import, people CRUD) without touching the operator’s existing DB on `git pull`.

## Focus Areas
- Python stdlib HTTP handler correctness (status codes, JSON body, no new framework)
- SQLite: parameterized queries, `PRAGMA foreign_keys = ON`, additive schema only, fill-gaps never deletes
- Vanilla JS SPA: hash routing, live tick one-write-one-row, 500 ms input lock, no new SPA framework
- Product copy in Turkish; UTF-8 end to end
- Import all-or-nothing validation; person `id` (sicil) immutable after insert
- Bind remains `127.0.0.1` (not `0.0.0.0`)
- Do not introduce pip dependencies or `requirements.txt` for core paths
- JSON write handlers: require a JSON object (`isinstance(body, dict)`) and respond 400 `invalid_json` otherwise — do not call `.get` on arrays or `null`; coerce scalars with `str(...)` before `.strip()`
- Unit tests isolate SQLite via temp files; never open, migrate, or wipe `data/attendance.db`
- First-run: while `GET /api/meta.configured` is false, every hash must render the wizard only (no list/live/people/settings); that intercept must stay *before* feature routes
- Settings/header tasks: hunks in `bindPersonRow`, `renderLive`, or attendance PUT are CRITICAL (live tick must stay one-write-one-row)
- Hash-router views must not `await` a second fetch after `route()`'s `viewSeq` check without re-checking `seq` (or `location.hash`) before writing `$app.innerHTML` — a stale Settings paint can clobber live tick (`#roster` missing, `stillHere()` no-ops)
- ADR-0001 upgrade insert (`ensure_default_profile`) must not call `fill_gap_meetings`; `PUT /api/profile` persists `group_profile` + fill-gaps in one transaction and rolls back on `SeriesError`

## Flags
- Performance-critical: false
- Accessibility-required: false
