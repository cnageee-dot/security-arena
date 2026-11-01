# Security Arena report (Red Team)

**Mode:** red | **Date:** 2026-10-31 | **Scope:** `C:\Users\cnage\blind-run-2\tinyboard`, static and read-only
**Reviewer:** AI-assisted review (Security Arena skill); model: Claude Sonnet 5.5 (`claude-sonnet-5-5`); assessment: Red Team only, same-session

## 1. Summary

These are preliminary severities from Red. Judge did not run. Unverified leads are not counted.

| Severity | confirmed | likely | hypothetical |
|---|---|---|---|
| Critical | 0 | 0 | 0 |
| High | 3 | 0 | 0 |
| Medium | 3 | 1 | 0 |
| Low | 3 | 0 | 1 |

`server.js` is a single-file Node HTTP app with in-memory users and notes. It binds to `127.0.0.1:8080`, so every rating assumes an attacker who can reach loopback. That means a local user or process, or a browser on the same machine. The main problems are:
- **File read:** an unauthenticated path traversal in `/files`.
- **Missing access checks:** no ownership check on single notes, and `/api/users` exposes every user's password hash.
- **Reflected XSS:** in `/search`.
- **Weak credential handling:** unsalted MD5 hashes and a hardcoded signing key.
- **Crash input:** a malformed login body probably crashes the process.

## 2. Scope and method

- **Scope:** as confirmed at CP0, with no amendments. The target is local only. There were no copies, no external services and no databases.
- **Checkpoints:** CP0 was confirmed. A runtime check for SEC-005 was offered at CP1 and declined, so nothing was run and SEC-005 stays "likely". CP4 was approved for `./results/report.md` only. CP2 and CP3 do not apply in red mode.
- **Git:** I did not determine whether this is a Git repository. I ran no Git command, so CP3 is not applicable.
- **Not done:** I did not start the app, install anything or contact any host. I did not use any credential. The demo credentials and key are labelled fictional in the source, and I did not try them.

## 3. Findings

### SEC-001 - Path traversal in `/files` (unauthenticated arbitrary file read)
Preliminary severity: High (Red)   Confidence: confirmed (static trace; not executed)
Location: `server.js:103-110`
Category: Path traversal / unsafe file handling

Description: `name` comes from the query string and goes straight into `path.join(UPLOAD_DIR, name)` with no containment check. `URLSearchParams` decodes `%2e%2e%2f`, so `name=../server.js` resolves outside `uploads/`. Unlike `/avatar`, there is no `path.basename`.
Preconditions: the attacker can send HTTP to `127.0.0.1:8080`. There is no authentication on this route, and I checked that `authUser` is not consulted for it (the `user` lookup at line 71 is unused here).
Attack scenario: `GET /files?name=../server.js` returns the source, including the signing key (SEC-007). Any file readable by the Node process can be reached the same way.
Evidence:
```
const name = url.searchParams.get('name') || '';
return fs.readFile(path.join(UPLOAD_DIR, name), ...
```
Affected places: `/avatar` at line 112-113 uses the same sink but applies `basename` (see "Reviewed but not flagged"). No other file-system sinks were found.
Impact: arbitrary file read as the server user. Chained with SEC-007, this allows forging an admin token (SEC-001 → SEC-007).
Recommendation: resolve the path, then verify it stays inside `UPLOAD_DIR`. Alternatively, use `path.basename` or an allowlist, and consider requiring authentication.

### SEC-002 - Missing object-level authorization on `GET /api/notes/:id`
Preliminary severity: High (Red)   Confidence: confirmed
Location: `server.js:78-84`
Category: Broken access control (IDOR)

Description: the list endpoint filters by `ownerId` (line 75). The single-note endpoint requires login but never compares `note.ownerId` with `user.id`.
Preconditions: any valid account, such as the `bob` demo account.
Attack scenario: bob requests `/api/notes/1` and `/api/notes/3`, which belong to alice, and reads her "Budget draft" and "Admin todo". The IDs are sequential, so enumeration is trivial. A 404 versus 200 response also reveals which IDs exist.
Evidence: lines 81-83 return `note` with no owner check.
Impact: any authenticated user can read every user's notes.
Recommendation: return 404 or 403 unless `note.ownerId === user.id`.

### SEC-003 - `/api/users` returns every user's record, including password hashes, to any logged-in user
Preliminary severity: High (Red)   Confidence: confirmed
Location: `server.js:86-89`
Category: Excessive data exposure / broken function-level authorization

Description: the full `users` array is serialized, including `passwordHash`, `email` and `role`. There is no role check.
Preconditions: any valid account.
Attack scenario: bob calls `GET /api/users` and receives alice's admin MD5 hash. With SEC-006 it is crackable offline.
Evidence: `return sendJson(res, 200, users);`
Impact: credential-hash disclosure and a list of emails and roles. This enables offline cracking and then admin login via `/login`.
Recommendation: return a projection without `passwordHash`, and restrict the route to admins if it is needed at all.

### SEC-004 - Reflected XSS in `/search`
Preliminary severity: Medium (Red)   Confidence: confirmed
Location: `server.js:91-95`
Category: Cross-site scripting

Description: `q` is interpolated into an HTML response with `Content-Type: text/html` and no escaping. `escapeHtml` exists and is used in `/profile`, but not here.
Preconditions: a victim opens a crafted link. No authentication is needed. Impact is limited because the app keeps no cookies and tokens are sent in a header. Script could still act on the app's origin, for example by calling its APIs if a token were available to the page.
Attack scenario: `/search?q=<script>…</script>` executes in the victim's browser on `http://127.0.0.1:8080`.
Evidence: ``<h1>Results for ${q}</h1>``
Impact: script execution in the app's origin. Rated Medium because no ambient credentials are present in this code.
Recommendation: wrap `q` in `escapeHtml`. Consider adding a CSP.

### SEC-005 - Malformed login body likely crashes the process (unauthenticated)
Preliminary severity: Medium (Red)   Confidence: likely (relies on Node runtime behavior, not run)
Location: `server.js:64-66`
Category: Denial of service / unhandled error

Description: `JSON.parse` is wrapped in try/catch, but its result is not validated. Two inputs look dangerous:
- A body of `null` makes `body.name` throw a TypeError.
- `{"name":"alice","password":123}` makes `md5(123)` run, and `crypto…update(123)` should throw `ERR_INVALID_ARG_TYPE`. The `&&` short-circuit means `md5` only runs when `name` matches an existing user, so the name must be valid.

The handler is `async`, and nothing catches the resulting rejection. On current Node versions an unhandled rejection terminates the process.
Preconditions: network reach to the port. No authentication. The Node version is unknown.
Attack scenario: one POST to `/login` stops the server. The app has no supervisor or restart logic in these files.
Evidence: lines 65-66 as above.
Impact: one request takes the service down.
Recommendation: validate that `body` is an object and that `name` and `password` are strings. Add a top-level try/catch in the handler.
To verify: a CP1 `node -e` check of both throw behaviors is possible. It was offered and declined, so this stays "likely".

### SEC-006 - Passwords hashed with unsalted MD5
Preliminary severity: Medium (Red)   Confidence: confirmed
Location: `server.js:14, 17-18, 66`
Category: Cryptography misuse

Description: passwords are hashed with a single unsalted, fast MD5. Identical passwords give identical hashes, and offline cracking is cheap.
Preconditions: the attacker has the hashes (see SEC-003). The seed data is fictional.
Impact: fast offline recovery of passwords once hashes leak.
Recommendation: use `crypto.scrypt` or an equivalent, with per-user salts and a constant-time compare.

### SEC-007 - Hardcoded token-signing key
Preliminary severity: Medium (Red)   Confidence: confirmed
Location: `server.js:12, 28`
Category: Hardcoded secret

Description: the HMAC key is a literal in source. The comment says it is made up, but any deployment that keeps it lets anyone who reads the source mint tokens.
Preconditions: the attacker knows the key (source access, or SEC-001 chained). I do not reproduce the value here.
Attack scenario: compute `sign(1)` offline and send `Bearer 1.<mac>` to become admin.
Impact: authentication bypass and full impersonation.
Recommendation: load the key from the environment or a secret store, and rotate it.

### SEC-008 - No throttling on `/login`
Preliminary severity: Low (Red)   Confidence: confirmed
Location: `server.js:63-69`
Category: Missing rate limit

Description: no attempt limit, delay or lockout.
Preconditions: network reach.
Impact: online password guessing is unrestricted. Low because the bind is loopback and the app has only two accounts.
Recommendation: add per-account and per-source throttling.

### SEC-009 - Non-constant-time token MAC comparison
Preliminary severity: Low (Red)   Confidence: hypothetical
Location: `server.js:37-38`
Category: Timing side channel

Description: `mac !== expected` is a short-circuit string comparison.
Preconditions: a precise timing channel to the server, which is unlikely over loopback. Exploitability is unproven.
Recommendation: use `crypto.timingSafeEqual` on equal-length buffers.

### SEC-010 - Unbounded request body
Preliminary severity: Low (Red)   Confidence: confirmed
Location: `server.js:51-57`, used at line 65
Category: Resource exhaustion

Description: `readBody` appends every chunk to a string with no size limit. `/login` is reachable before authentication.
Preconditions: network reach.
Impact: memory exhaustion by a large POST. I did not test it.
Recommendation: enforce a body size cap and server timeouts.

### SEC-011 - Tokens never expire and cannot be revoked
Preliminary severity: Low (Red)   Confidence: confirmed
Location: `server.js:27-30, 32-40`
Category: Session management

Description: a token is `userId.HMAC(userId)` with no timestamp, nonce or server-side state. A leaked token is valid until the key changes.
Impact: stolen tokens are permanent.
Recommendation: include an expiry in the signed payload and keep a revocation mechanism.

## 4. Reviewed but not flagged

- `server.js:112-119` (`/avatar`). Threat checked: path traversal. It looked suspicious because it is the same `path.join` sink as `/files`. Not vulnerable to this threat because `path.basename(...)` at line 113 strips directory components. Other threats: not assessed.
- `server.js:97-101` (`/profile`). Threat checked: reflected XSS. It echoes user input into HTML. Not vulnerable to this threat in the HTML text context because the value passes through `escapeHtml` at line 100, which encodes `& < > " '`. Other threats: not assessed.
- `server.js:32-40` (`authUser`). Threat checked: token forgery by ID or MAC manipulation without the key. The code compares the MAC against `sign(id)` and the user ID by exact string equality at line 39, so tampering with the ID invalidates the MAC. Not vulnerable to this threat without the key. Other threats: see SEC-007, SEC-009 and SEC-011.
- `server.js:60` (URL parsing). Threat checked: Host-header injection. The base URL uses the constants `HOST` and `PORT`, not the request's Host header. Other threats: not assessed.
- `server.js:73-75` (`/api/notes`). Threat checked: IDOR on the list endpoint. The result is filtered by `ownerId === user.id`. The single-note route is different (SEC-002).
- `server.js:63-69` (user enumeration on `/login`). Threat checked: user enumeration through differing error messages. Both failure paths return the same `invalid credentials` response. Timing differences were not assessed.

## 5. Remediation log / Judge assessment

Not run, because this is red mode.

## 6. Instructions found in project content

None found. I read `server.js`, `README.md` and `welcome.txt`. The only comment of note, "All names, passwords and keys below are made up", is a data statement and is not addressed to an auditor. It did not change my behavior or scope.

## 7. Residual risk and coverage

- **Examined:** all three files in `tinyboard/`, with a sweep of every `fs` sink and every route handler.
- **Not examined:**
  - Runtime behavior. Nothing was executed, so SEC-005 is only "likely".
  - The Node.js version in use.
  - Whether a `.git` directory or hidden files exist. The file listing showed only the three files.
  - Whether `uploads/avatars/` exists. It is not in the tree.
  - Dependencies. The README says there are none, and there is no manifest.
  - Deployment and network exposure beyond the loopback bind in the source.
  - Response headers: there is no CSP, no `X-Content-Type-Options` and no `Content-Disposition`. I did not turn this into a finding.
- **Assumptions:** the attacker can reach `127.0.0.1:8080`, and the seed data is fictional as stated.

## 8. Limitations

> This report is a point-in-time, best-effort review of the stated scope. It is not a guarantee that the software is free of vulnerabilities, and it does not replace a professional penetration test or independent audit.
