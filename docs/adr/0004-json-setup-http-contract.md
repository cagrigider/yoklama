# 0004 — JSON HTTP contract for setup, import, and people writes

- **Status:** accepted
- **Date:** 2026-09-08
- **Deciders:** architect (plan review, yoklama-setup)

## Context and Problem Statement

The existing app already speaks JSON over `/api/…` (`GET /api/meta`, `GET /api/people`, meeting CUD, single-row attendance). yoklama-setup adds a profile save, a roster import, and people writes. The IEEE 829 test plan designed a harness for those routes, but PLAN-yoklama-setup acceptance criteria never named them. The developer reads plan ACs (and `ARCHITECTURAL_PRINCIPLES.md`), not the test plan. Unnamed routes would satisfy every current AC and still block QA, or would fork a second JSON style (snake_case profile fields vs existing camelCase `statusLabels`).

## Considered Options

- Leave paths as a QA substitution table only (test plan §6.3)
- Invent a second protocol (multipart, OpenAPI, `/api/setup` plus `/api/group`)
- **Pin the test plan’s harness as the Development contract**, matching existing JSON handlers

## Decision Outcome

Chosen option: **pin the harness as the contract**, because the SPA already `fetch`es JSON `/api/…` and `GET /api/meta` is already loaded on the meeting list. Substitution remains valid only for documented aliases of these same operations.

| Action | Method | Path | Body / notes |
|--------|--------|------|----------------|
| Meta (gate + header) | GET | `/api/meta` | Existing fields plus `configured` (bool) and `groupName` (string). May also return `firstDate`, `endDate`, `repeatRule`. |
| Wizard and Settings save | PUT | `/api/profile` | `{ "name", "firstDate", "endDate" \| null, "repeatRule": "none"\|"weekly"\|"biweekly"\|"monthly" }` |
| Roster import | POST | `/api/people/import` | JSON `{ "filename", "text" }` or `{ "filename", "contentBase64" }` — not multipart |
| Add person | POST | `/api/people` | `{ "id", "name", "position"?, "center"?, "email"? }` |
| Edit person | PUT | `/api/people/{id}` | `{ "name", "position", "center", "email"? }` — id in the path only |
| Delete person | DELETE | `/api/people/{id}` | — |

JSON field names for new profile fields follow existing meta camelCase (`statusLabels`), not SQL snake_case. People resources keep the shipped keys (`id`, `name`, `position`, `center`, `email`). Validation is HTTP 400 or 422 except duplicate add, which is **409**. No OpenAPI. No bind-address change.

## Consequences

- Positive: Development and QA share one surface; wizard intercept can read `configured` from the meta call the SPA already makes.
- Negative / accepted cost: a developer who already drafted `POST /api/setup` must rename or alias.
- Follow-up: PLAN-yoklama-setup ACs must name this contract (architect plan-review F-2).
