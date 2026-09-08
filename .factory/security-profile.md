# Security Profile

<!-- factory-version: 1.3.0 -->
> security-agent tuning.
> Last updated: 2026-09-09

## Security Concerns
- Bind loopback only (`127.0.0.1`); never listen on `0.0.0.0` or add a public host
- No authentication by design — treat the process as a local single-user tool, not a network service
- PII in SQLite (`data/attendance.db`) and `seed/people.json` must remain gitignored
- SQL injection: all queries parameterized; no string-built SQL from request bodies
- Static file serving: prevent path traversal out of `static/` (`Path.is_relative_to`, not only `str.startswith`)
- JSON body size / malformed JSON handling on POST/PUT (cap `Content-Length` before `rfile.read`)
- Do not log roster names, sicil, or emails in committed docs or CI artifacts
- No secrets in the repo (GitHub token lives in `.factory/.env` only)
- SPA `innerHTML`: escape **all** roster fields including `people.id` / sicil (`personCard` must match `peopleRow`)

## Scan Focus
- Secrets: tokens, `.env`, real roster JSON, SQLite dumps
- Injection: SQLite parameterization, path traversal on `STATIC_DIR`
- Dependency advisories: none expected (stdlib only); flag any new pip/npm add as a policy violation unless an ADR allows it
- OWASP: security misconfiguration (bind address), sensitive data exposure (git of PII), injection

## Exclusions
- Missing login / CSRF / TLS — out of product scope (local loopback, no auth)
- Hosted multi-user threat model — TBD if the product ever leaves loopback
