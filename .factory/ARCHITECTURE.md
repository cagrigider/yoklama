# ARCHITECTURE — Yoklama

> Architect-owned working memory. Detailed technical landscape of this project.
> Not read by the `developer` (too wide) — the developer reads `ARCHITECTURAL_PRINCIPLES.md`.
> Last updated: 2026-09-08 (plan-review revision, `yoklama-setup` — Approved)

## 1. Current landscape — local Python + SQLite + static UI

Yoklama is an existing single-user attendance app for one AI Champion and one group. There is no login and no hosted service.

| Dimension | State |
|-----------|--------|
| Language / runtime | Python 3, stdlib only (`http.server.ThreadingHTTPServer`, `sqlite3`, `json`, `pathlib`) |
| Bind | `127.0.0.1:8765` (`HOST` / `PORT` in `app.py`) |
| UI | Static SPA: `static/index.html`, `static/css/app.css`, `static/js/app.js` (hash router, Turkish copy) |
| Persistence | SQLite `data/attendance.db` (`CREATE TABLE IF NOT EXISTS`; `PRAGMA foreign_keys = ON`) |
| Seed | `seed/people.json` gitignored; loaded only when `people` is empty. Tracked example: `seed/people.example.json` (synthetic). `seed_meetings()` is a no-op |
| Distribution | Private GitHub `cagrigider/yoklama`. `.gitignore` omits `data/*.db`, `seed/people.json`, `*.xlsx`/`*.csv` |
| Tests / packages | No test framework, no `requirements.txt` |

### 1.1 Schema (as shipped)

```
people (id PK TEXT, name, position, center, email)
meetings (id INTEGER PK, title, date TEXT ISO, kind, notes)
attendance (meeting_id, person_id, status, tags JSON, note)
  PK (meeting_id, person_id)
  ON DELETE CASCADE from meetings and people
```

There is **no** `group_profile` table yet. Header brand is hardcoded “Yoklama”. Meetings have **no unique constraint on `date`**.

### 1.2 HTTP surface (as shipped)

| Method | Path | Role |
|--------|------|------|
| GET | `/api/meta` | today, statuses, tags, labels |
| GET | `/api/people`, `/api/overview`, `/api/people/{id}/report` | roster read / history |
| GET | `/api/meetings`, `/roster`, `/report` | meetings + live roster |
| POST | `/api/meetings` | extra meeting (`kind=extra`) |
| PUT | `/api/meetings/{id}` | title/date/notes |
| DELETE | `/api/meetings/{id}` | meeting + cascaded attendance |
| PUT | `/api/meetings/{id}/attendance/{personId}` | **single-row** status/tags/note upsert |
| POST | `/api/meetings/{id}/close` | unmarked → absent |
| GET | `/api/export` | dump people/meetings/attendance |

**Missing vs yoklama-setup:** group profile GET/PUT, series fill-gaps, roster import, people POST/PUT/DELETE. People list UI is read-only (`#/people`). Live tick, tags, notes, copyable summaries already exist (FR-017).

### 1.3 Data flow

```
Browser (127.0.0.1:8765)
  → static SPA (hash: / , /meeting/:id , /people , /people/:id)
  → JSON /api/*
  → per-request sqlite3.connect(data/attendance.db)
```

Live tick: UI `save()` → one PUT → `reloadAndPaint()` of that meeting’s roster. JS input lock 500 ms. Position/center already shown on the person row when present (FR-018).

## 2. Incoming requirement — `yoklama-setup`

Source: `docs/analysis/yoklama-setup/FRD-yoklama-setup.en.md` (+ BRD, diagrams, screens).
Review: `.factory/plans/ARCHITECT_REVIEW-REQ-yoklama-setup.md` — **Approved-with-notes**.

Intent: other champions clone the repo, configure **their** group without editing Python, without receiving Grup 8 PII. Operator DB survives `git pull`.

In: wizard, Settings, series fill-gaps, Excel/CSV/`people.json` upsert, people CRUD, README column contract, keep live tick.
Out: hosted multi-user, login, other groups’ data, Teams auto-attendance, guests, managers as users.

### 2.1 Target component shape

```
  first-run / Settings  → GroupProfile (SQLite singleton, ADR-0001)
                        → series fill-gaps (ADR-0003) → meetings INSERT missing dates only
  file / people form    → import validator (ADR-0002) → people UPSERT / CRUD
  live tick (unchanged) → attendance single-row UPSERT
```

SPA gains a **blocking** first-run surface (`#/setup` or overlay) and `#/settings`. Unconfigured chrome must not leave Toplantılar / Kişiler live (shipped `index.html` always shows those tabs today). Header `strong` shows `group_profile.name` when set (FR-019). HTTP contract is ADR-0004.

### 2.2 Integration points

| Boundary | State | Notes |
|---------|--------|--------|
| Loopback HTTP | Keep | NFR-002 |
| SQLite file | Keep; add `group_profile` | Additive migrate only |
| Git | Distribution; PII gitignored | Already true for db + `people.json` |
| Excel/CSV/JSON files | New, local only | ADR-0002; never commit |
| Partner APIs | None | ba-services skipped on purpose |
| Auth / bind address | Unchanged | `127.0.0.1`, no password |
| JSON setup routes | ADR-0004 | `GET /api/meta` += `configured`,`groupName`; `PUT /api/profile`; `POST /api/people/import`; people POST/PUT/DELETE |

## 3. Technical decisions in force

| ADR | Decision |
|-----|----------|
| [0001](../docs/adr/0001-group-profile-in-sqlite.md) | GroupProfile is a SQLite singleton. Operator DBs with meetings get a default profile (no series). Wizard only when no profile and no meetings. |
| [0002](../docs/adr/0002-stdlib-roster-import.md) | CSV/JSON/xlsx via stdlib; JSON upload body; all-or-nothing then upsert by id. |
| [0003](../docs/adr/0003-series-fill-gaps-weekday.md) | Weekly +7 / biweekly +14 / monthly same weekday + week-of-month ordinal; never delete. One fill-gaps function for wizard and Settings. |
| [0004](../docs/adr/0004-json-setup-http-contract.md) | Pin QA harness as the JSON HTTP contract (`/api/meta`, `/api/profile`, `/api/people/import`, people CUD). |

## 4. Risks and constraints (live)

1. **FR-001 vs operator DB.** Literal “no group profile → wizard” would hit the operator after upgrade. ADR-0001 materializes a profile when meetings exist.
2. **Excel vs no pip.** Solved by ADR-0002; exotic workbooks fail closed to CSV.
3. **NFR-001 (1 s save, ≤80 people).** Already the architecture: one UPSERT + roster reread. Realistic. No automated timing case in BA tests — keep as a manual/smoke check.
4. **NFR-004.** `.gitignore` already protects the DB; `seed_meetings` is a no-op. Hazard is a future `DROP TABLE` or reseeding Grup 8. Additive migrate only.
5. **`seed/people.json`.** Present locally, gitignored, not tracked. `seed_people()` still fills an empty people table. Must not skip the wizard (ADR-0001). Must not be committed.
6. **Duplicate dates.** Series uniqueness is “any meeting on that ISO date”, not a UNIQUE index (extras can share a date with a series row and will block insert — safe).
7. **NFR-003.** New wizard/Settings/people copy must be Turkish; BA screens.md is English.
8. **Wizard bypass.** Shipped header always links Toplantılar and Kişiler. First-run is the only reachable surface until a profile row exists (TASK-1.1.2#AC13; plan-review F-1 closed).
9. **Monolith parallelism.** Wave 3 SS (Settings ‖ import) shares `app.py` / `app.js`. Settings leaves empty `#settings-import`; import fills that host only (TASK-1.2.1#AC8 / TASK-1.2.2#AC8; plan-review F-4 closed).
10. **xlsx XML.** Stdlib `ElementTree` without resolving external entities; fail closed (ADR-0002). No `defusedxml` package.

## 5. Planning-lane state (`yoklama-setup`)

- Requirement feasibility: **Approved-with-notes** (2026-09-08).
- Plan + test plan: `PLAN-yoklama-setup`, `TESTPLAN-yoklama-setup` — 39 cases, **46/46** ACs traced, verdict `complete`.
- Plan review: **Approved** (revision 2026-09-08) — `.factory/plans/ARCHITECT_REVIEW-yoklama-setup.md`. Prior F-1…F-4 closed (wizard-only chrome, ADR-0004 HTTP ACs, shared fill-gaps AC, Settings `#settings-import` host). No re-slice, no re-rate.
- Binding now in plan ACs: TASK-1.1.1#AC8 (one fill-gaps function); TASK-1.1.2#AC13/#AC14; TASK-1.2.1#AC1/#AC8; TASK-1.2.2#AC8; TASK-1.2.3#AC8.
- Complexity: 4 high / 1 medium; mechanical labels match signals; step 4b flagged none.
- Next: Development lane. Do not return the FRD to BA.
