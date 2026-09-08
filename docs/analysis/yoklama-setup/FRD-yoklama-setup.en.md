# Functional Requirements Document (FRD/SRS) — Yoklama shareable setup

| Field | Value |
|-------|-------|
| Version | v0.1 |
| Date | 2026-09-08 |
| Status | Draft |
| Slug | yoklama-setup |
| Source | BRD-yoklama-setup.en.md, diagrams-yoklama-setup.en.md |
| Output locales | en (default; no `_memory/MEMORY.md`) |

## 1. Scope Summary

Make the existing local Yoklama app usable by other AI Champions via git clone, without login or a server, and without leaking Grup 8 data. In: first-run wizard, Settings, series fill-gaps, Excel/CSV/`people.json` import, people CRUD, README field contract, keep live tick. Out: hosted multi-user product, other groups’ data, Teams auto-attendance, guests, managers as app users.

## 2. Functional Requirements (FR)

| ID | Requirement | EARS Pattern | Source BR | Source UR |
|----|-------------|--------------|-----------|-----------|
| FR-001 | WHILE the local database has no group profile the system shall present a first-run wizard and shall not show the meeting list as the first screen. | State-driven | BR-002 | UR-001 |
| FR-002 | WHILE a group profile exists the system shall not present the first-run wizard. | State-driven | BR-003 | UR-002 |
| FR-003 | WHEN the champion completes the wizard with a group name, a first date, and “don’t repeat” the system shall persist the profile and create a meeting only on the first date. | Event-driven | BR-002, BR-005 | UR-003, UR-004 |
| FR-004 | WHEN the champion completes the wizard with every week, every 2 weeks, or every month and an end date on or after the first date the system shall persist the profile and insert missing meetings on that weekday from first date through end date at the chosen interval. | Event-driven | BR-002, BR-005 | UR-003, UR-005 |
| FR-005 | IF the champion submits a repeating series with an end date before the first date THEN the system shall reject the save and leave meetings unchanged. | Unwanted | BR-005 | UR-006 |
| FR-006 | WHEN series generation runs the system shall insert a meeting only for generated dates that do not already have a meeting and shall not delete existing meetings or attendance. | Event-driven | BR-003, BR-005 | UR-007 |
| FR-007 | WHEN the champion opens Settings the system shall allow changing group name, first date, end date, and repeat rule using FR-005 and FR-006, and shall allow import and people add/edit/delete. | Event-driven | BR-003, BR-004 | UR-008 |
| FR-008 | WHEN the wizard completes with zero people the system shall persist the profile and any generated meetings. | Event-driven | BR-002, BR-004 | UR-009 |
| FR-009 | WHEN the champion imports Excel, CSV, or `people.json` the system shall upsert people by sicil/`id` and shall not delete people who are absent from the file. | Event-driven | BR-004 | UR-010 |
| FR-010 | IF any imported row lacks sicil/`id` or name THEN the system shall reject the whole file and change no people. | Unwanted | BR-004 | UR-011 |
| FR-011 | WHEN the champion adds a person with sicil/`id` and name the system shall add them to the roster. | Event-driven | BR-004 | UR-012 |
| FR-012 | WHEN the champion edits a person the system shall allow name, position, and center to change and shall not allow sicil/`id` to change. | Event-driven | BR-004 | UR-013 |
| FR-013 | WHEN the champion deletes a person the system shall remove that person and all of their attendance rows. | Event-driven | BR-004 | UR-014 |
| FR-014 | IF add-person is submitted without sicil/`id` or name THEN the system shall not create the person. | Unwanted | BR-004 | UR-015 |
| FR-015 | The system shall accept connections only on the local machine and shall store people, meetings, and attendance only in the local database. | Ubiquitous | BR-001 | UR-016 |
| FR-016 | The git-tracked tree shall omit `data/*.db` and real `seed/people.json`; README shall state required columns sicil/`id` and name, and optional position and center/yetkinlik. | Ubiquitous | BR-006 | UR-017 |
| FR-017 | The system shall keep live joined/absent ticking, optional activity, tags, notes, and copyable person and meeting summaries. | Ubiquitous | BR-007 | UR-018 |
| FR-018 | WHERE position or center is present the system shall show it on the person row or person report. | Optional | BR-008 | UR-019 |
| FR-019 | WHEN a group name is saved the system shall show that name in the app header. | Event-driven | BR-002, BR-003 | UR-020 |

## 3. Non-Functional Requirements (NFR)

### 3.1 Performance & Scalability

| ID | Requirement | EARS Pattern |
|----|-------------|--------------|
| NFR-001 | WHEN the champion saves one attendance mark on a roster of at most 80 people the system shall persist it and update that row within 1 second on the local machine. | Event-driven |

### 3.2 Security & Privacy

| ID | Requirement | EARS Pattern |
|----|-------------|--------------|
| NFR-002 | The system shall listen only on 127.0.0.1, shall not require a password, and shall not place a real roster or attendance database in git. | Ubiquitous |

### 3.3 Usability & Accessibility

| ID | Requirement | EARS Pattern |
|----|-------------|--------------|
| NFR-003 | The system shall present the wizard, Settings, and people forms in Turkish, consistent with the existing UI, and shall document required import columns in README. | Ubiquitous |

### 3.4 Reliability & Maintainability

| ID | Requirement | EARS Pattern |
|----|-------------|--------------|
| NFR-004 | WHEN the champion updates the app via git pull the system shall leave an existing `data/attendance.db` in place; series generation shall not drop existing marks. | Event-driven |

## 4. ⚠ Conflicts & Gaps

- [ ] None detected. GroupProfile storage (SQLite table vs config file) is an implementation choice; ER shows a logical entity only.

## 5. Traceability Matrix

| Requirement | Source BR | Source UR | Diagram |
|-------------|-----------|-----------|---------|
| FR-001 | BR-002 | UR-001 | Activity |
| FR-002 | BR-003 | UR-002 | Activity, State |
| FR-003 | BR-002, BR-005 | UR-003, UR-004 | Activity, Sequence |
| FR-004 | BR-002, BR-005 | UR-003, UR-005 | Activity |
| FR-005 | BR-005 | UR-006 | Activity |
| FR-006 | BR-003, BR-005 | UR-007 | Activity, State |
| FR-007 | BR-003, BR-004 | UR-008 | Activity |
| FR-008 | BR-002, BR-004 | UR-009 | Sequence |
| FR-009 | BR-004 | UR-010 | Activity, ER |
| FR-010 | BR-004 | UR-011 | Activity, Sequence |
| FR-011 | BR-004 | UR-012 | Activity, ER |
| FR-012 | BR-004 | UR-013 | ER |
| FR-013 | BR-004 | UR-014 | ER |
| FR-014 | BR-004 | UR-015 | Activity |
| FR-015 | BR-001 | UR-016 | Sequence |
| FR-016 | BR-006 | UR-017 | — |
| FR-017 | BR-007 | UR-018 | — |
| FR-018 | BR-008 | UR-019 | ER |
| FR-019 | BR-002, BR-003 | UR-020 | State |
| NFR-001 | BR-007 | — | — |
| NFR-002 | BR-001, BR-006, BR-010 | UR-016, UR-017 | Sequence |
| NFR-003 | BR-002 | UR-017 | Activity |
| NFR-004 | BR-003, BR-005, BR-006 | UR-007 | State |
