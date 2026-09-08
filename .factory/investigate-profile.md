# Investigate Profile

<!-- factory-version: 1.3.0 -->
> investigate tuning. Read by the `investigate` agent.
> Last updated: 2026-09-08

## RCA Conventions
- Classification taxonomy: product defect | test defect | environment/setup.
- Where to look first: `app.py` Handler + SQLite schema; `static/js/app.js` hash routes; isolated-temp vs operator DB mix-up; bind address; gitignore of PII.
- Depth/evidence: cite file:line, HTTP status, SQL side effects (row counts before/after). Prefer reproducing in a temp tree.
- Common env-wrong: QA pointed at `data/attendance.db` on the operator machine; port 8765 already bound.

## RCA JSON Schema (RCA-{slug}.json)
{
  "qa_report": "QAREPORT-{slug}",
  "generated_by": "investigate",
  "findings": [
    { "case": "TC-1", "root_cause": "...", "classification": "product | test | environment",
      "evidence": "file:line / condition", "suggested_fix": "..." }
  ]
}

## Sequential thinking
The bundled `sequentialthinking` reasoning tool (`factory-sequentialthinking` MCP) is **off by default**. Set `Status` to `enabled` to let the investigate agent use it — and even then only when the root cause is genuinely knotty enough to benefit (a clear-cut failure never triggers it). Any value other than `enabled`, or a missing section, reads as disabled.

Status: disabled
