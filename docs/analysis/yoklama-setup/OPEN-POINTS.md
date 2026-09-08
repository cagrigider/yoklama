# Open points — yoklama-setup

## OP-001 · major · answered
- **Raised by:** intake · 2026-09-08
- **Q:** How does a champion’s people list get filled on first run?
- **Why it matters:** first-run screen and README.
- **Affects:** wizard, Settings import, README, people.json seed path
- **Disposition:** answered (operator, 2026-09-08) — Excel/CSV import in the app **and** `people.json` still works.

## OP-002 · major · answered
- **Raised by:** intake · 2026-09-08
- **Q:** Which roster fields are required?
- **Why it matters:** import validation and README contract. Unused fields must not be mandatory.
- **Affects:** import, `people.example.json`, README
- **Disposition:** answered (operator + current UI, 2026-09-08) — required `id` or `sicil` + `name`; optional `position` and `center`/`yetkinlik`; `email` not required (stored if present, not shown).

## OP-003 · blocker · answered
- **Raised by:** intake · 2026-09-08
- **Q:** Who sees setup — empty clone only, or also Settings later?
- **Why it matters:** operator already has Grup 8 data that must not be wiped.
- **Affects:** first-run gate, Settings, header group name
- **Disposition:** answered (operator, 2026-09-08) — empty DB → first-run wizard; afterwards a Settings screen for everyone including the operator.

## OP-004 · blocker · answered
- **Raised by:** intake · 2026-09-08
- **Q:** Generating a series when meetings already exist — delete, replace, or fill gaps?
- **Why it matters:** wrong default can wipe attendance.
- **Affects:** series generator, Settings, existing Grup 8 meetings
- **Disposition:** answered (operator, 2026-09-08) — never delete; add missing dates in the range; leave existing meetings and marks.

## OP-005 · major · answered
- **Raised by:** intake · 2026-09-08
- **Q:** Which repeat choices does setup/Settings offer?
- **Why it matters:** series generator and first-run fields.
- **Affects:** wizard, Settings, meeting seed
- **Disposition:** answered (operator, 2026-09-08) — weekday of the first date; every week / every 2 weeks / every month / don’t repeat.

## OP-006 · major · answered
- **Raised by:** analyst Phase 1 · 2026-09-08
- **Q:** Delete a person who already has attendance?
- **Why it matters:** history integrity vs roster hygiene.
- **Affects:** people UI, attendance rows, reports
- **Disposition:** answered (operator, 2026-09-08) — delete is allowed; their marks are deleted with them.

## OP-007 · major · answered
- **Raised by:** analyst Phase 1 · 2026-09-08
- **Q:** Re-import when roster is not empty?
- **Why it matters:** accidental wipe vs stale rows.
- **Affects:** Excel/CSV/`people.json` import
- **Disposition:** answered (operator, 2026-09-08) — upsert on sicil/id; do not delete people missing from the file.

## OP-008 · blocker · answered
- **Raised by:** analyst Phase 1 · 2026-09-08
- **Q:** How is a repeating series bounded?
- **Why it matters:** unbounded generation.
- **Affects:** wizard, Settings, series generator
- **Disposition:** answered (operator, 2026-09-08) — first date and end date; fill that weekday through the end date.

## OP-009 · major · answered
- **Raised by:** analyst Phase 1 · 2026-09-08
- **Q:** May first-run finish with an empty roster?
- **Why it matters:** wizard validation vs people UI later.
- **Affects:** first-run
- **Disposition:** answered (operator, 2026-09-08) — yes; add or import later.

## OP-010 · major · answered
- **Raised by:** analyst Phase 1 · 2026-09-08
- **Q:** Can sicil/id be edited after create?
- **Why it matters:** import match key and attendance PK.
- **Affects:** people edit, import
- **Disposition:** answered (operator, 2026-09-08) — immutable; wrong id → delete and add.

## OP-011 · minor · answered
- **Raised by:** analyst Phase 0 · 2026-09-08
- **Q:** Is people add/edit/delete in the UI in this slug?
- **Why it matters:** intake had import only.
- **Affects:** people screens, FRD
- **Disposition:** answered (operator, 2026-09-08) — in scope (widened).

## OP-012 · major · answered
- **Raised by:** analyst Phase 2 · 2026-09-08
- **Q:** Spreadsheet with mixed valid and invalid rows?
- **Why it matters:** partial import vs atomic.
- **Affects:** Excel/CSV/`people.json` import
- **Disposition:** answered (operator, 2026-09-08) — reject the whole file; change nothing.
