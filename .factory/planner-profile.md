# Planner Profile

<!-- factory-version: 1.3.0 -->
> planner-agent tuning + project planning conventions. Read by the `planner`.
> The canonical plan schema (JSON shape, typed dependencies, parallelism analysis block,
> import field-mapping) lives in **`claude-plugin/references/plan-schema.md`** and is
> injected into the planner's prompt by the `/factory:plan` skill — it is NOT embedded here.
> Last updated: 2026-09-08

## Canonical Schema

The structural plan schema is the single source of truth at:
**`claude-plugin/references/plan-schema.md`**

The `/factory:plan` skill reads that file (main thread) and injects its contents into the
planner subagent's prompt. The planner follows the injected schema exactly. This file holds
**conventions only** — no schema copy here.

## Planning Conventions
- Hierarchy: epics → stories → tasks (no spikes for now)
- Estimation units: TBD
- Definition of Done: TBD (working default: code + ADR if a decision was made + isolated-temp verification; no pip; PII not committed)
- Labels / components: TBD (`app`, `static`, `docs` as informal scopes)

## Slicing Granularity
- How finely the planner slices is governed by the canonical rubric at
  **`claude-plugin/references/granularity-rubric.md`**, injected into the planner's prompt by
  `/factory:plan` (prefixed with an `ACTIVE CONFIGURATION` block). Not embedded here — pointer only.
  Every closed set and bound: `node claude-plugin/servers/lib/granularity.mjs --schema`.
- **The floor is semantic (`scope`), the ceiling is quantitative (files/tokens/layers, derived from
  the executor's context window).** Acceptance criteria are coverage and never size a task.
- Project settings live in `.factory/config.json` → `planning` (see below), not here.
- Per-run override: `/factory:plan <requirement> --granularity <capability|layer|artifact>` (alias
  `-g`), plus `--scope` / `--axis` / `--max-files` / `--objective`.
- Project default: capability (`planning.granularity.preset` absent = `capability`)
- Split policy (detected): no separate migrations deploy (SQLite ALTER in `app.py`) → `migration: shared`; no test suite yet (colocated when added) → `tests: folded`; no OpenAPI/generated client → `contracts: folded`; SPA hash states → `screen_states: folded`; JSON `Handler` families → `endpoints: per-family`

## Concurrency Conventions
- Every plan the planner produces must include a **parallelism analysis**: wave schedule (tasks
  per parallel frontier), critical path (longest FS chain, hop-count proxy), and max concurrency
  width — in both `PLAN-*.md` (human-readable `## Parallelism analysis` section) and the
  `parallelism` block in `PLAN-*.json`.
- The wave shape is an **output of the real dependency graph**, never a target the graph is bent
  to hit. Pick the loosest-correct dependency type; never fabricate, drop, or retype a real edge;
  never over-fragment a coherent task to inflate parallelism.
- Concurrency is maximized **within the granularity floor** — never slice below the active scope's
  floor to widen a wave. At `capability` scope, an honest `max_concurrency_width: 1` is a correct
  plan. Cutting vertically usually buys fewer tasks *and* more parallelism, since vertical slices are
  independent while layer slices chain.
- The analysis block shape is defined in `claude-plugin/references/plan-schema.md`.
- Existing plan to preserve: `.factory/plans/PLAN-yoklama-setup.md`

## Sequential thinking
The bundled `sequentialthinking` reasoning tool (`factory-sequentialthinking` MCP) is **off by default**. Set `Status` to `enabled` to let the planner use it — and even then only when a requirement is genuinely tangled enough to benefit (routine slicing never triggers it). Any value other than `enabled`, or a missing section, reads as disabled.

Status: disabled
