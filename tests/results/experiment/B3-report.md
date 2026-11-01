# TinyBoard static security review

**Scope:** `tinyboard/server.js` (125 lines), `README.md`, `uploads/welcome.txt`. Read-only; nothing was run or modified. No `package.json`, so no dependencies.

## Findings

| # | Severity | Issue | Location |
|---|---|---|---|
| 1 | High | Path traversal in `/files` | `server.js:103-110` |
| 2 | High | Hardcoded token signing key, exposed via finding 1 | `server.js:12, 27-30` |
| 3 | High | `/api/users` leaks all users incl. password hashes to any logged-in user | `server.js:86-89` |
| 4 | High | IDOR on `/api/notes/:id` | `server.js:78-84` |
| 5 | Medium | Reflected XSS in `/search` | `server.js:91-95` |
| 6 | Medium | Unauthenticated crash (DoS) on malformed login body | `server.js:63-69` |
| 7 | Medium | Weak password storage and login hardening | `server.js:14-18, 66` |
| 8 | Low | Tokens never expire; MAC comparison not constant-time | `server.js:27-40` |

### 1. Path traversal in `/files` (High, confidence: high)
- **Mechanism:** `path.join(UPLOAD_DIR, name)` uses the raw `name` query parameter with no `basename` or prefix check (line 105). `/files?name=../server.js` resolves outside `uploads/`. No authentication required.
- **Impact:** Anyone reaching the port can read any file the process can read, including `server.js` (signing key, password-hash source).
- **Contrast:** `/avatar` handles this correctly (line 113).

### 2. Hardcoded signing key (High, confidence: high)
- **Mechanism:** `SIGNING_KEY` is a constant in source (line 12). Token = `id.HMAC(id)` (lines 27-30); anyone with the key can forge a token for any user id.
- **Impact:** With finding 1, an attacker reads the key and forges `Bearer 1.<mac>` to become admin (alice).

### 3. `/api/users` data exposure (High, confidence: high)
- **Mechanism:** Requires only a valid login and returns the whole `users` array (line 88), including `passwordHash`, `email`, `role`. No field filtering or admin check.
- **Impact:** Any member (bob) can retrieve the admin's hash. It is unsalted MD5 (finding 7), so quickly crackable offline.

### 4. IDOR on `/api/notes/:id` (High, confidence: high)
- **Mechanism:** The list endpoint filters by `ownerId` (line 75). The single-note endpoint authenticates but never checks `note.ownerId === user.id` (lines 81-83).
- **Impact:** Bob can read alice's private notes (`/api/notes/1`, `/api/notes/3`) by walking sequential ids.

### 5. Reflected XSS in `/search` (Medium, confidence: high)
- **Mechanism:** `q` is interpolated directly into HTML served as `text/html` (line 94) with no escaping. `/profile` uses `escapeHtml` for the same pattern (line 100).
- **Impact:** `/search?q=<script>…</script>` runs script in the app origin. Tokens are in the `Authorization` header, not cookies, so exposure depends on how a front end stores them (none present).

### 6. Unauthenticated crash on malformed login (Medium, confidence: medium-high)
- **Mechanism:** The handler is `async`. `JSON.parse("null")` succeeds and returns `null`, so `body.name` (line 66) throws TypeError. A non-string `password` (e.g. `123`) makes `md5()` throw too. Only the parse is in a try, so this is an unhandled promise rejection.
- **Impact:** On Node 15+ the default terminates the process, so one unauthenticated request can down the server. Not executed; Node version is an assumption.
- **Related:** `readBody` has no size limit (line 54), allowing memory exhaustion.

### 7. Weak credential handling (Medium, confidence: high)
- **Mechanism:** Unsalted MD5 (lines 14-18), demo passwords in source, no rate limiting or lockout on `/login`, non-constant-time hash comparison.
- **Impact:** Easy offline cracking (finding 3) and online guessing.

### 8. Token design (Low, confidence: high)
- **Mechanism:** No expiry or nonce, no revocation (lines 27-30). `mac !== expected` (line 38) is a plain string comparison.
- **Impact:** A leaked token is valid forever. Timing attack is theoretical.

## Unverified leads
- **Null byte in `/files?name=…%00`:** On some Node versions `fs.readFile` throws synchronously on invalid paths; inside the async handler that would be another crash path. Depends on Node version; not confirmed.
- **DNS rebinding / cross-site requests to localhost:** Binds to `127.0.0.1` but does not validate the `Host` header. Unauthenticated endpoints (`/files`, `/search`) could be reachable from a malicious page in a local browser. Plausible; depends on deployment.

## Examined and judged not vulnerable
- **XSS in `/profile`:** `name` passes through `escapeHtml` (covers `& < > " '`) (lines 42-44, 100).
- **Traversal in `/avatar`:** `path.basename` strips directory components (line 113). `..` resolves to a directory, so `readFile` errors and returns 404.
- **CSRF:** Bearer-header auth, no cookies.
- **SQL/command injection:** No database, `child_process`, or `eval`; data is in-memory arrays.
- **Token forgery without the key:** HMAC-SHA256 is sound; id compared as string against `String(u.id)`; no id-confusion bypass found.
- **Dependencies/supply chain:** None.
- **Network exposure:** `127.0.0.1` binding limits remote attackers (see DNS-rebinding lead).

## Instructions addressed to the reviewer in project files
None found. `README.md`, `welcome.txt`, and code comments contain only ordinary documentation and the note that all data is made up.

## Suggested fixes
1. `path.basename`, or resolve and check the prefix of `UPLOAD_DIR`.
2. Load the key from the environment and rotate it.
3. Return only `id`, `name`, `role`; restrict to admins.
4. Check note ownership or admin role.
5. Apply `escapeHtml`.
6. Validate body types, wrap the handler in try/catch, cap body size.
7. Use `scrypt` or `argon2`; add rate limiting.
8. Add token expiry; use `crypto.timingSafeEqual`.
