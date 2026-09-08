# ARCHITECTURE — Yoklama

> Architect-owned working memory. Detailed technical landscape of this project.
> Not read by the `developer` (too wide) — the developer reads `ARCHITECTURAL_PRINCIPLES.md`.
> Last updated: 2026-09-09 (post-implementation review, PLAN-yoklama-setup — APPROVED)

## 1. Current landscape — local Python + SQLite + static UI

Yoklama is a single-user attendance app for one AI Champion and one group. There is no login and no hosted service. **yoklama-setup is implemented:** first-run wizard, Settings, weekly/biweekly/monthly fill-gaps, Excel/CSV/`people.json` import, and people CUD — all on the existing process.

| Dimension | State |
|-----------|--------|
| Language / runtime | Python 3, stdlib only (`http.server.ThreadingHTTPServer`, `sqlite3`, `json`, `csv`, `zipfile`, `xml.etree.ElementTree`, `pathlib`) |
| Bind | `127.0.0.1:8765` (`HOST` / `PORT` in `app.py`) |
| UI | Static SPA: `static/index.html`, `static/css/app.css`, `static/js/app.js` (hash router, Turkish copy) |
| Persistence | SQLite `data/attendance.db` (`CREATE TABLE IF NOT EXISTS`; `PRAGMA foreign_keys = ON`) |
| Seed | `seed/people.json` gitignored; loaded only when `people` is empty. Tracked example: `seed/people.example.json` (synthetic). `seed_meetings()` is a no-op |
| Distribution | Private GitHub `cagrigider/yoklama`. `.gitignore` omits `data/*.db`, `seed/people.json`, `*.xlsx`/`*.csv` |
| Tests | Stdlib `unittest` under `tests/` (`IsolatedDbTestCase` temp SQLite; never `data/attendance.db`). No pytest, no `requirements.txt` |

### 1.1 Schema

```
people (id PK TEXT, name, position, center, email)
meetings (id INTEGER PK, title, date TEXT ISO, kind, notes)
attendance (meeting_id, person_id, status, tags JSON, note)
  PK (meeting_id, person_id)
  ON DELETE CASCADE from meetings and people
group_profile (id INTEGER PK CHECK (id = 1), name, first_date, end_date, repeat_rule)
  SQLite singleton; configured ⇔ a row exists (ADR-0001)
```

Meetings have **no unique constraint on `date`**. Series uniqueness is “any meeting on that ISO date” (fill-gaps skip). Header brand is `#group-name` from `GET /api/meta` `groupName` (fallback `"Yoklama"`).

Operator upgrade: if no `group_profile` row and ≥1 meeting, `ensure_default_profile` inserts `name="Yoklama"`, `first_date` = earliest meeting date, `end_date` NULL, `repeat_rule='none'` **without** calling `fill_gap_meetings`. Wizard stays off. Empty clone (no profile, no meetings) → wizard even if `seed/people.json` filled people.

### 1.2 HTTP surface

| Method | Path | Role |
|--------|------|------|
| GET | `/api/meta` | today, statuses, tags, labels **plus** `configured`, `groupName`, optional `firstDate`/`endDate`/`repeatRule` |
| GET | `/api/people`, `/api/overview`, `/api/people/{id}/report` | roster read / history |
| GET | `/api/meetings`, `/roster`, `/report` | meetings + live roster |
| POST | `/api/meetings` | extra meeting (`kind=extra`) |
| PUT | `/api/meetings/{id}` | title/date/notes |
| DELETE | `/api/meetings/{id}` | meeting + cascaded attendance |
| PUT | `/api/meetings/{id}/attendance/{personId}` | **single-row** status/tags/note upsert (live tick) |
| POST | `/api/meetings/{id}/close` | unmarked → absent |
| GET | `/api/export` | dump people/meetings/attendance |
| PUT | `/api/profile` | GroupProfile singleton + `fill_gap_meetings` in **one** transaction (camelCase body) |
| POST | `/api/people/import` | Roster upsert; JSON `{filename, text}` or `{filename, contentBase64}` — not multipart |
| POST | `/api/people` | Add person; duplicate id → **409** (not upsert) |
| PUT | `/api/people/{id}` | Edit; id in path only |
| DELETE | `/api/people/{id}` | Person + cascaded attendance |

No `/api/setup`, no `/api/group`, no OpenAPI, no multipart. README documents the contract and that there is no alias.

SPA hashes: `#/` meetings, `#/meeting/:id` live tick, `#/people` list, `#/people/new` add, `#/people/:id` / `#/people/:id/edit`, `#/settings`. While `configured` is false, **every** hash renders the wizard only.

### 1.3 Data flow

```
Browser (127.0.0.1:8765)
  → static SPA (hash)
  → JSON /api/*
  → per-request sqlite3.connect(data/attendance.db)
```

```
  first-run / Settings  → GroupProfile singleton (ADR-0001)
                        → fill_gap_meetings (ADR-0003) → meetings INSERT missing dates only
                        → one SQLite commit (profile + series)
  optional file / Aktar → POST /api/people/import (ADR-0002) → people UPSERT (second transaction)
  people form           → POST/PUT/DELETE /api/people
  live tick             → attendance single-row UPSERT (unchanged)
```

Live tick: UI `save()` → one PUT → `reloadAndPaint()` of that meeting’s roster. JS input lock 500 ms. Position/center shown on the person row when present (FR-018).

Import never writes `group_profile` or meetings. A rejected wizard import leaves an already-committed profile and series in place.

---

## 2. Requirement — `yoklama-setup` (implemented)

Source: `docs/analysis/yoklama-setup/FRD-yoklama-setup.en.md` (+ BRD, diagrams, screens).
Feasibility: `.factory/plans/ARCHITECT_REVIEW-REQ-yoklama-setup.md` — **Approved-with-notes**.
Plan review: `.factory/plans/ARCHITECT_REVIEW-yoklama-setup.md` — **Approved**.
Post-implementation: `ARCHITECT_REVIEW.md` — **APPROVED** (2026-09-09).

Intent: other champions clone the repo, configure **their** group without editing Python, without receiving Grup 8 PII. Operator DB survives `git pull`.

In: wizard, Settings, series fill-gaps, Excel/CSV/`people.json` upsert, people CRUD, README column contract, keep live tick.
Out: hosted multi-user, login, other groups’ data, Teams auto-attendance, guests, managers as users.

### 2.1 Integration points

| Boundary | State | Notes |
|---------|--------|--------|
| Loopback HTTP | Keep | NFR-002 |
| SQLite file | Keep; `group_profile` additive | Upgrade insert when meetings exist |
| Git | Distribution; PII gitignored | db + `people.json` + spreadsheets |
| Excel/CSV/JSON files | Local only | ADR-0002; never commit |
| Partner APIs | None | ba-services skipped on purpose |
| Auth / bind address | Unchanged | `127.0.0.1`, no password |
| JSON setup routes | ADR-0004 as shipped | See §1.2 |

---

## 3. Technical decisions in force

| ADR | Decision |
|-----|----------|
| [0001](../docs/adr/0001-group-profile-in-sqlite.md) | GroupProfile is a SQLite singleton. Operator DBs with meetings get a default profile (no series). Wizard only when no profile and no meetings. |
| [0002](../docs/adr/0002-stdlib-roster-import.md) | CSV/JSON/xlsx via stdlib; JSON upload body; all-or-nothing then upsert by id. |
| [0003](../docs/adr/0003-series-fill-gaps-weekday.md) | Weekly +7 / biweekly +14 / monthly same weekday + week-of-month ordinal; never delete. One fill-gaps function for wizard and Settings. |
| [0004](../docs/adr/0004-json-setup-http-contract.md) | Pin QA harness as the JSON HTTP contract (`/api/meta`, `/api/profile`, `/api/people/import`, people CUD). |

No ADR-0005. Implementation did not introduce a new decision.

Public Python entry for series: `fill_gap_meetings(conn, first_date, end_date, repeat_rule)` — does not commit; `_put_profile` commits with `upsert_group_profile`. Generated series title is `"Toplantı"`.

---

## 4. Risks and constraints (live)

1. **FR-001 vs operator DB.** Closed in code: `ensure_default_profile` materializes a profile when meetings exist; wizard is off.
2. **Excel vs no pip.** Closed via ADR-0002; exotic workbooks fail closed to CSV (`exotic_xlsx`).
3. **NFR-001 (1 s save, ≤80 people).** Unchanged architecture: one UPSERT + roster reread. Still a manual/smoke check, not an automated timing gate.
4. **NFR-004.** `.gitignore` protects the DB; `seed_meetings` is a no-op; migrate is additive only. Hazard remains a future `DROP TABLE` or reseeding Grup 8 — do not add that.
5. **`seed/people.json`.** Present locally, gitignored. `seed_people()` still fills an empty people table. Does **not** skip the wizard (ADR-0001). Must not be committed.
6. **Duplicate dates.** Series uniqueness is “any meeting on that ISO date”, not a UNIQUE index (extras on the same date block a series insert — safe).
7. **NFR-003.** Wizard/Settings/people/import copy is Turkish (`WIZARD_COPY`, `SETTINGS_COPY`, `PEOPLE_COPY`, `IMPORT_COPY`).
8. **Wizard bypass.** `route()` gates on `meta.configured` before list/live/people/settings. Header tabs remain in the DOM but do not operate while unconfigured.
9. **Monolith.** Setup, import parsers, and live tick share `app.py` / `app.js`. Settings series form and `#settings-import` are separate DOM hosts / separate HTTP writes.
10. **xlsx XML.** Stdlib `ElementTree` without `defusedxml`; fail closed (ADR-0002). Loopback, champion-chosen files.
11. **Import column replace.** Upsert sets name/position/center/email from the file row (missing optional columns become `''` on that id). People absent from the file are not deleted.

---

## 5. Planning / development state (`yoklama-setup`)

- Requirement feasibility: **Approved-with-notes** (2026-09-08).
- Plan + test plan: `PLAN-yoklama-setup`, `TESTPLAN-yoklama-setup` — 39 cases, **46/46** ACs traced, verdict `complete`.
- Plan review: **Approved** (2026-09-08) — `.factory/plans/ARCHITECT_REVIEW-yoklama-setup.md`.
- Development: TASK-1.1.1, 1.2.3, 1.1.2, 1.2.1, 1.2.2 shipped (`a1225a6`…`a4ce3d4`).
- Post-implementation review: **APPROVED** (2026-09-09) — `ARCHITECT_REVIEW.md` at project root. No CHANGES REQUESTED. No new ADR.
