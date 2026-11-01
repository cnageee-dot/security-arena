# Findings for remediation: TinyBoard

Source: Red Team report (static review of `./tinyboard`, nothing was executed). Severities are preliminary. Line numbers refer to `tinyboard/server.js`.

## F1 - Any logged-in user can read any note

Preliminary severity: High   Confidence: confirmed (static)
Location: `server.js:78-84`
Category: Broken object-level authorization

Description: `GET /api/notes/:id` authenticates the caller but never compares the note's `ownerId` with the caller's id. The list route (`server.js:73-76`) filters by owner, so the by-id route is inconsistent with it.
Preconditions: a valid token for any account; the note id exists (ids are small sequential integers).
Attack scenario: `bob` requests `/api/notes/1` and `/api/notes/3`, which belong to `alice`, and reads their content.
Evidence: `server.js:81-83` looks the note up by id and returns it with no ownership check.
Impact: disclosure of every user's notes to any authenticated user.

## F2 - Unauthenticated file read outside the uploads directory

Preliminary severity: High   Confidence: confirmed (static)
Location: `server.js:103-110`
Category: Path traversal

Description: the `name` query parameter of `GET /files` is joined to `UPLOAD_DIR` with `path.join` and read. `..` segments are normalized and nothing checks that the result stays inside `UPLOAD_DIR`. The route runs without any authentication.
Preconditions: network reach to the listener; the target file is readable by the Node process.
Attack scenario: `GET /files?name=../server.js` returns the application source, including the signing key described in F4. Percent-encoded separators are decoded by `URLSearchParams` before the join.
Evidence: `server.js:104-105`, `const name = url.searchParams.get('name') || ''; return fs.readFile(path.join(UPLOAD_DIR, name), ...`
Impact: arbitrary file read as the server user; together with F4 it allows forging a token for the first account (id 1).

## F3 - Reflected XSS in the search page

Preliminary severity: Medium   Confidence: confirmed (static)
Location: `server.js:91-95`
Category: Cross-site scripting

Description: the `q` query parameter is interpolated into an HTML response (`Content-Type: text/html`) without encoding.
Preconditions: a victim opens a crafted link; no authentication is needed. Impact depends on how a client stores the token (the token is sent in a header, not a cookie).
Attack scenario: `/search?q=<script>...</script>` runs script in the application's origin.
Evidence: `server.js:94`, `` `<h1>Results for ${q}</h1><p>No notices match.</p>` ``
Impact: script execution in the victim's browser on the application's origin.

## F4 - Token-signing key is a literal in the source

Preliminary severity: High   Confidence: confirmed (static)
Location: `server.js:12`, used at `server.js:27-30`
Category: Hardcoded secret

Description: the HMAC key is a string literal. A token is `userId.HMAC(userId)`, so anyone who knows the key can compute a valid token for any user id.
Preconditions: the attacker has the source code, or can read it through F2.
Attack scenario: compute the MAC for user id 1 offline and send `Authorization: Bearer 1.<mac>` to act as the first account (id 1) without a password.
Evidence: `server.js:12` (value not reproduced here), `server.js:28`.
Impact: full authentication bypass and impersonation of any account.

## F5 - User list exposes password hashes

Preliminary severity: High   Confidence: confirmed (static)
Location: `server.js:86-89`, data at `server.js:16-19`
Category: Sensitive data exposure

Description: `GET /api/users` returns the complete `users` array, including `passwordHash`, `email` and `role`, to any authenticated user. The hashes are unsalted MD5 values.
Preconditions: a valid token for any account.
Attack scenario: `bob` calls `GET /api/users` and receives the first account's password hash for offline cracking.
Evidence: `server.js:88`, `return sendJson(res, 200, users);`
Impact: disclosure of credential hashes and personal data to non-privileged users.

## F6 - Unhandled exceptions in the async request handler can end the process

Preliminary severity: Medium   Confidence: likely (not executed; relies on Node runtime behavior)
Location: handler at `server.js:59`; trigger points at `server.js:60`, `server.js:65-66`, `server.js:105`, `server.js:114`
Category: Denial of service / error handling

Description: the request handler is an `async` function with no outer `try/catch`, and the process has no `unhandledRejection` handler. In current Node versions an unhandled rejection terminates the process. Several unauthenticated inputs make the handler throw:
- T1: `POST /login` with a JSON body of `null` (`body.name` is read on `null`, line 66).
- T2: `POST /login` with an existing username and a non-string, truthy `password` such as a number or an object (`md5()` is called with a non-string, lines 14 and 66). The hash function is only reached when `u.name === body.name` is true.
- T3: `GET /files?name=%00` (a NUL character in the path passed to `fs.readFile`, line 105).
- T4: `GET /avatar?name=%00` (same, line 114; `path.basename` does not remove the NUL character).
- T5: a request target such as `//` (`new URL(req.url, ...)` throws on line 60). Whether the HTTP parser delivers such a target to the handler was not checked.
Preconditions: network reach to the listener; Node 15 or later for the process to end (the version used is not stated); T2 additionally requires an existing username.
Attack scenario: one request of the kinds above stops the server until it is restarted.
Evidence: `server.js:59-66`, `server.js:105`, `server.js:114`.
Impact: loss of availability for all users.

## F7 - Reflected XSS in the profile page through incomplete output encoding

Preliminary severity: Medium   Confidence: likely (not executed)
Location: `server.js:42-44`, `server.js:97-101`
Category: Cross-site scripting

Description: `GET /profile` writes the `name` query parameter into an HTML response. The `escapeHtml` helper that is applied to it encodes only `&`, `"` and `'`; it does not encode `<` or `>`, so markup in the parameter reaches the page unchanged.
Preconditions: a victim opens a crafted link; no authentication is needed.
Attack scenario: `/profile?name=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E` renders an `img` element whose `onerror` script executes in the application's origin.
Evidence: `server.js:98` reads the parameter and `server.js:100` writes `escapeHtml(name)` into the page; the helper is at `server.js:42-44`.
Impact: script execution in the victim's browser on the application's origin.
