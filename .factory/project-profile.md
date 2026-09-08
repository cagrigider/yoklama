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
