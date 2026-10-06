# 0005 — Stdlib HTTPS to Claude Academy and Skilljar verify

- **Status:** accepted
- **Date:** 2026-09-17
- **Deciders:** operator (Çağrı Gider); implementation of Academy/Skilljar certificate tracking

## Context and Problem Statement

Yoklama is a local stdlib app with no partner APIs ([ARCHITECTURAL_PRINCIPLES.md](../../.factory/ARCHITECTURAL_PRINCIPLES.md) §1). Champions need to record that a roster person earned a Claude Academy or Skilljar completion badge. Academy publishes a public verify page and the same JSON RPC the page already calls. Skilljar publishes a public HTML certificate page (`verify.skilljar.com/c/{slug}`) with no documented JSON RPC. There is no official SDK, and pip is not allowed on the core path.

## Considered Options

- Manual trust: paste a URL, store it without a live check
- Scrape the HTML verify page (Skilljar has no JSON; Academy has JSON)
- **Stdlib `urllib.request`:** Academy `POST` to public `VerifyCertificate` JSON RPC; Skilljar `GET` of the public HTML page; both isolated behind `fetch_live_badge`
- Add a pip HTTP client

## Decision Outcome

Chosen option: **stdlib outbound HTTPS**, because it returns structured student name, course title, and completion time without new dependencies.

- Academy: `POST` `https://academy.claude.com/api/anthropic.academy_public.api.v1alpha.AcademyPublicService/VerifyCertificate` → `valid`, `certificateName`, `courseTitle`, `issuedAt`.
- Skilljar: `GET` `https://verify.skilljar.com/c/{slug}` → parse visible **Student**, **Course Completed**, **Completion Date** (`Sept. 3, 2026` stored as ISO date, no time of day).

This is an **explicit exception** to “no partner APIs”. The call is outbound HTTPS from the champion’s machine, loopback bind is unchanged, and there is still no login.

**Contract**

- Treat only a successful parse with a name and course title as a real badge (Academy HTTP 200 with `{}` is not valid; Skilljar HTML without Student/Course is not valid).
- Cloudflare WAF blocks Python-urllib’s default User-Agent (error 1010). Send a browser UA (Academy also Origin/Referer), and treat Cloudflare/403/429 payloads as `academy_unreachable`, never as an invalid badge.
- Network/timeout/5xx → HTTP 503 `academy_unreachable`; fail closed; never force-accept.
- Tests replace the fetcher (`fetcher=` or `fetch_live_badge`) so the suite never hits the network.
- Catalog titles are champion-maintained; match course title with Turkish/ASCII fold; `&` and `and` are the same.
- Catalog rows may store two optional URLs (`url`, `url2`); a person still has at most one badge per catalog course. Issuer (`academy` / `skilljar`) is stored on the assignment and shown as **Claude Academy** or **Skilljar**.

## Consequences

- Positive: live check, unique `verify_code` in the local DB, course mapping without a pip client.
- Negative / accepted cost: undocumented RPC/HTML can change; isolate adapters so a break is one function. Name on the badge can be edited at the issuer; uniqueness of `verify_code` is the anti-reuse control.
- Follow-up: if Academy RPC disappears, parse the public HTML page; if Skilljar markup changes, fail closed with a Turkish connection or validation error.
