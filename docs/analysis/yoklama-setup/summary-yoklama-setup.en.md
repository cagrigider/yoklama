# Executive Summary — Yoklama shareable setup

| Field | Value |
|-------|-------|
| Date | 2026-09-08 |
| Slug | yoklama-setup |
| Version | v0.1 |

## Problem

Yoklama is a local attendance app that already works for one AI Champion. Other champions cannot clone it safely: the product was seeded for one group, and a naive share would leak roster and marks. Cadence is not the same for every group.

## Proposed Solution

Keep Yoklama on each champion’s computer (no login, no server). Ship it via private git. An empty clone starts with a short wizard: group name, first meeting, end date, weekly / every 2 weeks / monthly / no repeat, optional roster import. Later, Settings does the same without wiping data. People can be imported (Excel/CSV or JSON) or maintained in the UI. Generating dates only fills gaps; existing ticks stay.

## Scope (Summary)

- In: wizard, Settings, import, people add/edit/delete, series fill-gaps, README required columns, keep live tick
- Out: login, central server, other groups’ data, Teams auto-attendance, guests, manager as an app user

## Key Requirements

- BR-001 Local-only, one group per machine
- BR-002 Empty install configurable without code edits
- BR-003 Existing data not wiped; Settings still available
- BR-004 Roster via import and UI
- BR-005 Series from first/end/repeat without deleting history
- BR-006 Git share without PII
- BR-007 Keep live tick and copyable summaries

## Top Risks

- Delete person removes history (confirm in UI)
- Bad spreadsheet rejected in full (champion must fix the file)
- Accidental share of `data/` folder (README)

## Next Step

`/factory:ba-modeler` on slug `yoklama-setup` (activity/state for wizard, Settings, import, series). Then FRD and UI specs. Implementation only after `/factory:plan`, not from this BRD directly.
