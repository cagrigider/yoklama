# Project Profile

<!-- factory-version: 1.3.0 -->
> Shared project facts. Read first by every dev-lane agent.
> Last updated: 2026-09-08

## Overview
- Name: Yoklama
- Type: app
- Platforms: backend, web
- Description: Local-only meeting attendance for one AI Champion and one group. Python 3 stdlib HTTP server plus a static Turkish SPA; SQLite on the operator’s machine. No login, no hosted service, no pip packages.

## Tech Stack
- Languages: python, javascript, html, css (small tree: one `app.py`, one SPA under `static/`)
- Frameworks: Python 3 standard library (`http.server.ThreadingHTTPServer`, `sqlite3`); vanilla JS hash-router SPA (no React/Vue)
- Build system / package manager: python3 (stdlib only; no pip, no `requirements.txt`, no `package.json`)
- Test frameworks: none yet — prefer pytest or unittest when tests are added

## Structure
- Apps:
  - yoklama → `.` (`python3 app.py`, type: web-app + backend; loopback `127.0.0.1:8765`)
- Modules:
  - static → `static/` (type: SPA assets — `index.html`, `css/app.css`, `js/app.js`)
  - data → `data/` (type: local SQLite; `attendance.db` gitignored)
  - seed → `seed/` (type: optional first roster; `people.json` gitignored, `people.example.json` tracked synthetic)

## Versioning
- File: TBD (no version field in the tree; no CHANGELOG yet)
- Format: TBD
- Strategy: single
- Keys: TBD (git tags on `main` until a version file is introduced)

## Learning History
- 2026-09-08 — initialize-agent: first `.factory/` profiles from detection (Python 3 stdlib + static SPA + SQLite). Architect memory and `plans/` / `test-plans/` left untouched.
- 2026-09-08 — unit-test-engineer: first suite is stdlib `unittest` under `tests/` (no pytest). Isolated temp SQLite via `tests/tempdb.py`; never `data/attendance.db`. Helpers under test: `fill_gap_meetings`, people write functions.
- 2026-09-09 — unit-test-engineer: TASK-1.1.2 `group_profile` suite. IsolatedDbTestCase schema includes additive `group_profile` singleton. Prefer helpers (`profile_meta`, `ensure_default_profile`, `upsert_group_profile`); PUT/GET profile contract uses in-process `127.0.0.1:0` Handler. Synthetic seed JSON only when asserting `seed_people` does not skip the wizard.
- 2026-09-09 — unit-test-engineer: TASK-1.2.1 Settings UI. No new Python — `tests/test_settings_ui.py` reads SPA sources and asserts `#settings-import` plus hash `#/settings`. PUT `/api/profile` and fill_gap stay in existing suites. No Playwright.
- 2026-09-09 — unit-tester: full suite `python3 -m unittest discover -s tests -v` → 32 passed / 0 failed (2.308s). Isolated temp SQLite only; `data/attendance.db` unused. New vs prior report: `SettingsUiHostTest` (TASK-1.2.1).
