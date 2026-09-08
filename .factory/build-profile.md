# Build Profile

<!-- factory-version: 1.3.0 -->
> Build/run config. Read by /factory:build (inline), the developer (builds clean before completing), the unit-tester (runs tests), and the unit-test-engineer (compiles new tests).
> Last updated: 2026-09-08

## Commands
- Build: `python3 -m py_compile app.py` (no compile/bundle step; syntax check only)
- Run: `python3 app.py` — serves http://127.0.0.1:8765
- Test: `python3 -m unittest discover -s tests -v` (stdlib unittest; no pytest)
- Clean: `find . -type d -name __pycache__ -prune -exec rm -rf {} +` (never delete `data/attendance.db`)
- Lint / format: TBD (no ruff/black/eslint in repo; stdlib only — do not add a formatter as a runtime dependency)

## Variants / Configurations
- Local loopback only (HOST=`127.0.0.1`, PORT=`8765` in `app.py`)
- No debug/release flavors, no staging/production deploys

## Outputs
- No packaged artifact (no wheel, APK, IPA, or SPA bundle)
- Runtime database: `data/attendance.db` (operator machine; gitignored)
- Syntax-check success is a zero exit from `python3 -m py_compile app.py`
