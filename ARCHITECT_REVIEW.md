VERDICT: APPROVED

# Architect post-implementation review — PLAN-yoklama-setup

| Field | Value |
|-------|--------|
| Mode | Post-implementation |
| Plan | PLAN-yoklama-setup (TASK-1.1.1, 1.2.3, 1.1.2, 1.2.1, 1.2.2) |
| Diff | `ff2221f..HEAD` (`a1225a6`, `6125c1b`, `41bf77a`, `a4ce3d4`) |
| Date | 2026-09-09 |
| Reviewer | architect |
| **Verdict** | **APPROVED** — architecturally sound. No CHANGES REQUESTED. |

The sprint implements the recorded decisions (ADR-0001…0004) on the existing Python stdlib + SQLite + hash-SPA process. It does **not** invent a second HTTP protocol, does **not** wipe the operator database, and does **not** show the wizard when meetings already exist.

No new ADR. No change to `ARCHITECTURAL_PRINCIPLES.md`.

---

## Verdict summary

Wizard, Settings, series fill-gaps, roster import, and people CUD sit on one loopback JSON `Handler`, one SQLite file, and one shared `fill_gap_meetings` function. Operator upgrade is additive `CREATE TABLE IF NOT EXISTS group_profile` plus `ensure_default_profile` (default row, no series). Live tick remains a single-row attendance PUT.

Problems that would require a developer fix: **none**.

---

## ADR honor check

| ADR | Required | Evidence in `ff2221f..HEAD` | Result |
|-----|----------|-----------------------------|--------|
| **0001** GroupProfile SQLite singleton; operator upgrade insert; wizard only when no profile and no meetings | `group_profile` `id=1`; no sidecar JSON; meetings ⇒ default profile, **no** `fill_gap_meetings` | `CREATE TABLE IF NOT EXISTS group_profile (id INTEGER PRIMARY KEY CHECK (id = 1), …)`; `ensure_default_profile` returns if a row exists, else `MIN(date)` + `name='Yoklama'` + `end_date NULL` + `repeat_rule='none'` without calling fill-gaps; SPA `route()` renders wizard iff `!meta.configured` | **Honored** |
| **0002** Stdlib CSV/JSON/xlsx; JSON upload body; all-or-nothing then upsert by id | No pip / `openpyxl`; not multipart; no delete of absentees | `csv` + `json` + `zipfile` + `xml.etree.ElementTree`; `POST /api/people/import` `{filename, text\|contentBase64}`; `validate_import_rows` before `ON CONFLICT(id) DO UPDATE`; no `requirements.txt` | **Honored** |
| **0003** Weekday fill-gaps; never delete; one function for wizard and Settings | `datetime.date` only; weekly +7 / biweekly +14 / monthly ordinal; insert missing ISO dates only | `fill_gap_meetings`; `_nth_weekday_in_month`; `kind='series'`; no `DELETE`/`UPDATE` of meetings; `_put_profile` is the only writer for wizard and Settings | **Honored** |
| **0004** Pin QA harness JSON contract | `/api/meta`, `PUT /api/profile`, `POST /api/people/import`, people POST/PUT/DELETE; camelCase; duplicate add 409 | Exact paths; meta adds `configured`/`groupName` (+ optional dates/rule); README states there is **no** `/api/setup` alias | **Honored** |

---

## Operator upgrade path (NFR-004 / ADR-0001)

**Does not wipe the DB. Does not show the wizard when meetings exist.**

`init_db()` on startup:

1. `CREATE TABLE IF NOT EXISTS` for people, meetings, attendance, **and** `group_profile` — no `DROP TABLE`, no rebuild from seed.
2. `seed_people` only if `people` is empty (pre-existing; does not create a profile).
3. `seed_meetings` remains a no-op.
4. `ensure_default_profile`: if **no** profile row and **at least one** meeting → insert default profile **without** `fill_gap_meetings`. `GET /api/meta` then returns `configured: true`. The SPA never enters `renderWizard()`.

Covered by `tests/test_group_profile.py` (`test_ensure_default_profile_inserts_without_extra_meetings`, `test_seed_people_does_not_create_profile`, `test_fresh_db_has_no_profile_configured_false`). Isolated suites never open `data/attendance.db`.

Empty clone (no profile, no meetings) → `configured: false` → wizard, even if `seed/people.json` filled people.

---

## HTTP surface (no second protocol)

| Action | Contract (ADR-0004) | Shipped |
|--------|---------------------|---------|
| Gate + header | `GET /api/meta` + `configured`, `groupName` | Existing fields spread with `profile_meta` |
| Wizard / Settings save | `PUT /api/profile` camelCase body | `_put_profile`: `fill_gap_meetings` then `upsert_group_profile`, **one** `commit`; `SeriesError` → `rollback`, HTTP 400 |
| Import | `POST /api/people/import` JSON, not multipart | People writes only; does not touch `group_profile` or meetings |
| People CUD | `POST /api/people`, `PUT/DELETE /api/people/{id}`; duplicate **409** | `people_write_id` excludes `import`; POST add is not upsert |
| Live tick | Unchanged `PUT /api/meetings/{id}/attendance/{personId}` | Single-row upsert; SPA `save()` still one PUT + roster reread |

No `/api/setup`, no `/api/group`, no OpenAPI, no multipart parser. `HOST` remains `127.0.0.1`.

---

## Per-task architecture

### TASK-1.1.1 — `fill_gap_meetings`

Shared generator in `app.py`. Calendar `date` / whole-day `timedelta` only. `repeat_rule none` inserts `first_date` only; weekly/biweekly step 7/14; monthly uses `(day-1)//7+1` weekday ordinal and skips months with no such day. Inserts `kind=series` only when that ISO `date` has no meeting. `POST /api/meetings` extras stay `extra`. Invalid bounds raise `SeriesError` before durable meeting writes. **AC8:** wizard and Settings do not reimplement this.

### TASK-1.1.2 — Profile gate and wizard

Configured **means a `group_profile` row exists**. Unconfigured `route()` returns `renderWizard()` before `#/`, `#/people`, `#/settings`, `#/meeting/:id`. Turkish `WIZARD_COPY`. PUT persists singleton + fill-gaps together; import is **not** in that transaction.

### TASK-1.2.1 — Settings, header, live-tick preserve

`#/settings` loads/saves the same singleton via meta + `PUT /api/profile` (same `_put_profile`). Shorter end date cannot delete meetings (fill-gaps insert-only). `#group-name` and `#meeting-list-title` use `groupName`. Live tick / tags / notes / summaries were not rewritten. `#settings-import` host present for TASK-1.2.2.

### TASK-1.2.2 — Roster import

Stdlib parsers; JSON body; all-or-nothing; upsert by sicil/`id`; absentees kept; exotic xlsx → 400 `exotic_xlsx` with CSV guidance. Wizard: `PUT /api/profile` **then** optional `POST /api/people/import`. Settings Aktar is a separate button. Rejected import cannot roll back a committed profile. README column + git-omit contract matches `.gitignore` (`data/*.db`, `seed/people.json`).

### TASK-1.2.3 — People CUD

Add requires id+name; duplicate 409 (not upsert); edit path-id only, sicil disabled; confirmed delete cascades attendance via FK. Empty roster valid. Position/center shown when present. Live tick writes untouched.

---

## Non-blocking notes (not CHANGES REQUESTED)

These do not violate ADRs or ACs; they are not developer-blocking.

1. **Header tabs stay in `index.html` during first-run.** Clicks still re-enter `route()` and, while `configured` is false, still render the wizard (TASK-1.1.2#AC13). Chrome is gated, not removed.
2. **`renderSettings` refetches `GET /api/meta`** after `route()` already loaded meta. Extra loopback GET; not a second protocol.
3. **Import row replaces all person columns.** A sicil+name-only file blanks omitted position/center/email on that id. Absentees are still kept (ADR-0002). Documented as full-row upsert.
4. **xlsx XML** uses stdlib `ElementTree.fromstring` without `defusedxml` (ADR-0002 / principles: no pip). Fail-closed to `exotic_xlsx` / `invalid_file`. Loopback, champion-chosen files.

---

## Open questions for the primary agent

None. No human decision is required to close this review.
