# 0001 — Store GroupProfile as a SQLite singleton

- **Status:** accepted
- **Date:** 2026-09-08
- **Deciders:** architect (requirement-feasibility review, yoklama-setup)

## Context and Problem Statement

The FRD introduces a GroupProfile (group name, first date, end date, repeat rule) and a first-run wizard when the install is unconfigured. The ER diagram is logical only; FRD §4 leaves storage as SQLite vs a sidecar file. The operator already has people, meetings, and marks in `data/attendance.db` and must not see a destructive first-run after `git pull` (BR-003, OP-003, NFR-004).

## Considered Options

- **SQLite singleton table** in `attendance.db` (one row, `id = 1`)
- Sidecar JSON next to the DB (e.g. `data/group.json`)
- Infer “configured” only from people/meetings with no stored profile

## Decision Outcome

Chosen option: **SQLite singleton table** in `data/attendance.db`, because it shares durability, backup, and `.gitignore` with attendance (NFR-004), and profile + series inserts can commit in one transaction.

**Configured** means a `group_profile` row exists.

**Operator upgrade:** on init, if there is no profile row and at least one meeting exists, insert a default profile (`name` empty or `"Yoklama"`, `first_date` = earliest meeting date, `end_date` null, `repeat_rule` `none`) **without** generating a series. The wizard stays off. The champion sets the real name in Settings (FR-019).

**Empty clone:** no profile and no meetings → wizard (FR-001). A local `seed/people.json` that fills an empty people table does **not** skip the wizard (series and group name are still missing).

Sidecar JSON is rejected: two sources of truth, easy to forget in `.gitignore`, and it cannot join the series insert transaction.

## Consequences

- Positive: one backup story; wizard gate is a single row; Settings loads from the same DB.
- Negative / accepted cost: existing DBs get a synthetic profile on first launch after upgrade; the champion may still need to type the group name once.
- Follow-up: Planning ACs must state the upgrade insert and that it does not create meetings.
