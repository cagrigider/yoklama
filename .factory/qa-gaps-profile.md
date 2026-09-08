# QA Gaps Profile

<!-- factory-version: 1.3.0 -->
> qa-gaps tuning. Read by the `qa-gaps` agent.
> Last updated: 2026-09-08

## Gap categories
- Missing HTTP handlers vs FRD, unhandled error bodies, SPA dead-ends (unconfigured chrome still showing Toplantılar/Kişiler), schema vs ADR drift

## API spec location
- No OpenAPI/Swagger. Source of truth: `app.py` `Handler` plus ADRs in `docs/adr/` (especially ADR-0004 JSON HTTP contract)

## Severity scheme
- blocker / major / minor — TBD mapping to P0–P2

## Error-code matrix defaults
- In-scope for “expected-error-code handled?”: `{400, 404, 409, 422, 500, timeout}`
- N/A by default: `{401, 403, 429, 502, 503}` (no auth, no rate limit, single local process)
