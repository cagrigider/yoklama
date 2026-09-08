# Security Scan Report

## Summary
- **Scan Date**: 2026-09-09
- **Scope**: Sprint diff `ff2221f..HEAD` (yoklama-setup feat commits) plus current tree secret scan
- **Status**: NEEDS ATTENTION
- **Sprint halt**: No (zero Critical / High)
- **Critical Issues**: 0
- **High Issues**: 0
- **Medium Issues**: 1
- **Low Issues**: 2
- **Informational**: 3

Login, CSRF, and TLS were not scored (local single-user loopback, per `.factory/security-profile.md`). Missing authentication on `127.0.0.1` is in-scope as a non-finding.

## Findings by Category

### Secrets and Credentials

No hardcoded production or development secrets were found in the tracked tree or in `git diff ff2221f..HEAD`.

| Check | Result |
|-------|--------|
| API keys / AWS / GitHub / Slack tokens / private keys | None |
| `.factory/.env` / root `.env` | Absent on disk; gitignored |
| `.factory/.env.example` | Tracked placeholder (`GITHUB_TOKEN=` empty) |
| `seed/people.json` | Present locally, **gitignored**, never in `git ls-files` or this sprint’s history |
| `data/attendance.db` | Present locally, **gitignored** (`data/*.db`) |
| Tracked seed | `seed/people.example.json` only — synthetic `ornek@example.com` |

**Remediation:** None. Keep `data/*.db`, `seed/people.json`, `*.xlsx`/`*.xls`/`*.csv`, and `.factory/.env` gitignored. Do not copy local roster files into commits or CI logs.

### Dependency Vulnerabilities

No third-party runtime dependencies. No `requirements.txt`, `package.json`, Pipfile, or `pyproject.toml`. Import path uses stdlib only (`csv`, `json`, `zipfile`, `xml.etree`). No `openpyxl` / pip / npm added in this sprint.

| Package | Version | CVE | Severity | Fixed Version |
|---------|---------|-----|----------|---------------|
| — | — | none | — | — |

### Code Security Issues

#### MEDIUM - Unescaped person id in live roster HTML
- **Location**: `static/js/app.js` (`personCard`, ~726 and ~734)
- **Category**: A03 Injection (stored XSS)
- **Description**: Roster names, notes, and People-list ids go through `escapeHtml`. The live-tick card interpolates `p.id` raw into `data-id` and `href`. Sicil is attacker-controlled after `POST /api/people/import` (or a manual add).
- **Risk**: A poisoned xlsx/csv/json with a sicil such as `x" onmouseover="…"` can break out of the attribute on `#/meeting/{id}`. In the operator’s browser that origin can read `/api/people` and `fetch` the roster to an external host. This is not a remote unauthenticated bug (loopback + operator must import the file) so it does not halt the sprint.
- **Evidence**: `peopleRow` uses `escapeHtml(p.id)`; `personCard` does not:
  ```
  <article class="person-row ${rowClass}" data-id="${p.id}">
  <a class="link-quiet" href="#/people/${p.id}">geçmiş</a>
  ```
- **Remediation**: Use the same helper as the People list:

```javascript
<article class="person-row ${rowClass}" data-id="${escapeHtml(p.id)}">
  …
  <a class="link-quiet" href="#/people/${encodeURIComponent(p.id)}">geçmiş</a>
```

`bindPersonRow` should keep using `row.dataset.id` (browser decodes the attribute). Prefer `encodeURIComponent` on hash links that include sicil (already done on the People screens).

#### LOW - Unbounded JSON / import body size
- **Location**: `app.py` `read_json` (~508–513) and `import_people` (`contentBase64`)
- **Category**: A04 Insecure Design (local resource exhaustion)
- **Description**: `Content-Length` is trusted with no cap. A huge base64 xlsx or a zip bomb inside stdlib `ZipFile.read` can exhaust memory on the operator machine. Malformed JSON is already mapped to HTTP 400.
- **Risk**: Local denial of service only; the operator (or malware already on the box) must send the request to `127.0.0.1`.
- **Remediation**: Reject `Content-Length` above a fixed ceiling (for example 5–10 MiB) before `rfile.read`, and refuse negative/non-integer lengths. Optionally skip xlsx members whose uncompressed size exceeds the same ceiling.

#### LOW - Static path prefix check is string `startswith`
- **Location**: `app.py` `serve_static` (~944–950)
- **Category**: A01 / path traversal (defense in depth)
- **Description**: After `Path.resolve()`, the handler allows a file only if `str(target).startswith(str(STATIC_DIR.resolve()))`. Requests such as `/../app.py` correctly 404 today because `…/attendance/app.py` does not start with `…/attendance/static`. The check would also match a hypothetical sibling path `static-backup/…`.
- **Risk**: No sensitive sibling of `static/` exists in this tree. PII lives under `data/` and `seed/`, which this prefix does not match.
- **Remediation**: Use `Path.is_relative_to` (Python 3.9+):

```python
root = STATIC_DIR.resolve()
target = (STATIC_DIR / rel).resolve()
if not target.is_relative_to(root) or not target.is_file():
    self._send(404, b"Not found", "text/plain")
    return
```

### Configuration Security

#### INFO - Loopback bind (pass)
- **Location**: `app.py` `HOST = "127.0.0.1"`; `ThreadingHTTPServer((HOST, PORT), Handler)`; tests assert `HOST == "127.0.0.1"`
- **Issue**: None. Not overridable via environment. Sprint diff does not introduce `0.0.0.0` or `::`.
- **Remediation**: Keep the constant; do not add a bind-address flag.

#### INFO - PII gitignore (pass)
- **Location**: `.gitignore`
- **Issue**: None. `data/*.db`, `seed/people.json`, spreadsheet/csv globs, and `.factory/.env` are ignored. `git check-ignore` confirms the local DB and roster.
- **Remediation**: None.

#### INFO - Request log line includes path (sicil in URL)
- **Location**: `Handler.log_message` → default request line on stdout
- **Issue**: `PUT/DELETE /api/people/{id}` prints sicil to the terminal. Profile forbids that in **committed docs / CI artifacts**, not in a local console.
- **Remediation**: Optional: log method + route template without the id, or skip logging `/api/people/*` write paths.

## Secure Code Examples

SQL in this sprint is parameterized (people CRUD, import upsert, profile, fill-gaps). Keep that pattern:

```python
conn.executemany(
    """
    INSERT INTO people (id, name, position, center, email)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        name = excluded.name,
        position = excluded.position,
        center = excluded.center,
        email = excluded.email
    """,
    [(p["id"], p["name"], p["position"], p["center"], p["email"]) for p in people],
)
```

xlsx sheet targets are read with `ZipFile.read` (archive member only, no `extractall`), so zip-slip to the filesystem is not in play. Keep it that way.

## Recommendations

### Immediate Actions (Critical/High)
None. Sprint may proceed.

### Short-term Improvements (Medium)
1. Escape (and URL-encode) `p.id` in `personCard` so import cannot inject HTML into the live roster.
2. Cap `Content-Length` on POST/PUT, especially `/api/people/import`.

### Long-term Security Enhancements (Low)
1. Switch `serve_static` to `is_relative_to`.
2. If the product ever leaves loopback, add auth, CSRF, and TLS — currently correctly out of scope.
3. Consider serving fonts locally instead of Google Fonts (`index.html` preconnects to `fonts.googleapis.com`); that is a privacy choice, not a vulnerability in the loopback model.

## Compliance Checklist

- [x] No hardcoded secrets in codebase
- [x] All dependencies on supported versions (stdlib only; no pip/npm)
- [x] HTTPS enforced for all network communication — N/A (loopback HTTP by design; TLS excluded)
- [x] Sensitive data encrypted at rest — N/A for local single-user SQLite; PII is gitignored
- [x] Proper authentication and authorization — N/A (no login by design)
- [x] Input validation on all user input — dates/enums validated; SQL parameterized; import fail-closed; **id HTML-escaped everywhere except live `personCard`**
- [x] Secure logging (no sensitive data) — no PII in git; local stdout may include sicil in URLs
- [ ] Security headers configured — not required for loopback; no CSP (informational)

## Performance Metrics
- Scan started: 00:37 (UTC+3)
- Scan completed: 00:45 (UTC+3)
- Duration: ~8 min
- Files scanned: 17 in `ff2221f..HEAD`; full tracked tree for secrets (~60 paths); `app.py`, `static/js/app.js`, `.gitignore`, seed example, tests
- Dependencies checked: 0 third-party packages
