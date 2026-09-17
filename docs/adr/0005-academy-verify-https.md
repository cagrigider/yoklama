# 0005 — Stdlib HTTPS to Claude Academy VerifyCertificate

- **Status:** accepted
- **Date:** 2026-09-17
- **Deciders:** operator (Çağrı Gider); implementation of Academy certificate tracking

## Context and Problem Statement

Yoklama is a local stdlib app with no partner APIs ([ARCHITECTURAL_PRINCIPLES.md](../../.factory/ARCHITECTURAL_PRINCIPLES.md) §1). Champions need to record that a roster person earned a Claude Academy completion badge. Academy publishes a public verify page and the same JSON RPC the page already calls. There is no official documented SDK, and pip is not allowed on the core path.

## Considered Options

- Manual trust: paste a URL, store it without a live check
- Scrape the HTML verify page
- **Stdlib `urllib.request` POST to the public `VerifyCertificate` JSON RPC**, isolated behind one function
- Add a pip HTTP client

## Decision Outcome

Chosen option: **stdlib POST to** `https://academy.claude.com/api/anthropic.academy_public.api.v1alpha.AcademyPublicService/VerifyCertificate`, because it returns structured `valid`, `certificateName`, `courseTitle`, and `issuedAt` without new dependencies.

This is an **explicit exception** to “no partner APIs”. The call is outbound HTTPS from the champion’s machine, loopback bind is unchanged, and there is still no login.

**Contract**

- Treat only `valid === true` as a real badge (HTTP 200 with `{}` is not valid).
- Cloudflare WAF blocks Python-urllib’s default User-Agent (error 1010). Send a browser UA plus Origin/Referer, and treat Cloudflare/403/429 payloads as `academy_unreachable`, never as an invalid badge.
- Network/timeout/5xx → HTTP 503 `academy_unreachable`; fail closed; never force-accept.
- Tests replace `fetch_academy_badge` (or pass `fetcher=`) so the suite never hits Academy.
- Catalog titles are champion-maintained; match `courseTitle` with the same Turkish/ASCII fold as names.

## Consequences

- Positive: live check, unique `verify_code` in the local DB, course mapping without scraping.
- Negative / accepted cost: undocumented RPC can change; isolate it so a break is one adapter. Name on the badge is editable on Academy; uniqueness of `verify_code` is the anti-reuse control.
- Follow-up: if the RPC disappears, parse the public HTML page or fail closed with a Turkish connection error.
