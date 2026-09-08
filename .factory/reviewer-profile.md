# Reviewer Profile

<!-- factory-version: 1.3.0 -->
> reviewer-agent tuning.
> Last updated: 2026-09-08

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

## Flags
- Performance-critical: false
- Accessibility-required: false
