# QA Engineer Profile

<!-- factory-version: 1.3.0 -->
> qa-engineer tuning. Read by the `qa-engineer`.
> Last updated: 2026-09-08

## Execution Environment
- Bring the app up from an **isolated temp tree** (rsync excluding `data/*.db` and `seed/people.json`), then `python3 app.py`. Never open the operator’s `data/attendance.db`. If 8765 is busy, stop that process — do not retarget the operator DB. Teardown: SIGINT the server; `rm -rf` the temp tree; do not copy the test DB onto `data/`.
- Tooling: cURL for `/api/*`; Playwright CLI (Chromium) for wizard/Settings/people/live tick; `git ls-files` for gitignore/README. Python 3 stdlib — no extra packages required to start the app.
- Existing plan: `.factory/test-plans/TESTPLAN-yoklama-setup.md`.
- **Assertion-timeout re-probe** — on a visibility/presence assertion timeout, do **one** markedly-longer re-probe before any regression verdict (never a loop). Extended budget = default assertion budget × **multiplier** `×5`, capped at **ceiling** `30000 ms`. Element appears within the extended budget → `slow-render` (records T1 budget + T2 appeared; not a FAIL); still absent → FAIL (genuine DOM/selector regression).

## Evidence & Reporting
- Evidence: cURL request/response (status + body), Playwright screenshot/trace, server stderr, `git ls-files` excerpts. Mask PII.
- **PII/secret masking (on by default).** Captured evidence (DOM/accessibility snapshots, response bodies, logs) can embed **real** personal data when the app under test renders it. Mask sensitive spans **as evidence is transcribed** into the report — detect by pattern (email/phone/Luhn-valid card/national-id/token shapes) **and** by label/accessibility-name context (`password`/`token`/`authorization`/`email`/`user`/`created-by`/`ssn`/`phone`/`card`/`sicil`). Two tiers: secrets → fixed-width placeholder (content **and** length hidden); identifying PII → partial deterministic mask keeping a small anchor (`mi•••@ad•••.com.tr`, `+90 ••• ••• •• 67`, `•••• •••• •••• 4242`). Unclassifiable → full mask (fail-safe). Structural fields (ids, `traces_to`, selectors, expected results) are never masked. Extra sensitive labels: `sicil`, `name` on roster rows when evidence might be from a non-synthetic DB (should not happen if isolated runtime is followed).

## QA Report JSON Schema (QAREPORT-{slug}.json)
{
  "test_plan": "TESTPLAN-{slug}",
  "mode": "inline | regression",
  "generated_by": "qa-engineer",
  "summary": { "total": 0, "passed": 0, "failed": 0, "blocked": 0, "slow_render": 0, "pass_rate": "0%" },
  "cases": [
    { "id": "TC-1", "traces_to": ["..."], "result": "pass | fail | blocked | slow-render",
      "failed_phase": "setup | run | null", "blocked_by": "<precondition-signature> | null",
      "reprobe": { "budget_ms": 0, "extended_ms": 0, "appeared_at_ms": 0 },
      "expected": "...", "actual": "...", "evidence": "...", "notes": "..." }
  ],
  "precondition_blocks": [
    { "precondition": "<failed shared setup step>", "affected_cases": ["TC-2", "TC-3"], "classification": "precondition-blocked",
      "kind": "env | auth | network | seed | null", "missing": "<the specific unmet prerequisite, named — never a guessed value>", "remediation": "<how the operator unblocks it>" }
  ]
}
