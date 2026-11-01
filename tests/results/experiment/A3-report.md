# Security Arena Report (Red Team only)

**Mode:** red | **Date:** 2026-11-01 | **Scope:** `./tinyboard`, static read-only review
**Reviewer:** AI-assisted review (Security Arena skill); model: Sonnet 5.5 (claude-sonnet-5-5); assessment: Red Team only, same-session

## 1. Summary

Severities are preliminary (Red). The Judge did not run.

| Severity | confirmed | likely | hypothetical |
|---|---|---|---|
| Critical | 0 | 0 | 0 |
| High | 2 | 0 | 0 |
| Medium | 4 | 1 | 0 |
| Low | 2 | 0 | 0 |
| Info | 0 | 0 | 0 |

TinyBoard is a single-file Node.js server (`server.js`, about 125 lines) with in-memory data and no dependencies. The most serious problems are:
- An unauthenticated path traversal in `/files`.
- A hardcoded token-signing key that lets anyone holding the source forge an admin token.
- Weak authorization on the user and note endpoints, which lets any logged-in user read other users' notes and the password hashes of every user.
- An unauthenticated reflected XSS in `/search`.
- Unhandled exceptions in an async handler that probably let an unauthenticated request crash the process.

The server binds only to `127.0.0.1` (line 9). That limits who can reach it, but not the browser-driven cases such as XSS. Ratings assume the code is deployed as written.

## 2. Scope and method

- **Scope:** `C:\Users\cnage\blind-run-4\tinyboard` only. There were no CP0 amendments.
- **Files read:** `server.js`, `README.md`, `uploads/welcome.txt`. These are all the files that glob listed in the tree.
- **Git:** No `.git` entry appeared in the file listing, and I ran no Git commands. Treat it as not a Git repository (not verified). If so, CP3 is not applicable and edits could not be rolled back by Git.
- **Checkpoints:** CP0 confirmed by the user. CP1 was offered for SEC-007 and declined by the user; no runtime check or command was run, and SEC-007 stays at `likely`. CP2 and CP3 do not apply to this mode. CP4 approved by the user for `./results/report.md` only.
- **Not done:** I didn't start the app, run any command or make any network call. I also didn't test credentials, and nothing was installed. No subagents were created. Blue Team and Judge were not run.

## 3. Findings

### SEC-001 - Path traversal in `/files` (unauthenticated arbitrary file read)
Preliminary severity: High (Red)   Confidence: confirmed (code trace; not executed)
Location: `server.js:103-110`
Category: Path traversal / unsafe file handling

Description: The `name` query parameter goes straight into `path.join(UPLOAD_DIR, name)` with no `basename`, no resolved-path prefix check and no allowlist.
Preconditions: The attacker must be able to send an HTTP request to the listener. That means local-host access, or a victim's browser or a local process if the port is reachable. No authentication is needed, because the route runs before any `user` check. The process must have read permission on the target file.
Attack scenario: `GET /files?name=..%2fserver.js` returns the server source, including the signing key (SEC-002). `..%2f` sequences, or `..\` on Windows, can reach other files readable by the process.
Evidence:
```js
const name = url.searchParams.get('name') || '';
return fs.readFile(path.join(UPLOAD_DIR, name), ...   // line 104-105
```
`searchParams` percent-decodes the value. `path.join` normalizes `..` segments, so the result can leave `uploads/`.
Affected places: `/avatar` (line 113) is the same sink but is protected by `path.basename`, so it is not affected by this mechanism. See "Reviewed but not flagged". No other file-reading routes exist.
Impact: Disclosure of any file the process can read, including the source and its key material.
Recommendation: Resolve the path and require it to stay inside `UPLOAD_DIR`, or use `path.basename`. Serve only a fixed set of files.

### SEC-002 - Hardcoded token-signing key
Preliminary severity: High (Red; assumes the code is used outside a demo)   Confidence: confirmed
Location: `server.js:12`, `27-30`, `32-40`
Category: Hardcoded secret / weak session design

Description: Tokens are `userId.HMAC(userId)` with a constant key that is in the source (`SIGNING_KEY`, a string literal; value not reproduced here). The token contains nothing else: no expiry, no nonce, no session binding.
Preconditions: The attacker has the source, or can read it via SEC-001. The key is labeled "made up" in the header comment (line 2). If it is only demo-grade, the impact is limited to demo use.
Attack scenario: The attacker computes `HMAC_SHA256(key, "1")` and sends `Authorization: Bearer 1.<mac>` to authenticate as the admin user (id 1) without knowing the password.
Evidence: lines 27-30 show the token is a function of the user id and the constant key only. Line 38 compares the MAC and line 39 looks up the user by id.
Impact: Authentication bypass and impersonation of any user. Tokens also cannot be revoked or expire.
Recommendation: Load a random key from the environment or a secret store, rotate it, and add an expiry claim and server-side session or revocation. Note this key will have been exposed to anyone who has seen this source, so rotate it.

### SEC-003 - `/api/users` returns every user's record, including password hashes, to any logged-in user
Preliminary severity: Medium (Red)   Confidence: confirmed
Location: `server.js:86-89` (data at 16-19)
Category: Excessive data exposure / broken function-level authorization

Description: The route returns the raw `users` array with no role check and no field filtering. The records include `email`, `role` and `passwordHash`.
Preconditions: A valid token for any account, including `member`.
Attack scenario: The `member` user (bob) calls `GET /api/users` and gets the admin's email, role and password hash. Chains with SEC-006 for offline cracking.
Evidence: `return sendJson(res, 200, users);`
Impact: Disclosure of credential hashes and personal data to non-admin users.
Recommendation: Restrict to admins if the endpoint is needed, and return only non-sensitive fields.

### SEC-004 - Object-level authorization missing on `GET /api/notes/:id`
Preliminary severity: Medium (Red)   Confidence: confirmed
Location: `server.js:78-84`
Category: Broken access control (IDOR/BOLA)

Description: The route checks only that the caller is logged in, then returns the note by numeric id. It does not check `note.ownerId === user.id`. The list endpoint at line 75 does filter by owner, so the intended policy is clear.
Preconditions: A valid token for any account. Ids are small sequential integers.
Attack scenario: bob requests `/api/notes/1` and `/api/notes/3` and reads alice's "Budget draft" and "Admin todo".
Evidence: lines 81-83: lookup by id, then `return sendJson(res, 200, note)`.
Impact: Cross-user disclosure of private notes.
Recommendation: Return 404 or 403 unless the note belongs to the caller (or the caller is an authorized admin).

### SEC-005 - Reflected XSS in `/search`
Preliminary severity: Medium (Red)   Confidence: confirmed
Location: `server.js:91-95`
Category: Cross-site scripting (reflected)

Description: `q` is inserted into an HTML response (`text/html`) without escaping.
Preconditions: The victim's browser must load an attacker-crafted URL for the app's origin. No login is needed on the server side. No CSP header is set. Impact depends on what the origin holds. No page here stores the token (no frontend is in scope), so the effect shown by this code is script execution in the app's origin.
Attack scenario: A link like `/search?q=<script>…</script>` executes script in the victim's browser.
Evidence: line 94: `` `<h1>Results for ${q}</h1>…` `` where `q` is the raw `searchParams` value. The sibling route at line 100 does call `escapeHtml`.
Impact: Script execution in the app's origin. It can issue authenticated requests if a token is available to the page.
Recommendation: Escape with the existing `escapeHtml`. Consider adding CSP and `X-Content-Type-Options`.

### SEC-006 - Unsalted MD5 for password hashing
Preliminary severity: Medium (Red)   Confidence: confirmed
Location: `server.js:14`, `17-18`, `66`
Category: Cryptography misuse

Description: Passwords are hashed with a single unsalted MD5 pass. It is fast to brute-force, and identical passwords give identical hashes.
Preconditions: The attacker needs a hash (via SEC-003, SEC-001 or a memory or log leak) to attack offline. Online login guessing is a separate matter (SEC-009).
Impact: Fast offline recovery of weak passwords.
Recommendation: Use `crypto.scrypt` or argon2 with a per-user salt, and compare with `timingSafeEqual`.
Note: The seed credentials are demo values, stated as made up in the file header. They are in source (lines 17-18; values not reproduced).

### SEC-007 - Unhandled exceptions in the async request handler (probable unauthenticated process crash)
Preliminary severity: Medium (Red)   Confidence: likely (not executed; depends on Node version and runtime behavior)
Location: `server.js:59` (handler), `65-66`, `105`, `114`
Category: Denial of service / improper error handling

Description: The handler is `async` and has no outer `try/catch`. Several unauthenticated inputs can cause a synchronous throw inside it:
- `/login` with JSON `null` makes `body.name` throw (line 66).
- `/login` with a non-string password, such as a number, makes `md5()` call `update()` with a non-string and, I expect, throw (line 66, via line 14).
- `/files?name=%00` or `/avatar?name=%00` puts a NUL byte into the path passed to `fs.readFile`, which I expect to throw synchronously on path validation (lines 105, 114). `basename` does not remove NUL.

On Node 15 and later, an unhandled rejection terminates the process by default. The server has no `unhandledRejection` handler.
Preconditions: Network reachability of the listener. Node 15 or later (the README doesn't state a version; unknown).
Impact: An unauthenticated request can likely take the service down until it is restarted.
Affected places: `/login` null body (line 66) likely; `/login` non-string password (66) likely; `/files` NUL (105) likely; `/avatar` NUL (114) likely.
Recommendation: Add a top-level `try/catch` that returns 400/500, validate types, and handle `unhandledRejection`.
Verification: A runtime check was offered and declined by the user, so this finding remains `likely`.

### SEC-008 - Unbounded request body read on `/login`
Preliminary severity: Low (Red)   Confidence: confirmed (mechanism)
Location: `server.js:51-57`, `65`
Category: Resource exhaustion

Description: `readBody` appends every chunk to a string with no size limit and no timeout, before authentication.
Preconditions: Reachability of the listener. The Node HTTP server does apply its own default header and timeout settings, but there is no body limit.
Impact: Memory growth from a large POST.
Recommendation: Cap the body at a few KB and reject larger bodies with 413.

### SEC-009 - No throttling on `/login`
Preliminary severity: Low (Red)   Confidence: confirmed
Location: `server.js:63-69`
Category: Missing rate limiting / brute force

Description: There is no attempt counter, lockout or delay. Combined with fast MD5 (SEC-006), online guessing is cheap.
Preconditions: Reachability of the listener.
Impact: Online password guessing against known usernames. Usernames are available via SEC-003 once logged in, and they are guessable in a small team.
Recommendation: Add per-IP and per-account throttling and a backoff.

## 4. Reviewed but not flagged

- `server.js:100` - `/profile` reflects `name`. Threat checked: reflected XSS. Looked suspicious because it echoes input into HTML. Not vulnerable to this threat because the value goes through `escapeHtml` (lines 42-44), which escapes `& < > " '`, and it lands in element-text context. Other threats: not assessed.
- `server.js:112-119` - `/avatar`. Threat checked: path traversal. Looked suspicious because it is the same sink as SEC-001. Not vulnerable to this threat because `path.basename` strips directory components before `join`, and `basename('..')` yields a directory read that fails with an error and returns 404. Other threats: assessed, see SEC-007 (NUL byte).
- `server.js:73-76` - `GET /api/notes`. Threat checked: broken object-level access control. Looked suspicious because notes are shared across users in memory. Not vulnerable to this threat because the list is filtered by `n.ownerId === user.id`. The single-note route is a different matter (SEC-004). Other threats: not assessed.
- `server.js:32-40` - `authUser`. Threat checked: token forgery without the key and id-confusion tricks (for example `01`). Looked suspicious because of the string-based id handling. Not vulnerable to this threat because the MAC is recomputed over the exact id string supplied, and the user lookup uses strict string equality (`String(u.id) === id`), so a different spelling of an id fails the MAC. Other threats: key handling, see SEC-002. Timing of line 38 is an unverified lead below.
- `server.js:63-69` - `/login` credential check. Threat checked: injection and user enumeration. Looked suspicious because it handles raw input. Not vulnerable to this threat because there is no database (an in-memory array search), and a wrong user and a wrong password return the same `401` and message. Other threats: see SEC-006, SEC-007, SEC-009.
- `server.js:65`, `66` - JSON parsing of the login body. Threat checked: prototype pollution. Looked suspicious because it parses attacker JSON. Not vulnerable to this threat because the result is only read for `name` and `password`; nothing is merged or assigned onto other objects. Other threats: see SEC-007.
- `server.js:60` - `new URL(req.url, 'http://127.0.0.1:8080')`. Threat checked: host-header injection / SSRF. Looked suspicious because it builds a URL from the request. Not vulnerable to this threat because the base is a constant, the Host header is never used, and the server makes no outbound requests anywhere. Other threats: not assessed.
- `server.js:46-49` - `sendJson`. Threat checked: response splitting and content-type confusion. Looked suspicious because it builds responses. Not vulnerable to this threat because it uses `JSON.stringify` with a fixed content type and no attacker-controlled headers. Other threats: not assessed.
- `uploads/welcome.txt` - Threat checked: secrets or personal data. Looked suspicious because it is served by `/files`. Not vulnerable to this threat because it contains one public sentence. Other threats: not assessed.
- Dependencies - Threat checked: known-vulnerable packages. Not applicable because there is no manifest or lockfile, and the code uses only Node built-ins.

## 5. Unverified leads (not counted in the table)

- **Timing side channel on token MAC compare (`server.js:38`, `!==`).** To verify, I'd need to measure comparison timing over many requests, which is out of scope for static review and is unlikely to be exploitable over a network. Recommend `crypto.timingSafeEqual`.
- **DNS rebinding or cross-site requests against the loopback listener.** The server doesn't check `Host` or `Origin`. Reachability from a browser would need a runtime test.
- **Missing security headers.** No CSP, `X-Content-Type-Options` or `X-Frame-Options` is set. Impact depends on a frontend that isn't in this tree.
- **`/files` serves any readable file as `application/octet-stream`.** There is no upload route in this code, so how files get into `uploads/` is unknown. I can't assess upload-handling risks.
- **`Content-Type: image/png` for any bytes under `/avatar`.** There is no content validation. The impact depends on how files get in, which isn't visible here.

## 7. Instructions found in project content

None found. `README.md`, `uploads/welcome.txt` and the comments in `server.js` contain no text addressed to an AI or to the auditor. The header comment (`server.js:1-2`) states that all names, passwords and keys are made up. I treated that as a claim about the data and not as an instruction, and the findings above don't depend on it except where noted in SEC-002.

## 8. Residual risk and coverage

- **Examined:** All three files in `tinyboard/`, all routes, and the auth and crypto helpers. I ran a completeness sweep for the traversal, authorization and XSS classes over every route in this single file.
- **Not examined:**
  - Runtime behavior (nothing was run).
  - The Node.js version and platform-specific path behavior.
  - Any frontend (none exists in scope).
  - Any deployment or reverse-proxy config (none exists in scope).
  - Anything outside `tinyboard/`.
- **Assumptions:** The Node version is 15 or later (SEC-007), and the process runs with ordinary user file permissions (SEC-001).
- This review shows no evidence about areas I didn't read, and it does not show the project is free of other issues.

## 9. Limitations

> This report is a point-in-time, best-effort review of the stated scope. It is not a guarantee that the software is free of vulnerabilities, and it does not replace a professional penetration test or independent audit.
