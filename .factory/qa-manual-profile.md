# QA Manual Profile

<!-- factory-version: 1.3.0 -->
> qa-manual tuning. Read by the `qa-manual` agent.
> Last updated: 2026-09-08

## Test categories
- First-run wizard / Settings, series fill-gaps, roster import, people CRUD, live tick, loopback bind, gitignore of PII

## Priority scheme (P0–P2)
- P0: isolated DB, loopback bind, no PII on git, live tick, fill-gaps never deletes
- P1: import validation, people 409, Turkish UI
- P2: extras, copyable summaries, README column contract

## Scope
- full | feature | PR — default feature for yoklama-setup; full for regression

## Synthetic-data defaults
- Reserved/non-routable ranges from `claude-plugin/references/safe-synthetic-data.md` — RFC 2606 domains, `555-01NN` phones, RFC 5737 IPs, standard test cards; project overrides: use `seed/people.example.json` shape only. Allowed real values: none.
