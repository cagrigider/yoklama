# Business Requirements Document (BRD) — Yoklama shareable setup

| Field | Value |
|-------|-------|
| Version | v0.1 |
| Date | 2026-09-08 |
| Status | Draft |
| Slug | yoklama-setup |
| Project type | Existing |
| Output locales | en (default; no `_memory/MEMORY.md`) |
| Filename style | locale-suffixed |

## 1. Executive Summary

Yoklama already works for one AI Champion (Grup 8) as a local attendance app. Other champions need the same tool on their own computers without receiving Grup 8’s roster or marks. This change adds a first-run wizard and Settings so each champion can name their group, generate a meeting series, and load people (Excel/CSV, `people.json`, or in-app), while the operator’s existing data is left intact. Sharing is git; personal data stays on disk.

## 2. Business Context & Problem Statement

AI Champions each lead a group and run their own sessions. Yoklama is the right shape (local, live tick, Turkish, manager copy-paste) but it was seeded for Grup 8: roster in `people.json`, hardcoded Wednesday series, and UI branding. That cannot be cloned as-is. Champions are developers, so git is the distribution channel. There must be no login and no central server. The operator already has real attendance in SQLite; an update must not empty that database.

## 3. Goals & Objectives

- A champion with an empty clone can complete setup and tick a meeting without editing Python.
- A champion with existing data (operator) keeps all people, meetings, and marks after upgrade, and can use Settings.
- A git clone never contains another group’s names, sicil, emails, or attendance database.
- README states the only required roster columns: sicil/`id` and name.

## 4. Scope

**In scope:**

- First-run wizard (empty local database / no group profile)
- Settings: group name, series first/end/repeat, import, people add/edit/delete
- Excel/CSV and `people.json` upsert import; whole-file reject on invalid rows
- Series fill-gaps; never delete meetings or marks
- README required-field contract
- Preserve AS-IS live tick, tags, notes, person/meeting summaries, Turkish UI, bind `127.0.0.1`

**Out of scope:**

- Login, accounts, hosted/multi-tenant server
- Access to another champion’s data
- Teams or other auto-attendance
- Guests as a first-class flow
- Program-owner rollup across groups
- Managers as users of the app
- Zip as the primary share method

## 5. Stakeholders

Project-wide map: none (`/factory:ba-init` not run). Slug-specific:

| Stakeholder | Role | Interest/Expectation |
|-------------|------|----------------------|
| Çağrı Gider | Grup 8 AI Champion; operator | Keep local data; Settings; share the app via git without leaking Grup 8 |
| Other AI Champions | Same role on their machines | Empty clone → wizard → their group only |

## 6. Business Requirements (BR)

| ID | Requirement | Priority (MoSCoW) |
|----|-------------|-------------------|
| BR-001 | Yoklama shall remain a single-user local tool: one champion, one computer, one group’s data. | Must |
| BR-002 | An empty install shall be configurable (group, series, roster) without changing source code. | Must |
| BR-003 | An install that already has data shall not be wiped by upgrade or Settings; the champion shall still change group name, series, and roster. | Must |
| BR-004 | Champions shall add and maintain people via spreadsheet/JSON import and via the UI. | Must |
| BR-005 | Champions shall generate a repeating (or single) meeting series from first date, end date, and a simple interval without destroying existing meetings or marks. | Must |
| BR-006 | The shared git repository shall not contain real rosters or attendance databases. | Must |
| BR-007 | Live ticking, activity tags, notes, and copyable summaries shall remain available as they are today. | Must |
| BR-008 | Optional person attributes (position, center) should display when present; email need not be required. | Should |
| BR-009 | Extra Excel column-name aliases beyond sicil/`id`/name/position/center/yetkinlik could be supported later. | Could |
| BR-010 | Yoklama shall not become a logged-in, hosted, or cross-group platform in this change. | Won't |

## 7. User Requirements (UR)

| ID | Requirement | EARS Pattern | Related BR |
|----|-------------|--------------|------------|
| UR-001 | WHILE the local database has no group profile the system shall present a first-run wizard and shall not treat the meeting list as the first screen. | State-driven | BR-002 |
| UR-002 | WHILE a group profile already exists the system shall not present the first-run wizard. | State-driven | BR-003 |
| UR-003 | WHEN the champion completes the wizard with group name, first date, repeat rule, and (when repeat is not “don’t repeat”) an end date on or after the first date the system shall persist the profile, create missing series meetings, and open the meeting list. | Event-driven | BR-002, BR-005 |
| UR-004 | WHEN the champion chooses “don’t repeat” the system shall create only the meeting on the first date and shall not require an end date. | Event-driven | BR-005 |
| UR-005 | WHEN the champion chooses every week, every 2 weeks, or every month the system shall require an end date and shall generate that weekday from the first date through the end date at the chosen interval. | Event-driven | BR-005 |
| UR-006 | IF the end date is before the first date THEN the system shall reject save and keep existing meetings unchanged. | Unwanted | BR-005 |
| UR-007 | WHEN series generation runs the system shall insert a meeting only for generated calendar dates that do not already have a meeting; existing meetings and attendance shall stay unchanged. | Event-driven | BR-003, BR-005 |
| UR-008 | WHEN the champion opens Settings the system shall allow changing group name, first date, end date, and repeat rule, and shall apply UR-007 (fill-gaps only). | Event-driven | BR-003, BR-005 |
| UR-009 | WHEN the wizard finishes with zero people the system shall still persist the group profile and any generated meetings. | Event-driven | BR-002, BR-004 |
| UR-010 | WHEN the champion imports Excel, CSV, or `people.json` the system shall upsert people by sicil/`id` (add or update) and shall not delete people absent from the file. | Event-driven | BR-004 |
| UR-011 | IF any imported row lacks sicil/`id` or name THEN the system shall reject the whole file and change no people. | Unwanted | BR-004 |
| UR-012 | WHEN the champion adds a person in the UI with sicil/`id` and name the system shall add them to the roster. | Event-driven | BR-004 |
| UR-013 | WHEN the champion edits a person the system shall allow name, position, and center to change and shall not allow sicil/`id` to change. | Event-driven | BR-004 |
| UR-014 | WHEN the champion deletes a person the system shall remove that person and all of their attendance rows. | Event-driven | BR-004 |
| UR-015 | IF add-person is submitted without sicil/`id` or name THEN the system shall not create the person. | Unwanted | BR-004 |
| UR-016 | The system shall bind only to the local machine and shall store attendance only in the local database. | Ubiquitous | BR-001 |
| UR-017 | The git-tracked tree shall omit `data/*.db` and real `seed/people.json`; README shall state required import columns (sicil/`id` and name) and optional columns (position, center/yetkinlik). | Ubiquitous | BR-006 |
| UR-018 | The system shall keep live joined/absent ticking, optional activity, tags, notes, and copyable person and meeting summaries. | Ubiquitous | BR-007 |
| UR-019 | WHERE position or center is present the system shall show it on the person row or person report. | Optional | BR-008 |
| UR-020 | WHEN the champion sets a group name the system shall show that name in the app header in place of a hard-coded group label. | Event-driven | BR-002, BR-003 |

## 8. Assumptions, Constraints, Dependencies

- **Assumptions:** Each clone is used by one champion for one group. Python 3 is available. Champions can run `git clone` / `git pull` and `python3 app.py`.
- **Constraints:** No network service, no authentication, no PII in git. Operator SQLite must survive `git pull`. Product UI language remains Turkish.
- **Dependencies:** Private GitHub repo `cagrigider/yoklama`. Excel import depends on a file the champion provides locally; column mapping is sicil or `id`, name, optional position, optional center/yetkinlik.

## 9. Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Operator or a champion deletes a person and loses history | H | M | UI confirm before delete; UR-014 is explicit |
| Import file encoding/headers don’t match | M | H | README required columns; reject whole file (UR-011) |
| `git pull` overwrites local data | H | L | gitignore db and `people.json`; never seed Grup 8 into empty DBs from git |
| Champion treats zip of the whole folder as sharing | M | M | README: clone repo, do not send `data/` |

## 10. AS-IS / TO-BE / GAP

**AS-IS:** Local Python HTTP app on `127.0.0.1:8765`, SQLite, Turkish live-tick UI, tags, copyable summaries. Roster from gitignored `seed/people.json` if present. New databases no longer auto-seed Grup 8 meetings. Header is generic “Yoklama”. GitHub private repo exists without PII. No wizard, no Settings, no Excel import, no people CRUD UI.

**TO-BE:** Same local app, plus group profile, first-run wizard, Settings, bounded series fill-gaps, Excel/CSV/`people.json` upsert with all-or-nothing validation, people add/edit/delete, header shows group name, README field contract.

**GAP / impact:** New first-run and Settings surfaces; group profile persistence; series generator; import parser; people write APIs; delete cascades attendance; skip wizard when profile/data exists; no change to live-tick semantics. Operator impact: one-time Settings to set “Grup 8” name if desired; meetings already in DB are not deleted.

## 11. Open Questions

None undispositioned. See `OPEN-POINTS.md` OP-001 … OP-012 (all answered).
