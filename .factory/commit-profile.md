# Commit Profile

<!-- factory-version: 1.3.0 -->
> commit-agent tuning.
> Last updated: 2026-09-08

## Commit Conventions
- Format: existing history uses imperative prose sentences (e.g. “Share Yoklama as a local-only app…”). Prefer Conventional Commits going forward (`feat`, `fix`, `docs`, `chore`) when the factory commit agent writes messages; do not rewrite old history.
- Scopes: free-form; useful values: `app`, `static`, `docs`, `seed`
- Footer / sign-off: TBD (issue refs optional; no required sign-off)
- Never stage `data/*.db`, `seed/people.json`, `.factory/.env`, or spreadsheet rosters
