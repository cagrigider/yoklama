# Test Designer Profile

<!-- factory-version: 1.3.0 -->
> test-designer tuning + the test-plan template and JSON schema. Read by the `test-designer`.
> Last updated: 2026-09-08

## Test Plan Template
- Standard: IEEE 829 (default). Existing plan: `.factory/test-plans/TESTPLAN-yoklama-setup.md` (+ JSON twin).

## Scope & Coverage
- Integration tests, traced to plan acceptance criteria. Coverage expectation: every P0/P1 acceptance criterion.
- Isolated temp runtime is mandatory — never open the operator Grup 8 `data/attendance.db`.

## Synthetic data defaults
- Default all synthetic PII/fixtures to the reserved, non-routable ranges in `claude-plugin/references/safe-synthetic-data.md` (RFC 2606 domains `@example.com`, reserved phone blocks `555-01NN`, RFC 5737 IPs `192.0.2.0/24`, standard test cards `4242…`, obviously-fictional names/IDs) — never a real corporate domain, live phone, or routable IP. Use `seed/people.example.json` as the roster shape. Never copy a real champion roster.

## Test Technique (by platform, from project-profile)
- Backend/API → cURL against http://127.0.0.1:8765 · Web → Playwright CLI (Turkish locators) · Mobile → not applicable.
- README / gitignore checks → `integration` (`git ls-files`).

## Error-code coverage defaults
- Per testable API operation, walk the canonical error-code matrix (`claude-plugin/references/error-code-matrix.md`) and design a negative/boundary case per **applicable** code — or an N/A stub (`reason: "not-applicable"`) when it can't arise. Applicability, not blanket generation.
- In-scope-by-default codes: `{400, 404, 409, 422, 500}` — `401`/`403` N/A (no auth); `429` N/A (no rate limit); `502/503` N/A (single local process). Timeout still in-scope for a hung handler.
- Validation may be 400 or 422 unless an AC requires **409** (duplicate person add).
- Hygiene cases generated **above** the FRD's explicit acceptance criteria are tagged `hygiene` / `above-FRD`.

## Test Plan JSON Schema (canonical output for TESTPLAN-{slug}.json)
{
  "requirement": "REQ-{slug}",
  "plan": "PLAN-{slug}",
  "generated_by": "test-designer",
  "test_plan": {
    "identifier": "TESTPLAN-{slug}",
    "introduction": "...",
    "test_items": ["..."],
    "features_to_test": ["..."],
    "features_not_to_test": ["..."],
    "approach": "...",
    "pass_fail_criteria": "...",
    "suspension_resumption": "...",
    "environmental_needs": "...",
    "risks": ["..."]
  },
  "test_cases": [
    {
      "id": "TC-1",
      "traces_to": ["TASK-1.1.1#AC1", "TASK-1.1.1#AC2"],
      "title": "...",
      "setup": "preconditions + how to get the software running",
      "technique": "curl | playwright-cli | accessibility | integration",
      "steps": ["..."],
      "test_data": "...",
      "expected_result": "...",
      "teardown": "..."
    }
  ],
  "excluded_coverage": [
    { "excluded": "<scenario/behavior deliberately NOT covered here>", "reason": "already-covered-by-existing-asset", "covered_by": "<verifiable pointer: TC id / spec / suite / file:path>" }
  ],
  "traceability": {
    "_computed": "Written by /factory:plan step 5b via servers/lib/plan-verify.mjs — NOT hand-authored.",
    "test_case_total": 0,
    "tasks": { "total": 0, "covered": [], "uncovered": [] },
    "acceptance_criteria": { "total": 0, "traced": 0, "untraced": [], "unverified": 0, "granularity": "per-ac | task-level", "verdict": "complete | partial | unverified" }
  }
}

**`traces_to` references acceptance criteria by ID:** `TASK-KEY#ACn` = criterion *n* (1-based) of that task's `acceptance_criteria[]`; a bare `TASK-KEY` is task-level only (cannot certify per-AC coverage). The **`traceability`** block is **computed** from the test cases' `traces_to` against the plan's task ACs by the `/factory:plan` flow — never self-reported. `verdict` is `complete` only when every task AC is AC-traced and covered; `partial` when an AC has no test; `unverified` when a task is traced only at task level. See `references/plan-schema.md`.
