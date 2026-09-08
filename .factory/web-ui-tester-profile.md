# Web UI Tester Profile

<!-- factory-version: 1.3.0 -->
> web-ui-tester tuning — Playwright web UI suite conventions. Read by the `web-ui-tester`.
> Last updated: 2026-09-09

## Suite Layout
- Spec directory: `webui/specs/` + `webui/helpers/`; `playwright.config.ts` at the project root
- Naming: `<flow>.spec.ts` (`wizard-gate`, `wizard-empty-roster`, `settings`, `live-tick`, `import`, `people`)
- Isolation helper: `webui/helpers/isolated-app.mjs` (copy tree excluding `data/*.db` and `seed/people.json`; never operator DB)

## Selector Policy
- Prefer getByRole / getByLabel / getByTestId; no positional or deep-CSS chains.
- Test-id attribute: TBD (today: `data-nav` on tabs, `#app` mount, `#wizard-form` / `#settings-import` / `#settings-roster-file` / `#person-id`). Product copy is Turkish — role/name locators must use Turkish accessible names, not English spec strings.
- Live roster: `.person-row` scoped by person name + `getByRole('button', { name: 'Katıldı'|'Gelmedi' })`. People delete uses `getByRole('dialog')`.
- Between live-tick PUTs wait ~600ms — product `armInputLock` is 500ms.

## Runtime
- App start for testing: Playwright `webServer` runs `node webui/helpers/isolated-app.mjs --port 18765` (copies to `/tmp/yoklama-setup-*`, `python3 app.py` from that copy). Never `data/attendance.db`.
- baseURL: http://127.0.0.1:18765 (dedicated test bind; **not** operator 8765)
- Shared DB reset between tests via sqlite DELETE on the temp copy; TC-12 starts a second isolated copy with synthetic `seed/people.json`
- Browser matrix: chromium
- Run mode: headless default; both headless and headful supported — `--headed` (specs) / `headless: false` (live-drive) override
- Workers: 1 (`fullyParallel: false`) so the shared isolated DB reset stays serial

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
