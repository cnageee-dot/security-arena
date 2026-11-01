# Security Arena Report - TinyBoard fixture (fictional) - Red run 1

> Raw output of the Red Team role. Written without opening `tests/fixtures/expected-findings.md`. NOT a blind test: see "Independence caveat" in `tests/results/evaluation.md`.

- **Mode:** red
- **Date:** 2026-10-31
- **Scope:** `tests/fixtures/vulnerable-demo/` (confirmed at CP0). Static review only.
- **Reviewer:** AI-assisted review (Security Arena skill, Red Team role)

## 1. Summary

Eight findings: 4 High, 2 Medium, 2 Low. No dynamic tests were run.

| Critical | High | Medium | Low | Info |
|---------:|-----:|-------:|----:|-----:|
| 0 | 4 | 2 | 2 | 0 |

## 2. Scope and method

- Environment: local files only; no process started; no network; no dependency install (CP1 not requested).
- Checkpoints: CP0 confirmed; CP4 approved for this file.
- Examined: `server.js` (all routes), `README.md`, `uploads/`.
- Not examined: runtime behavior, HTTP-level behavior of Node's parser, deployment (none present).

## 3. Findings

### SEC-001 - Any logged-in user can read any note
Severity: High   Confidence: confirmed
Location: `server.js:79-85`
Category: Broken object-level authorization
Description: `GET /api/notes/:id` finds the note by id and returns it without comparing `note.ownerId` to the requester. The list route at `server.js:76` does filter by owner, which shows the intended policy.
Attack scenario: bob (id 2) requests `/api/notes/1` and `/api/notes/3`, which belong to alice.
Evidence: `const note = notes.find((n) => n.id === Number(noteMatch[1])); ... return sendJson(res, 200, note);`
Impact: Disclosure of every user's notes; ids are small sequential integers.
Recommendation: Require `note.ownerId === user.id` (return 404 otherwise).

### SEC-002 - Path traversal in file download (unauthenticated)
Severity: High   Confidence: confirmed
Location: `server.js:104-111`
Category: Path traversal
Description: `name` is joined to `UPLOAD_DIR` with `path.join` and read; `..` segments are not rejected and the route runs before any authentication check.
Attack scenario: `GET /files?name=../server.js` reads source code (including the signing key, SEC-004) with no login.
Evidence: `fs.readFile(path.join(UPLOAD_DIR, name), ...)`; `path.join` normalizes `..` and does not confine the result.
Impact: Arbitrary file read as the server user; with SEC-004, a full compromise chain.
Recommendation: Use `path.basename`, or resolve and verify the result starts with `UPLOAD_DIR + path.sep`; consider requiring auth.

### SEC-003 - Reflected XSS in search page
Severity: Medium   Confidence: confirmed
Location: `server.js:92-96`
Category: Cross-site scripting
Description: `q` is placed inside an HTML response with `Content-Type: text/html` with no escaping.
Attack scenario: A crafted link with a script payload in `q` runs in the victim's browser on the app origin.
Evidence: `` `<h1>Results for ${q}</h1>...` ``
Impact: Script execution in the page context. Limited by the fact that the token is sent via an Authorization header (no cookie evident), so session theft depends on how a client stores the token (not visible in this code).
Recommendation: Use `escapeHtml(q)` (already defined at `server.js:43`).

### SEC-004 - Hardcoded token signing key lets anyone forge tokens
Severity: High   Confidence: confirmed
Location: `server.js:13`, `server.js:28-31`
Category: Hardcoded secret / broken authentication
Description: The HMAC key is a string literal in source, and the token content is only the user id, so anyone who reads the source (or obtains it via SEC-002) can compute a valid token for any user id.
Attack scenario: Compute `1.<hmac_sha256(key, "1")>` and call authenticated routes as user 1 (alice, role admin).
Evidence: `const SIGNING_KEY = 'tinyboard-demo-signing-key';` (fictional value).
Impact: Full authentication bypass.
Recommendation: Load the key from the environment/secret store and fail to start if absent; rotate; add expiry and a random component to tokens.

### SEC-005 - User list exposes password hashes and emails to any user
Severity: High   Confidence: confirmed
Location: `server.js:87-90`
Category: Sensitive data exposure
Description: `/api/users` returns the full `users` array, including `passwordHash` and `email`, to any authenticated user.
Evidence: `return sendJson(res, 200, users);` with `passwordHash` defined at `server.js:18-19`.
Impact: Offline cracking of hashes; combined with SEC-006, trivial.
Recommendation: Return only public fields (id, name) and restrict the route.

### SEC-006 - Passwords hashed with unsalted MD5
Severity: Medium   Confidence: confirmed
Location: `server.js:15`, `server.js:18-19`, `server.js:67`
Category: Weak cryptography
Description: Fast, unsalted MD5 is used for password verification.
Impact: Hashes are quickly crackable; identical passwords produce identical hashes.
Recommendation: Use scrypt/argon2/bcrypt with a per-user salt.

### SEC-007 - Non-constant-time MAC comparison, no token expiry, no login throttling
Severity: Low   Confidence: likely (timing: hypothetical in practice)
Location: `server.js:39`, `server.js:64-70`
Category: Authentication hardening
Description: `mac !== expected` is a short-circuit string comparison; tokens never expire; `/login` has no rate limit.
Impact: Weak-in-theory timing leak; unlimited password guessing; tokens valid forever once issued.
Recommendation: `crypto.timingSafeEqual`, add `exp` to tokens, throttle `/login`.

### SEC-008 - Unbounded request body in login
Severity: Low   Confidence: likely
Location: `server.js:52-58`, `server.js:66`
Category: Resource exhaustion
Description: `readBody` appends all data with no size limit, on an unauthenticated route.
Impact: Memory exhaustion by a large POST. Not demonstrated (no dynamic test; CP1 not requested).
Recommendation: Cap body size and reject early.

## Unverified leads

- `/files` with an absolute-looking or encoded `name` (e.g. percent-encoded separators): `URL.searchParams` decodes values, so encoded `..%2f` should behave like SEC-002; not tested dynamically.
- Whether a client stores the token in a way that makes SEC-003 session-stealing (no client code in scope).

## Reviewed and not reported

- `GET /profile`: output is passed through `escapeHtml` (`server.js:101`).
- `GET /avatar`: `path.basename` is applied before the join (`server.js:114`), so traversal does not apply there.
- `GET /api/notes` (list): filtered by owner.
- The `role` field is never checked anywhere, and no admin-only routes exist, so no privilege-escalation finding is claimed.

## 6. Residual risk and coverage

- Static review of one 125-line file; no dynamic confirmation.
- Not examined: HTTP parsing edge cases, deployment, TLS (app serves plain HTTP on loopback).

## 7. Limitations

This report is a point-in-time, best-effort review of the stated scope. It is not a guarantee that the software is free of vulnerabilities, and it does not replace a professional penetration test or independent audit.
