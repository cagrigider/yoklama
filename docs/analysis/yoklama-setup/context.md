---
name: context
slug: yoklama-setup
updated: 2026-09-08
project-type: existing
---

# Context — yoklama-setup

## Project type

Existing project (AS-IS + GAP). Confirmed by operator 2026-09-08.

## Source

- Running app: `attendance/` (GitHub `cagrigider/yoklama`, private)
- Intake: `docs/analysis/_inbox/INTAKE-2026-09-08-1.md`
- Operator Q&A in the same chat (2026-09-08)
- No prior Yoklama BRD/FRD. AS-IS is taken from the running app + intake, not from a signed document.
- Operator declined extra Excel as an AS-IS source (`Group_8.xlsx` stays off git and is not a spec).

## Purpose

Other AI Champions can clone Yoklama, set **their** group name, meeting series, and roster, then tick attendance on their own computer. Nobody sees another champion’s data. No login and no shared server.

## Scope boundaries (operator, 2026-09-08)

**In (GAP on top of AS-IS):**

- First-run wizard when the database is empty
- Settings afterwards (including the operator’s already-populated install): group name, series, further import
- Roster via Excel/CSV import **and** `people.json`
- Add / edit / delete people in the UI (widened vs intake)
- Series from first date + repeat (every week / every 2 weeks / every month / don’t repeat), weekday of the first date
- Fill-gaps only: never delete existing meetings or marks
- README lists required roster fields
- Required fields: `id` or `sicil` + `name`. Optional: `position`, `center`/`yetkinlik`. `email` not required

**Out:**

- Login, accounts, central server
- Seeing or merging other champions’ groups
- Teams (or other) auto-attendance
- Guests as a first-class flow
- Cross-group / program-owner rollup
- Managers as app users (copy-paste summary already exists; they do not use the app)

**AS-IS that stays (unless a later phase changes it):**

- Local `127.0.0.1` web app, SQLite on disk
- Live tick: joined / absent, optional activity, tags, note
- Turkish UI
- Person history + copyable meeting/person summary for a manager
- Git distribution; `data/attendance.db` and `seed/people.json` gitignored

## Key stakeholders (slug-specific)

Project-wide map: **none** — `docs/analysis/_memory/` is missing. Suggest `/factory:ba-init`.

- Çağrı Gider — Grup 8 AI Champion; operator of this analysis; already has local data that must not be wiped
- Other AI Champions — same role on their own machines; empty clone until they complete first-run

## Output locales

No `MEMORY.md`. Default for this analysis: **en** only, filename style **locale-suffixed** (`BRD-yoklama-setup.en.md`). The product UI stays Turkish; that is a UI locale, not a BRD locale, unless the operator later asks for `tr` artifacts.

## Structured raw requirements (elicitation, 2026-09-08)

Operator confirmed this set, then answered the gaps below.

1. Each AI Champion runs Yoklama only on their computer. No login, no shared server, no one else’s data.
2. Empty database: first-run wizard for group name, first meeting date, end date, repeat (every week / every 2 weeks / every month / don’t repeat). Weekday follows the first date. Roster may be imported (Excel/CSV and/or `people.json`) or left empty.
3. Wizard may finish with zero people; people can be added, edited, imported later.
4. After first run (including the operator’s populated Grup 8 database): Settings — group name, series fill-gaps, further import, people maintenance. Wizard does not run again and must not wipe existing data.
5. Series generation never deletes meetings or marks. It only inserts missing dates in [first date, end date] on the first date’s weekday at the chosen interval.
6. Extending the end date in Settings adds missing future dates. Shortening the end date does not remove meetings already created.
7. People: Excel/CSV import, `people.json`, and UI add/edit/delete.
8. Import is upsert on sicil/`id`: update matching rows, add new ids, do not delete people absent from the file.
9. Required person fields: `id` or `sicil` + `name`. Optional: `position`, `center`/`yetkinlik`. `email` not required.
10. Sicil/`id` is immutable after create. Name/position/center can be edited. Wrong id → delete and add again.
11. Delete in the UI is allowed even if the person has marks; those attendance rows go with them.
12. AS-IS live tick, tags, Turkish UI, person/meeting copy-paste summaries stay.
13. Git clone to share; never commit `data/attendance.db` or real `seed/people.json`.

## Open questions

Intake OP-001 … OP-012 answered (see `OPEN-POINTS.md`). No undispositioned blockers or majors.

## Phase 2

BRD `BRD-yoklama-setup.en.md` and `summary-yoklama-setup.en.md` drafted 2026-09-08 (v0.1). MoSCoW accepted by operator. Import invalid rows: reject whole file (OP-012).
