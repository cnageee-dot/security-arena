# TinyBoard Security Review

**Scope:** `tinyboard/` only (`server.js`, `README.md`, `uploads/welcome.txt`)
**Method:** Static, read-only analysis. No code was executed, no network access, no files under `tinyboard/` modified.
**Findings:** 7 (3 High, 3 Medium, 1 Low)

## Summary

| # | Severity | Confidence | Issue | Location |
|---|---|---|---|---|
| 1 | High | High | Broken access control on notes (IDOR) | `server.js:78-84` |
| 2 | High | High | Path traversal in `/files` | `server.js:103-110` |
| 3 | High | High | `/api/users` exposes password hashes to any logged-in user | `server.js:86-89` |
| 4 | Medium | High | Reflected XSS in `/search` | `server.js:91-95` |
| 5 | Medium | High | Weak password storage (unsalted MD5) | `server.js:14-18`, `66` |
| 6 | Medium | High | Weak token design (hardcoded key, no expiry, non-constant-time compare) | `server.js:12`, `27-40` |
| 7 | Low | Medium | Smaller hardening gaps | various |

Confidence reflects code reading only. None of the findings were dynamically confirmed.

## Findings

### 1. Broken access control on notes (IDOR), High
**Evidence:** `GET /api/notes/:id` requires login but never compares `note.ownerId` to `user.id` (`server.js:78-84`). The list endpoint (`/api/notes`) does filter by owner (`server.js:75`), so the intent to restrict access is clear.
**Impact:** Any authenticated user (e.g. bob) can read other users' notes by ID, such as notes 1 and 3 owned by alice.
**Fix:** Require `note.ownerId === user.id`, with an admin override if desired.

### 2. Path traversal in `/files`, High
**Evidence:** `name` from the query string is passed to `path.join(UPLOAD_DIR, name)` with no check that the resolved path stays inside `uploads/` (`server.js:103-110`). The endpoint requires no authentication.
**Impact:** A request such as `?name=../server.js` can read files outside the uploads directory, including the source containing the signing key.
**Fix:** Resolve the path and require it to start with `UPLOAD_DIR + path.sep`, or use `path.basename` as `/avatar` does.

### 3. User list exposes password hashes, High
**Evidence:** `/api/users` returns the full `users` array, including `passwordHash`, `email` and `role`, to any logged-in user (`server.js:86-89`).
**Impact:** Any member can obtain unsalted MD5 hashes for offline cracking (see finding 5).
**Fix:** Strip `passwordHash` from the response and restrict the route to admins.

### 4. Reflected XSS in `/search`, Medium
**Evidence:** `q` is interpolated into HTML unescaped (`server.js:91-95`). `/profile` handles the same case correctly with `escapeHtml` (`server.js:97-101`).
**Impact:** Script injection via crafted links in the page origin.
**Fix:** Wrap `q` in `escapeHtml`.

### 5. Weak password storage, Medium
**Evidence:** Passwords are hashed with unsalted MD5 (`server.js:14-18`, `66`).
**Impact:** Fast to brute-force and vulnerable to precomputed tables; amplifies finding 3.
**Fix:** Use scrypt, argon2 or bcrypt with a per-user salt.

### 6. Weak token design, Medium
**Evidence:** Signing key is hardcoded (`server.js:12`). Tokens are `userId.HMAC(userId)` with no expiry or revocation, and the MAC is compared with `!==` rather than `crypto.timingSafeEqual` (`server.js:27-40`).
**Impact:** Anyone with the source can forge a token for any user, including the admin. Tokens never expire. The non-constant-time compare is a minor timing risk.
**Fix:** Load the key from an environment variable, add an expiry, and compare in constant time.

### 7. Smaller hardening gaps, Low
**Evidence / notes:**
- No login rate limiting on `POST /login`, so password guessing is unrestricted.
- `readBody` has no size limit, so a large request body can exhaust memory.
- No security headers (CSP, `X-Content-Type-Options`).
- `/files` serves everything as `application/octet-stream`.

## Unverified leads
- Findings 2 and 6 describe exploitation paths derived from code reading only; they were not tested.
- No evidence was found of a way to write to `uploads/`, so the practical reach of the `/files` traversal is limited to reading existing files.

## Reviewed and cleared
- `/avatar` uses `path.basename`, which blocks traversal.
- `/profile` escapes its input with `escapeHtml`.
- The server binds to `127.0.0.1`, which limits exposure to the local machine. Findings 1-4 would be remotely exploitable if the bind address changed.
- The README's "no dependencies" claim holds; only Node built-ins are used.
- All data, names, passwords and keys in the source are labelled fictional.
