# Unit Test Engineer Profile

<!-- factory-version: 1.3.0 -->
> unit-test-engineer tuning — the AUTHORING side (writes/updates tests).
> Last updated: 2026-09-08

## Test Frameworks
- **unittest** (stdlib). Do not add pytest or any pip package. Discover: `python3 -m unittest discover -s tests -v` from the project root.

## Authoring Conventions
- Structure: Arrange-Act-Assert
- Naming: `test_<behavior>` in `tests/test_*.py`
- Import bootstrap: insert project root (and `tests/`) on `sys.path` so `from app import …` works under discover `-s tests`
- Mocking strategy: do not mock SQLite for persistence tests — use `tests/tempdb.py` `IsolatedDbTestCase` (temp file + monkeypatch `app.DB_PATH` / `app.SEED_PATH`). Never open `data/attendance.db`. Never call `init_db()` / `seed_people()` (those would load real `seed/people.json`)
- Test the Python helpers the HTTP handlers call (`fill_gap_meetings`, `insert_person`, `update_person`, `delete_person`). Do not start a long-lived server on 8765
- Fixtures: synthetic people only (`seed/people.example.json` style); RFC 2606 emails; never copy Grup 8 PII / `seed/people.json`

## Coverage Priorities
- Additive schema / group_profile upgrade insert (no DROP, no seed rebuild)
- Series fill-gaps (insert missing dates only; shortening end date never deletes)
- Import all-or-nothing validation; upsert on sicil; absentees not deleted
- People CRUD 409 on duplicate; immutable id
- Live tick remains a single-row upsert
- HTTP handler unit tests vs isolated-temp integration: prefer helpers; in-process `ThreadingHTTPServer` on `127.0.0.1:0` only if a route cannot be reached through a helper
