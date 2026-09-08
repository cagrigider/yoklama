# Unit Tester Profile

<!-- factory-version: 1.3.0 -->
> unit-tester tuning — the RUN side (the test command lives in build-profile).
> Last updated: 2026-09-08

## Test Frameworks
- None in the tree yet. When added: pytest (preferred) or unittest. Do not add a test runner as an app runtime dependency.

## Coverage Targets
- TBD (no suite yet)

## Run Conventions
- There is no test command until a suite exists — report “no tests” rather than inventing a runner
- When added: `python3 -m pytest` from the project root, or `python3 -m unittest discover`
- Never point tests at the operator’s `data/attendance.db`; use an isolated temp tree or a documented `YOKLAMA_DATA_DIR` / temp DB
- Parallelism: TBD (single-process SQLite — default serial)
- Flaky-test handling: TBD
