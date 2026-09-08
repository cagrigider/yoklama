# Web UI Tester Profile

<!-- factory-version: 1.3.0 -->
> web-ui-tester tuning — Playwright web UI suite conventions. Read by the `web-ui-tester`.
> Last updated: 2026-09-08

## Suite Layout
- Spec directory: none yet (`playwright.config.*` absent). Default: `webui/` with `webui/specs/` + `webui/helpers/`; config at the project root when first authored
- Naming: `<flow>.spec.ts`

## Selector Policy
- Prefer getByRole / getByLabel / getByTestId; no positional or deep-CSS chains.
- Test-id attribute: TBD (today: `data-nav` on tabs, `#app` mount; no `data-testid`). Product copy is Turkish — role/name locators must use Turkish accessible names, not English spec strings.

## Runtime
- App start for testing: `python3 app.py` from an **isolated temp tree** (never the operator `data/attendance.db`). See TESTPLAN-yoklama-setup isolated runtime.
- baseURL: http://127.0.0.1:8765
- Browser matrix: chromium
- Run mode: headless default; both headless and headful supported — `--headed` (specs) / `headless: false` (live-drive) override

## Web UI Test Report JSON Schema (WEBUIREPORT-{slug}.json)
{
  "test_plan": "TESTPLAN-{slug} | null",
  "mode": "author-and-run | run-only | author-only",
  "generated_by": "web-ui-tester",
  "command": "npx playwright test ...",
  "environment": { "playwright": "...", "node": "...", "browsers": ["chromium"], "headed": false, "base_url": "http://127.0.0.1:8765" },
  "summary": { "total": 0, "passed": 0, "failed": 0, "flaky": 0, "skipped": 0,
               "pass_rate": "0%", "duration_ms": 0 },
  "specs": [ { "path": "webui/specs/....spec.ts", "status": "created | updated | unchanged",
               "covers": ["TC-1"] } ],
  "cases": [
    { "id": "TC-1", "spec": "webui/specs/....spec.ts", "traces_to": ["..."],
      "result": "pass | fail | blocked", "duration_ms": 0,
      "expected": "...", "actual": "...",
      "verdict": "product-wrong | test-wrong | env-wrong | null",
      "evidence": { "screenshot": "...", "trace": "..." }, "notes": "..." }
  ],
  "degraded": ["..."],
  "flaky_reruns": [ { "id": "TC-3", "first": "fail", "rerun": "pass" } ]
}
