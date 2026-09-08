# Unit Test Engineer Profile

<!-- factory-version: 1.3.0 -->
> unit-test-engineer tuning — the AUTHORING side (writes/updates tests).
> Last updated: 2026-09-08

## Test Frameworks
- None yet. Prefer pytest; unittest is acceptable if pytest is not introduced. Do not add pip packages to the *app* runtime.

## Authoring Conventions
- Structure: Arrange-Act-Assert
- Naming: `test_<behavior>` in `tests/` (or `test_*.py` beside `app.py` if the first suite stays tiny)
- Mocking strategy: do not mock SQLite for persistence tests — use a temp DB. Mock only process boundaries (filesystem import fixtures, clock/date if needed)
- Fixtures: synthetic people only (`seed/people.example.json` style); RFC 2606 emails; never copy Grup 8 PII

## Coverage Priorities
- Additive schema / group_profile upgrade insert (no DROP, no seed rebuild)
- Series fill-gaps (insert missing dates only; shortening end date never deletes)
- Import all-or-nothing validation; upsert on sicil; absentees not deleted
- People CRUD 409 on duplicate; immutable id
- Live tick remains a single-row upsert
- TBD: HTTP handler unit tests vs isolated-temp integration (see test-designer / existing TESTPLAN-yoklama-setup)
