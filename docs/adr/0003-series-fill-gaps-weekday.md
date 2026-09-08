# 0003 — Series fill-gaps on the first date’s weekday

- **Status:** accepted
- **Date:** 2026-09-08
- **Deciders:** architect (requirement-feasibility review, yoklama-setup)

## Context and Problem Statement

FR-004 / OP-005 / OP-008 require generating meetings from first date, end date, and repeat (every week / every 2 weeks / every month / don’t repeat), using the weekday of the first date, inserting only dates that do not already have a meeting. “Every month” plus “that weekday” is under-specified (same calendar day vs same weekday each month vs every four weeks).

## Considered Options

- Calendar day-of-month (`+1` month, clamp to last day) — drops weekday
- Every 4 weeks from first date — not calendar months
- **Same weekday and same week-of-month ordinal** as the first date, in each month through the end date

## Decision Outcome

Chosen option: **weekday of `first_date`, at the stated interval**, using `datetime.date` only.

| `repeat_rule` | Dates |
|---------------|--------|
| `none` | `first_date` only; end date not required |
| `weekly` | `first_date + 7n` while `<= end_date` |
| `biweekly` | `first_date + 14n` while `<= end_date` |
| `monthly` | in each calendar month from the first date’s month through the end date’s month, the date with the same weekday and week-of-month ordinal as `first_date` (`(day - 1) // 7 + 1`); skip a month that has no such day (e.g. fifth Wednesday); keep a date only if `first_date <= d <= end_date` |

Insert a `meetings` row only when **no** meeting exists with that ISO `date`. Never update or delete meetings or attendance. `end_date < first_date` → reject, no writes (FR-005). Shortening end date in Settings does not remove rows (SCR-04).

Meeting `kind` for generated rows is `series`; extras created from the list stay `extra`.

## Consequences

- Positive: weekly/biweekly match TC-BE-004; monthly keeps Wednesday-style series; fill-gaps is a single function used by wizard and Settings.
- Negative / accepted cost: a fifth-weekday first date will skip some months; that is accepted.
- Follow-up: Planning ACs must name this monthly rule so tests are not guessed.
