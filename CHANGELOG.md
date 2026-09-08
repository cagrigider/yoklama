# Changelog

All notable changes to Yoklama are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

This project has no version file yet. Sprint work is recorded under `[Unreleased]`; `/factory:integrate` does not bump versions.

## [Unreleased]

### Added

- Local-only Turkish attendance app on loopback (`127.0.0.1`): Python 3 stdlib HTTP, SQLite, and a hash-router SPA, shared without group roster data or `attendance.db`.
- First-run wizard that saves a singleton group profile (name, first date, optional end date, repeat) and generates series meetings in one transaction.
- Default group profile on startup when meetings already exist, so an operator database skips the wizard and is not wiped.
- Series fill-gaps for none, weekly, biweekly, and monthly weekday rules; existing extra meetings and attendance marks are never deleted.
- People add, edit, and delete (sicil stays immutable on edit; delete cascades attendance; duplicate add returns 409).
- Settings (`#/settings` / Ayarlar) to update group name and series without rewriting live tick; saved group name appears in the topbar and meeting list.
- Roster import from simple Excel, CSV, or `people.json` (stdlib parsers, no pip): all-or-nothing validation, upsert by sicil, people missing from the file are kept. Optional file picker after the wizard; Aktar on Settings.
- Isolated `unittest` suite on a temp SQLite file (never `data/attendance.db`).
- Isolated Playwright suite under `webui/` (chromium, headless): copies the tree to `/tmp` and binds `127.0.0.1:18765` so operator data and real `seed/people.json` are never used. Covers wizard, empty roster, Settings, people, import, and live tick.
- Post-implementation architect review (`ARCHITECT_REVIEW.md`, APPROVED) and security scan (`SECURITYREPORT.md`, no Critical/High) for the yoklama-setup sprint.

### Changed

- `GET /api/meta` now includes `configured`, `groupName`, and series fields. There is no `/api/setup` alias.
- SPA `api()` shows the server’s Turkish `message` instead of English error codes.
- Roster import rejects macros, extra header rows, encrypted workbooks, and decode errors as HTTP 400 with Turkish copy.
- IEEE 829 yoklama-setup test plan back-annotated with Playwright `automated.spec`.

### Fixed

- CSV/JSON decode and parse failures return 400 `invalid_file` instead of an unhandled 500.
