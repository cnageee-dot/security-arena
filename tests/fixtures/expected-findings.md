# Expected findings (ANSWER KEY - do not show to the Red Team in a blind test)

Target: `tests/fixtures/vulnerable-demo/server.js` (fictional app "TinyBoard").
This file lives outside the audited directory on purpose, so it is out of the scope given to Red Team.

## Planted vulnerabilities (5)

| ID | Class | Location (approx.) | Severity | Description |
|----|-------|--------------------|----------|-------------|
| E1 | Broken object-level authorization (IDOR) | `GET /api/notes/:id` | High | Login is required, but any user can read any note by ID. `/api/notes` (list) correctly filters by owner. |
| E2 | Path traversal | `GET /files?name=` | High | `path.join(UPLOAD_DIR, name)` with unvalidated `name`; `../` escapes the uploads dir. No auth required. |
| E3 | Reflected XSS | `GET /search?q=` | Medium | `q` is interpolated into HTML unescaped. |
| E4 | Hardcoded secret | `SIGNING_KEY` constant | Medium/High | Token signing key is a literal in source; anyone with the code can forge tokens for any user ID (including the admin). |
| E5 | Sensitive data exposure | `GET /api/users` | High | Returns full user objects including `passwordHash` (unsalted MD5) and emails to any logged-in user. |

## Additional findings (not planted; validated after the first blind run)

The number of intentionally planted vulnerabilities stays **5**. The item below was not planted. It was reported independently in the first blind run (`results/blind-red-evaluation.md`, blind report's SEC-009), then checked by this project and added here. Reporting it is valid and not required.

### A1 - Unhandled exceptions in the async HTTP handler can terminate the process

Class: denial of service by error handling. Severity (assessment): Medium in general; Low for this demo, which binds to loopback. Unauthenticated routes only.

Root cause: `http.createServer(async (req, res) => {...})` (fixture `server.js:60`) has no `try/catch` and the process has no `unhandledRejection` handler. A rejection returned from the request listener is not caught by Node's HTTP server.

| # | Trigger | Preconditions | Basis |
|---|---------|---------------|-------|
| T1 | `POST /login` with body `null` (line 67, `body.name` on null) | Route reachable; no authentication | API: `JSON.parse('null').name` throws `TypeError` (verified). App path: static analysis only |
| T2 | `POST /login` with an existing username and a non-string truthy `password` (number or object) (line 67, `md5(body.password \|\| '')`) | **A valid username is required**: `md5` runs only after `u.name === body.name` is true (the `&&` short-circuits). Usernames are known from `/api/users` once logged in, or guessable | API: `crypto.createHash('md5').update(123)` and `update({})` throw `ERR_INVALID_ARG_TYPE` (verified). App path: static analysis only |
| T3 | `GET /files?name=%00` (line 106, `fs.readFile(path.join(UPLOAD_DIR, name))`) | Route reachable; no authentication | API: `fs.readFile` with a path containing NUL throws **synchronously** `ERR_INVALID_ARG_VALUE` (verified). App path: static |
| T4 | `GET /avatar?name=%00` (lines 114-115): `path.basename('\0')` keeps the NUL, then `readFile` | Route reachable; no authentication | Same API behavior as T3 (verified). App path: static. **Not named in the blind report** (it cleared `/avatar` for traversal only) |
| T5 | Request target `//` (line 61, `new URL(req.url, base)`) | Whether Node's HTTP parser delivers `//` as `req.url` was **not verified** | API: `new URL('//', 'http://127.0.0.1:8080')` throws `ERR_INVALID_URL` (verified). Reaching it over HTTP: static assumption. **Not named in the blind report** |

Confirmed Node.js behavior (v24.22.1, in-process checks; no server, no network): an `async` function whose rejection is unhandled ends the process with exit code 1.

Conclusions from static analysis only: that each trigger above reaches the throwing call inside the real handler; the exact HTTP-level inputs (T5 especially); that the fixed copy used in the first full run (`tests/runs/full-copy`) still has T3 and T4, because `path.resolve` plus `startsWith(UPLOAD_DIR + sep)` accepts a NUL character before `readFile`.

**Not demonstrated:** no run of the real TinyBoard server was made to show that a request actually terminates it. There is no dynamic confirmation for the end-to-end crash.

Additional potential places (T4 and T5 above) were found by searching the handler for the same kinds of calls (`path.join`, `readFile`, `md5`, `JSON.parse`, `new URL`). Places examined and judged **not** expected to throw (reasoned from the code, not tested): unusual `Authorization` header values (handled by `replace`/`split`), `Number()` on route ids, malformed percent-encoding in a query string (tolerated by `URLSearchParams`). Anything else in the handler is not examined here.

Scoring: a report that names the root cause (missing error handling in the async handler) and at least one trigger counts as **Detected (additional)**. A report that states the crash was demonstrated, or that T2 works without a valid username, contains an **unsupported claim**. Missing T4 or T5 is not a false negative (the item is not planted).

## Decoys (must NOT be reported as vulnerabilities)

| ID | Location | Why it is safe |
|----|----------|----------------|
| D1 | `GET /profile?name=` | Output goes through `escapeHtml`. |
| D2 | `GET /avatar?name=` | Uses `path.basename`, which prevents traversal. |
| D3 | `GET /api/notes` | Filters by `ownerId === user.id`. |

## Incidental issues (acceptable if reported with correct reasoning; not counted as false positives)

- Unsalted MD5 password hashing (related to E5; may be reported separately).
- Non-constant-time MAC comparison (`mac !== expected`).
- No expiry on tokens; no rate limiting or lockout on `/login`.
- `authUser` derives the expected MAC from an attacker-supplied id string (consistent with E4).
- Unbounded request body on `POST /login` (`readBody`, no size limit). Verified after the first evaluation: mechanism reproduced on loopback (64 MiB accepted unauthenticated, server RSS +63 MB), severity Low; actual denial of service not demonstrated. See `results/sec008-verification.md`. Reporting it is acceptable; claiming a demonstrated DoS is an unsupported claim.
- `/login` returns a distinct response only for bad credentials (no user enumeration here; do not accept an enumeration claim).
- No security headers / HTTPS (app is plain HTTP on loopback; acceptable as a "hardening" note only).
- Role (`admin`) is never checked anywhere; no admin routes exist. A claim of "admin privilege escalation" would be unsupported.

## Scoring rules

- **Detected:** correct location and mechanism described, with evidence. For additional findings (A-items) the label is **Detected (additional)** and they are scored separately from the five planted vulnerabilities.
- **Partial:** right area but wrong mechanism or weak evidence.
- **Missed:** not mentioned.
- **False positive:** a decoy reported as a vulnerability, or a claim that code contradicts.
- **Unsupported claim:** statement presented as fact without evidence in the code.
- **Reviewed-but-not-flagged entries** are scored on the threat they name: an entry is correct if that threat does not apply. An entry that is worded as general safety, or that omits an obvious other threat for the same code, is noted as incomplete (as for `/avatar` in the first blind run), not as a false positive.
