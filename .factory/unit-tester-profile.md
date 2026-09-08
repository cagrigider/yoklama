# Unit Tester Profile

<!-- factory-version: 1.3.0 -->
> unit-tester tuning — the RUN side (the test command lives in build-profile).
> Last updated: 2026-09-08

## Test Frameworks
- **unittest** (stdlib). Do not add pytest or any pip package.

## Coverage Targets
- TASK-1.1.1 fill-gaps + TASK-1.2.3 people CRUD helpers (see `tests/`)

## Run Conventions
- From project root: `python3 -m unittest discover -s tests -v`
- Never point tests at the operator’s `data/attendance.db`; the suite uses `tests/tempdb.py` isolated temp files
- Parallelism: serial (single-process SQLite)
- Flaky-test handling: TBD
