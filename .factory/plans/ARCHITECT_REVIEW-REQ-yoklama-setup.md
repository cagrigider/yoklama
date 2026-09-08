# Architect Requirement Feasibility Review — yoklama-setup

| Field | Value |
|-------|--------|
| Slug | yoklama-setup |
| Mode | Requirement feasibility review (no implementation plan) |
| Requirement | `docs/analysis/yoklama-setup/FRD-yoklama-setup.en.md` |
| Also read | BRD, diagrams, `uiux/screens.md`, `review/REVIEW-yoklama-setup.en.md`, `app.py`, `static/`, `README.md`, `.gitignore` |
| Date | 2026-09-08 |
| Reviewer | architect |
| **Verdict** | **Approved-with-notes** |

## Verdict summary

The FRD can be built on the current local Python 3 + SQLite + static SPA without changing the bind address, the live-tick model, or the “no pip / no login / PII off git” shape. Gaps are additive (profile table, series generator, import, people write APIs, wizard/Settings screens). Three storage/algorithm choices the FRD left open are now decided (ADR-0001 … 0003). Nothing requires returning the FRD to BA before Planning.

---

## 1. Technical feasibility

The running app already is the TO-BE runtime: `ThreadingHTTPServer` on `127.0.0.1:8765`, `data/attendance.db`, hash SPA, Turkish UI, single-row attendance UPSERT, `ON DELETE CASCADE` on person → attendance (FR-013). `seed_meetings()` is a no-op; new clones do not get Grup 8 dates.

| FR cluster | Feasible? | Structural cost |
|-----------|-----------|-----------------|
| FR-001…002 wizard gate | Yes, with ADR-0001 upgrade rule | New table + `/api/meta.configured`; SPA intercept before meeting list |
| FR-003…006 series | Yes | One date generator (ADR-0003); INSERT missing dates only; no UNIQUE(date) today — check existence by `date` |
| FR-007, FR-019 Settings + header | Yes | New `#/settings`; `/api/meta` returns `groupName` |
| FR-008 empty roster | Yes | Wizard must not require people; `seed_people` may still fill from local `people.json` without skipping wizard |
| FR-009…014 import + CRUD | Yes | New POST/PUT/DELETE `/api/people` and import endpoint; people UI is read-only today |
| FR-015…016 local + git | Already true | README column contract still missing (note) |
| FR-017…018 live tick / position | Already true | Do not rewrite live handlers |

Excel without a package is the only non-trivial technical risk; ADR-0002 keeps stdlib and fails exotic `.xlsx` closed to CSV. That satisfies FR-009 without violating the existing run contract.

There is no partner API. Planning must not invent OpenAPI; extend `Handler` JSON routes.

---

## 2. Conflicts with current architecture

| Topic | Conflict? | Resolution |
|---------|-----------|------------|
| Bind / no auth / SQLite file | None | FR-015 / NFR-002 match `HOST = "127.0.0.1"` and gitignore |
| Stdlib-only vs Excel | **Tension** | ADR-0002 — do not add `openpyxl` |
| FR-001 “no group profile → wizard” vs operator DB with meetings but no profile | **Wording vs OP-003/BR-003** | ADR-0001 — materialize a default profile when meetings exist; do not generate series |
| GroupProfile table vs sidecar JSON | Unspecified in FRD §4 | ADR-0001 — SQLite singleton, not sidecar |
| `seed_people()` on empty people table | Compatible if wizard is not skipped | People-only seed ≠ configured |
| People write APIs / Settings / wizard | Gap, not a collision | Additive |
| Meeting delete vs series “never delete” | None | User-initiated extra/series delete on the live screen stays AS-IS; generator must not delete |
| ER `PERSON.id` vs import `sicil` | None | Map `sicil` → `people.id` |

**Do not** interpret FR-001 as “any DB without a profile row shows the wizard.” That would put the operator on SCR-01 after upgrade. TC-BE-001 already describes first-run as a DB with **no people and no meetings**.

---

## 3. NFR realism

### NFR-001 — 1 s save on ≤80 people — **realistic**

Attendance persist is already one `INSERT … ON CONFLICT DO UPDATE` plus a roster reread (`meeting_roster`: two queries). Eighty rows on localhost is milliseconds, not seconds. The 500 ms UI lock is already stricter than 1 s. BA tests do not cover this (⚠ in REVIEW). Planning: one manual/smoke AC is enough; do not add a flaky wall-clock assertion as a gate.

`/api/overview` is O(people × meetings) and is **out of NFR-001**. Leave it unless Settings people-list feels slow; 80 × tens of meetings is still fine locally.

### NFR-002 — 127.0.0.1, no password, no PII in git — **already met, keep it**

- Listen: `ThreadingHTTPServer(("127.0.0.1", 8765), …)` — no change.
- No password: keep.
- Git: `data/*.db` and `seed/people.json` are gitignored and **not tracked**. Tracked seed is synthetic `people.example.json`. Local `seed/people.json` may exist on the operator machine; implementation must never add it to the tree.

### NFR-003 — Turkish wizard/Settings/people forms + README columns — **realistic**

Existing UI is Turkish (`lang="tr"`, Katıldı/Gelmedi). Screens.md is English by BA locale rules. Implementation must write Turkish copy, not paste spec labels. README today does not list required columns sicil/`id` + name (FR-016) — documentation task, not a stack issue.

### NFR-004 — git pull must not wipe DB; series must not drop marks — **realistic if migrations stay additive**

- `git pull` does not touch gitignored `data/attendance.db`.
- `init_db` uses `CREATE TABLE IF NOT EXISTS` and does not reseed meetings.
- `seed_people` returns if the people table is non-empty.

Hazard is implementation: `DROP TABLE`, deleting `data/`, or series REPLACE. Planning ACs must require additive `group_profile` create and fill-gaps-only inserts (ADR-0001, ADR-0003). Shortening end date must not DELETE meetings (SCR-04).

---

## 4. Integration risk

Low. No external systems. Import files stay on the champion’s disk (gitignore `*.xlsx`/`*.csv`). Git is the share channel; zip-of-`data/` remains a human process risk (BRD §9) — README only.

File upload: keep JSON bodies (ADR-0002) so the stdlib server does not grow a multipart parser.

---

## 5. Findings

### F-1 (note, implementation-binding) — FR-001 upgrade path

**IDs:** FR-001, FR-002, BR-003, OP-003, NFR-004  
**Why:** After this change, the operator’s DB has people and meetings but no `group_profile`. A literal FR-001 gate would show SCR-01.  
**Solution:** ADR-0001. Planning AC: if meetings exist and profile does not, insert default profile, skip wizard, do not insert series dates.

### F-2 (note, decided) — GroupProfile storage

**IDs:** FRD §4, ER GROUP_PROFILE  
**Why:** Table vs sidecar was left open. Sidecar can diverge from the DB and from NFR-004.  
**Solution:** ADR-0001 — singleton row in `attendance.db`.

### F-3 (note, decided) — Excel without pip

**IDs:** FR-009, FR-010  
**Why:** README/BRD assume `python3 app.py` with no packages.  
**Solution:** ADR-0002. Planning must not add `requirements.txt` for import.

### F-4 (note, decided) — Monthly series rule

**IDs:** FR-004, OP-005, OP-008  
**Why:** “Every month” + “weekday of the first date” is otherwise implementer-guessed.  
**Solution:** ADR-0003 (week-of-month ordinal + weekday; skip impossible months). Encode in task ACs.

### F-5 (note) — NFR-001 has no designed test

**IDs:** NFR-001  
**Why:** BA already flagged this. It is not a feasibility fail.  
**Solution:** Manual check on an 80-person roster; do not treat as Must-automated.

### F-6 (note) — People write surface is missing

**IDs:** FR-011…014  
**Why:** `handle_api_write` has no people POST/PUT/DELETE; `#/people` is read-only. Schema and CASCADE already match FR-013.  
**Solution:** Add JSON people APIs and SCR-05…07. Duplicate id → 409, no silent overwrite on add.

### F-7 (note) — README field contract

**IDs:** FR-016, NFR-003  
**Why:** README explains copy-`people.example.json` but not required vs optional columns.  
**Solution:** Document sicil/`id` + name required; position, center/yetkinlik optional.

### F-8 (note) — Wizard then rejected import

**IDs:** FR-008, FR-010, SCR-01  
**Why:** Sequence says invalid file does not roll back profile.  
**Solution:** Two transactions: (1) profile + meetings, (2) import. Match the screen spec.

### F-9 (note) — Series date identity

**IDs:** FR-006  
**Why:** Multiple meetings can share a date today.  
**Solution:** “Already has a meeting” = `SELECT 1 FROM meetings WHERE date = ?`. Do not add UNIQUE(date) (would break extra meetings on the same day).

---

## 6. Decisions recorded

| ADR | Title |
|-----|--------|
| [0001](../../docs/adr/0001-group-profile-in-sqlite.md) | GroupProfile in SQLite; operator upgrade insert |
| [0002](../../docs/adr/0002-stdlib-roster-import.md) | Stdlib CSV/JSON/xlsx; JSON upload |
| [0003](../../docs/adr/0003-series-fill-gaps-weekday.md) | Fill-gaps weekday / monthly ordinal |

`ARCHITECTURAL_PRINCIPLES.md` bootstrapped (stdlib, additive schema, fill-gaps, PII off git, Turkish UI). `ARCHITECTURE.md` refreshed.

---

## 7. Open questions for the primary agent

None that block Planning. Optional BA tidy (not required): reword FR-001 to “no group profile **and** no meetings” so it matches ADR-0001 and TC-BE-001. If the analyst leaves FR-001 as written, Planning still follows ADR-0001.

---

## 8. Planning handoff

If this verdict is accepted: `/factory:plan docs/analysis/yoklama-setup/FRD-yoklama-setup.en.md`

Slice so that (a) additive `group_profile` migrate + upgrade insert, (b) series function used by wizard and Settings, (c) import validator, (d) people CRUD, (e) Turkish wizard/Settings, (f) README columns, (g) live tick untouched. Expected tests remain the BA Gherkin ids; do not require a services artefact.
