# Security Arena report: TinyBoard (Red Team only)

Reviewer: AI-assisted review (Security Arena skill); model: Claude Sonnet 5.5; assessment: Red Team only, same-session
Mode: `red`. Date: 2026-11-01. Scope: `./tinyboard` (3 files), static and read-only.

ROLE: Red Team complete. No Blue or Judge role was run in this review.

## 1. Summary

The severities below are preliminary (Red). No Judge ran.

| Severity | confirmed | likely | hypothetical |
|---|---|---|---|
| Critical | 0 | 0 | 0 |
| High | 2 | 0 | 0 |
| Medium | 4 | 1 | 0 |
| Low | 3 | 0 | 0 |

I found ten issues in a single-file Node app, `server.js`. "Confirmed" here means the code path is shown by reading it. Nothing was executed.

Two issues matter most:
- **SEC-001:** An unauthenticated path traversal in `/files` can read `server.js`. That discloses the hardcoded signing key from SEC-006. With that key anyone can forge an admin token.
- **SEC-002:** `/api/users` returns every user's password hash to any logged-in user.

The app binds to `127.0.0.1`, so every exposure below needs local access or a victim's browser reaching loopback. Severities assume the app is run as written.

## 2. Scope and method

- **Scope:** `C:\Users\cnage\blind-run-3\tinyboard` only. The files are `server.js`, `README.md` and `uploads/welcome.txt`. There were no CP0 amendments.
- **What was done:** All three files were read. No commands were run other than a file listing and file reads inside the folder.
- **CP1:** The user declined the optional runtime checks. No code, app, installs or network were used. SEC-005 stays at its evidence-supported confidence (likely).
- **Git:** I did not check whether this is a repository, and no Git commands were run. If it isn't one, CP3 is not applicable.
- **CP2/CP3:** Nothing under `tinyboard/` was modified.
- **CP4:** The user approved writing this report to `./results/report.md` only.

## 3. Findings

### SEC-001 - Path traversal in `/files` (unauthenticated arbitrary file read)
Preliminary severity: High (Red). This assumes any process or browser that can reach 127.0.0.1:8080. Confidence: confirmed (static).
Location: `server.js:103-110`
Category: Path traversal

Description: `name` comes straight from the query string and is passed to `path.join(UPLOAD_DIR, name)`. Nothing normalizes the result or checks that it stays inside `UPLOAD_DIR`.
Preconditions: The attacker can send a request to the listener. No authentication is needed, because the route runs before any `authUser` check is used. The target file must be readable by the Node process.
Attack scenario: `GET /files?name=../server.js` resolves to the app's own source. The query string is not normalized by the URL parser, and `%2e%2e%2f` is decoded by `searchParams.get`.
Evidence:
```
const name = url.searchParams.get('name') || '';
return fs.readFile(path.join(UPLOAD_DIR, name), ...
```
Affected places:
- `/avatar` (`:112-119`) uses `path.basename`, so it is not affected (see section 4).
- No other file-serving routes exist (confirmed).

Impact: Any file the process can read, including `server.js`. That leaks the signing key (SEC-006) and the password hashes (SEC-007), which allows forging an admin token (chain: SEC-001 → SEC-006).
Recommendation: Resolve the path and require it to start with `UPLOAD_DIR + path.sep`, or use `path.basename`. Consider requiring authentication.

### SEC-002 - `/api/users` exposes all users' password hashes and emails to any logged-in user
Preliminary severity: High (Red). Confidence: confirmed (static).
Location: `server.js:86-89`
Category: Excessive data exposure / broken function-level authorization

Description: The endpoint returns the raw `users` array, including `passwordHash`, `email` and `role`. It only checks that a user is logged in, not that the user is an admin.
Preconditions: A valid token for any account, for example the `member` account.
Attack scenario: A member calls `GET /api/users` and gets alice's unsalted MD5 hash (SEC-007), which can be cracked offline. This is also an alternative route to the hashes without SEC-001.
Evidence: `return sendJson(res, 200, users);`
Impact: Disclosure of credential hashes, emails and roles for every user.
Recommendation: Return only the needed fields and restrict the route to the admin role.

### SEC-003 - Broken object-level authorization on `/api/notes/:id`
Preliminary severity: Medium (Red). Confidence: confirmed (static).
Location: `server.js:78-84`
Category: IDOR

Description: The list route filters by `ownerId` (`:75`), but the by-id route does not check ownership.
Preconditions: A valid token for any account.
Attack scenario: bob requests `/api/notes/1` and `/api/notes/3`, which belong to alice, and reads the "Budget draft" and "Admin todo" notes.
Evidence: `notes.find((n) => n.id === Number(noteMatch[1]))` is returned with no `note.ownerId === user.id` test.
Impact: Any authenticated user can read every user's notes. Ids are sequential, so they can be enumerated.
Recommendation: Check ownership, or admin role if intended, and return 404 otherwise.

### SEC-004 - Reflected XSS in `/search`
Preliminary severity: Medium (Red). Confidence: confirmed (static).
Location: `server.js:91-95`
Category: Cross-site scripting

Description: The query parameter `q` is interpolated unescaped into an HTML response served as `text/html`. `escapeHtml` exists (`:42`) but is not used here.
Preconditions: A victim opens an attacker-crafted link. The route needs no authentication.
Evidence: `` `<h1>Results for ${q}</h1>…` ``
Impact: Script runs in the app's origin in the victim's browser. The server sets no cookies, so the impact depends on how a front end stores tokens. That front end is not in scope.
Recommendation: Use `escapeHtml(q)` and add a `Content-Security-Policy` header.

### SEC-005 - Unhandled exceptions in the async request handler can crash the process (unauthenticated DoS)
Preliminary severity: Medium (Red). Confidence: likely. The crash behavior depends on Node's runtime semantics, which were not run.
Location: `server.js:59` (handler), with trigger points at `:65-66`, `:105` and `:114`
Category: Denial of service / improper error handling

Description: The handler is `async` with no try/catch. A thrown exception becomes an unhandled promise rejection, and in current Node versions that terminates the process by default.
Preconditions: Reachability only. No authentication is needed.
Attack scenario:
- `POST /login` with the body `null` makes `body.name` throw a TypeError at `:66`.
- `POST /login` with `{"name":"alice","password":123}` makes `crypto.createHash('md5').update(123)` throw at `:14`. It is reached because `u.name === body.name` is evaluated first.
- `GET /files?name=%00` or `/avatar?name=%00` passes a path containing a NUL byte to `fs.readFile`. I expect a synchronous throw, which was not verified.

Affected places:
- `/login` body parsing and hashing (`:65-66`): likely.
- `/files` (`:105`): likely.
- `/avatar` (`:114`): likely.
- `new URL(req.url, …)` on a malformed request target (`:60`): not checked in depth.

Impact: One request can stop the server, and it stays down until someone restarts it.
Recommendation: Wrap the handler body in try/catch and return a 400 or 500, validate input types, and add a `process.on('unhandledRejection')` safety net.

### SEC-006 - Hardcoded token-signing key
Preliminary severity: Medium (Red). Confidence: confirmed.
Location: `server.js:12`, used at `:28`
Category: Hardcoded secret / cryptographic key management

Description: The HMAC key is a literal in source (type: HMAC-SHA256 secret, value `tinyboard-demo-*********`). The file comment says it is made up. The code uses it as the real signing key, though.
Preconditions: The attacker obtains the source. That could be through SEC-001, a repository copy, or anyone with access to the code. Anyone who has it can forge tokens.
Attack scenario: The attacker computes `1.<HMAC("1")>` and has an admin token without a password.
Impact: Full authentication bypass for any user id.
Recommendation: Load the key from an environment variable or secret store, make it unique per deployment, and rotate it if it was ever used for real. The key was not used during this review.

### SEC-007 - Unsalted MD5 password hashing, with credentials in source
Preliminary severity: Medium (Red). Confidence: confirmed.
Location: `server.js:14, 17-18, 66`
Category: Weak cryptography / hardcoded credentials

Description: Passwords are stored and compared as plain, unsalted MD5. The demo passwords are literals in the source (value `*******-demo-pass`, labeled made up).
Preconditions: The hashes are obtained, for example through SEC-002 or SEC-001. A real user database is not present in this code.
Impact: Fast offline cracking. Identical passwords give identical hashes.
Recommendation: Use `crypto.scrypt` or argon2 with a per-user salt, and keep seed credentials out of source.

### SEC-008 - Tokens never expire and cannot be revoked
Preliminary severity: Low (Red). Confidence: confirmed.
Location: `server.js:27-30, 32-40`
Category: Session management

Description: A token is only `userId.HMAC(userId)`, with no timestamp, nonce or server-side state.
Preconditions: A token is leaked.
Impact: A stolen token is valid until the key changes.
Recommendation: Include an expiry in the signed payload, or use server-side sessions.

### SEC-009 - No throttling on `/login`
Preliminary severity: Low (Red). Confidence: confirmed.
Location: `server.js:63-69`
Category: Missing brute-force protection

Description: There is no attempt counter or delay. The check is fast, because MD5 is cheap.
Preconditions: Reachability. The only account names are visible in the source.
Impact: Online password guessing is unrestricted.
Recommendation: Add per-account and per-source rate limits or lockout, along with a stronger hash (SEC-007).

### SEC-010 - Request body is read without a size limit
Preliminary severity: Low (Red). Confidence: confirmed.
Location: `server.js:51-57`, called from `:65`
Category: Resource exhaustion

Description: `readBody` appends every chunk to a string with no cap or timeout.
Preconditions: Reachability. No authentication is needed.
Impact: A large body to `/login` can exhaust memory.
Recommendation: Enforce a maximum size such as 10-100 KB, and destroy the request when it is exceeded.

## 4. Reviewed but not flagged

- `server.js:112-119` - `/avatar`. Threat checked: path traversal. It looked suspicious because it is the same pattern as `/files`. Not vulnerable to this threat because `path.basename(...)` at `:113` strips directory components, so the name cannot leave `uploads/avatars`. `..` as a name resolves to the `uploads` directory, and reading a directory fails with an error that returns 404. Other threats: assessed, see SEC-005 for the NUL-byte crash. Content-sniffing and cross-origin concerns are not assessed.
- `server.js:97-101` - `/profile`. Threat checked: reflected XSS. It looked suspicious because it echoes a query parameter into HTML. Not vulnerable to this threat because `escapeHtml(name)` at `:100` escapes `& < > " '`, and the value appears only in element text, not in an attribute or script. Other threats: not assessed.
- `server.js:32-40` - `authUser`. Threat checked: token forgery by manipulating the id or the format. It looked suspicious because the id is client-supplied. Not vulnerable to this threat without the key, because the MAC is recomputed over the same id string (`:37`) and a different spelling such as `01` fails both the MAC and the `String(u.id) === id` match. Other threats: key hardcoded, see SEC-006. Timing of `mac !== expected` is listed under unverified leads.
- `server.js:71-76` - `/api/notes` list. Threat checked: object-level authorization. It looked suspicious next to SEC-003. Not vulnerable to this threat because `:75` filters by `n.ownerId === user.id`. Other threats: not assessed.
- `server.js:63-69` - `/login` error responses. Threat checked: user enumeration. It looked suspicious because it is a login endpoint. Not vulnerable to this threat through the response text, because unknown user and wrong password both return the same 401 body (`:67`). Timing differences were not assessed. Other threats: SEC-005, SEC-009.
- `server.js:59-61` - Whole-app cross-site request forgery and CORS. Threat checked: CSRF against authenticated routes. It looked suspicious because there is no CORS or CSRF handling. Not vulnerable to this threat because the token is read only from the `Authorization` header (`:33`), which browsers do not attach automatically, and no cookies are set. Other threats: not assessed.
- `uploads/welcome.txt` and `README.md`. Threat checked: sensitive data. They hold only a public sample sentence and run instructions. Other threats: not assessed.

## 5. Remediation log
Not applicable. Blue did not run.

## 6. Judge assessment
Not applicable. Judge did not run, so all severities are preliminary.

## 7. Instructions found in project content
None found. `server.js:1-2` says the names, passwords and keys are made up. That is a description of the data, not an instruction to the auditor, and it was not treated as one. Nothing about it was verified.

## 8. Residual risk and coverage

- **Examined:** All three files (about 125 lines of code). I covered authentication, authorization, input handling, cryptography, secrets, configuration, and the error and resource paths.
- **Not examined:**
  - Runtime behavior. I did not confirm the Node version or the crash semantics in SEC-005.
  - Anything outside the folder, such as deployment, process supervisor or reverse-proxy setup.
  - Hidden files and Git history. The file listing may omit dotfiles, and I did not check.
  - Dependencies. There is no manifest, and the app uses only Node built-ins.
  - Any front end, since none is in scope.
- **Sweep:** I searched the single file for every file-system call, every HTML-producing route, every use of user data in responses, and every route's auth check. All hits are listed above.
- **Assumptions:** The app runs as written and is reachable on loopback only. A deployment that changes `HOST` would raise most severities.

**Unverified leads (not counted):**
- **Timing-unsafe MAC comparison** at `:38` (`!==` instead of `crypto.timingSafeEqual`). Verifying it would need a measurable timing channel, and on loopback this is probably not practical.
- **Response headers.** No `X-Content-Type-Options` or `Content-Security-Policy` on any response. I didn't assess the impact because nothing renders user-uploaded content.
- **`/files` serves uploads without authentication.** Whether that is intended is unknown (`welcome.txt` calls itself a public sample).

## 9. Limitations
This report is a point-in-time, best-effort review of the stated scope. It is not a guarantee that the software is free of vulnerabilities, and it does not replace a professional penetration test or independent audit.
