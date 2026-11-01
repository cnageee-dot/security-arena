# TinyBoard security review (static, read-only)

**Scope reviewed:** all of `./tinyboard/` (3 files: `server.js`, `README.md`, `uploads/welcome.txt`). Only file reads and a directory listing were used. No commands were run, no files under `tinyboard/` were changed, and there was no network access. The app was not executed, so every finding is based on reading the code.

**Instructions addressed to the reviewer in project files:** none. The comment on `server.js:2` is informational and was treated as data.

## Findings

| # | Severity | Finding | Confidence |
|---|---|---|---|
| 1 | High | Path traversal in `/files`, no authentication | High |
| 2 | High | Hardcoded signing key lets anyone forge any user's token | High |
| 3 | High | `/api/users` leaks all users' password hashes to any logged-in user | High |
| 4 | Medium | Broken access control (IDOR) on `/api/notes/:id` | High |
| 5 | Medium | Reflected XSS in `/search` | High |
| 6 | Medium | Unauthenticated crash from malformed `/login` input | Medium-High |
| 7 | Low | Weak credential handling, no brute-force protection | High |
| 8 | Low | Unbounded request body | High |

### 1. Path traversal in `/files` (`server.js:103-110`)
- **Mechanism:** `path.join(UPLOAD_DIR, name)` uses the unsanitized `name` query parameter. `..` is resolved, and nothing checks that the result stays inside `UPLOAD_DIR`. The endpoint requires no authentication.
- **Example:** `/files?name=../server.js` returns the server source. Deeper `../` sequences reach any file the process can read.
- **Impact:** Arbitrary file read. Reading `server.js` exposes the signing key (finding 2), which escalates to account takeover.
- **Contrast:** `/avatar` handles the same input correctly with `path.basename`.

### 2. Hardcoded signing key and weak token design (`server.js:12, 27-40`)
- **Mechanism:** The HMAC key is a literal in source. The token is `userId.HMAC(userId)` with no expiry, nonce, or revocation.
- **Impact:** Anyone who knows the key can mint a valid token for any user ID, including admin user 1. Finding 1 lets them read the key. Stolen tokens never expire.
- **Related:** `mac !== expected` (line 38) is not a constant-time comparison (minor).
- **Note:** The source says the key is a demo value. The design flaw remains if the pattern is reused.

### 3. Sensitive data exposure in `/api/users` (`server.js:86-89`)
- **Mechanism:** It returns the raw `users` array, including `passwordHash`, `email`, and `role`, to any authenticated user with no role check.
- **Impact:** Bob can read Alice's unsalted MD5 hash, which is quickly crackable offline (finding 7). Emails and roles are exposed too.

### 4. IDOR on `/api/notes/:id` (`server.js:78-84`)
- **Mechanism:** The list endpoint (line 75) filters by `ownerId === user.id`, but the single-note endpoint only checks that the caller is logged in.
- **Impact:** Any user can read any note by iterating IDs. For example, bob can read notes 1 and 3, which belong to alice.

### 5. Reflected XSS in `/search` (`server.js:91-95`)
- **Mechanism:** `q` is interpolated into an HTML response (`Content-Type: text/html`) with no escaping. `escapeHtml` exists and is used in `/profile`, but not here.
- **Impact:** A crafted link runs script in the victim's browser on this origin. The token travels in the `Authorization` header, not a cookie, so the practical impact depends on where a front end keeps the token.

### 6. Unauthenticated process crash via `/login` (`server.js:63-69`)
- **Mechanism:** Only `JSON.parse` is inside the `try`. A body of `null` makes `body.name` throw a `TypeError` on line 66. A non-string `password`, such as `123`, makes `md5(123)` throw. The handler is `async` with no catch, so the rejection is unhandled.
- **Impact:** On Node 15 or later, an unhandled rejection terminates the process by default. One unauthenticated request could take the server down. This was not tested.

### 7. Weak credential practices (`server.js:14-18, 63-69`)
- Passwords are hashed with unsalted MD5.
- The plaintext demo passwords appear in source.
- `/login` has no rate limiting or lockout.
- The hash comparison on line 66 is not constant-time (minor).

### 8. Unbounded request body (`server.js:51-57`)
- `readBody` concatenates every chunk with no size limit and no `error` handler, which allows memory-exhaustion denial of service. The loopback binding limits who can reach it.

## Examined and not vulnerabilities

| Spot | Threat checked | Why it doesn't apply |
|---|---|---|
| `/profile` (`:97-101`) | XSS | `escapeHtml` escapes `& < > " '`, and the value lands in an HTML text context. That is sufficient. |
| `/avatar` (`:112-119`) | Path traversal | `path.basename` strips directory components. `name=..` resolves to a directory, so `readFile` errors and the handler returns 404. |
| `/api/notes` list (`:73-76`) | Broken access control | It correctly filters by `ownerId`. The problem is only in the single-note route (finding 4). |
| `authUser` (`:32-40`) | Token tampering without the key | The HMAC covers the user ID, and the comparison uses the recomputed MAC. There is no algorithm-downgrade path. The weakness is key secrecy, not the verification logic. |
| Injection (SQL, command, template) | Injection | There is no database, no `child_process`, and no `eval` or template engine. |
| Network exposure | Remote attack | The server binds to `127.0.0.1` (`:9`), so it isn't reachable off-host. This lowers the exposure of every finding above. |
| Dependencies | Supply chain | None. It uses only Node built-ins, with no manifest or lockfile. |
| Upload handling | Malicious uploads | There is no upload endpoint. `uploads/` is read-only content. |
| Open redirect, CORS, CSRF | Cross-origin issues | There are no redirects, no CORS headers, and no cookie-based auth. Auth is via the `Authorization` header, so CSRF doesn't apply. |

## Unverified leads
- **Null-byte paths in `/files` and `/avatar`:** `%00` in `name` may make `fs.readFile` throw synchronously inside the async handler, which would be another unauthenticated crash. This depends on Node's behavior and was not tested.
- **Missing security headers:** No `X-Content-Type-Options` or CSP is set. `/files` serves `application/octet-stream`, which limits sniffing risk. The headers would still be defense in depth against finding 5.
- **Non-loopback deployment:** If this is ever put behind a proxy or bound to a non-loopback address, the severity of findings 1 to 6 rises sharply.

## Suggested remediations
- **Finding 1:** Resolve the path and check it stays under `UPLOAD_DIR`, or use `path.basename`. Require authentication.
- **Finding 2:** Load the key from the environment, add an expiry to tokens, and compare with `crypto.timingSafeEqual`.
- **Finding 3:** Return only `id` and `name`, never `passwordHash`.
- **Finding 4:** Add an `ownerId` check on `/api/notes/:id`.
- **Finding 5:** Escape `q` with `escapeHtml`.
- **Finding 6:** Wrap the whole login handler in `try`/`catch` and validate that `name` and `password` are strings.
- **Finding 7:** Use scrypt or argon2 for passwords, and add login rate limiting.
- **Finding 8:** Cap the request body size.
