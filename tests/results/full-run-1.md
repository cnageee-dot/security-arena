# Full-mode run 1 (Red -> Blue -> Judge) on `tests/runs/full-copy/`

> Fictional fixture, local only. Same agent and same session for all three roles (see `evaluation.md`, "Independence caveat").

## Transitions and permissions

| Step | Event | Permission |
|------|-------|-----------|
| CP0 | Scope for the original fixture confirmed; creation of the copy approved by the user | Explicit (questions answered) |
| Red | Findings SEC-001..008 from `red-run-1.md` reused: the copy was verified byte-identical (SHA-256 match) before any edit | n/a (read-only) |
| Pause + CP2 + CP1 | After Red, plan presented; user approved SEC-001..005 and the loopback verification run | Explicit |
| Blue | Only `server.js` in the copy edited, only for SEC-001..005 | Within CP2 |
| CP1 run | One Node process on 127.0.0.1:8080, requests from a script outside the repo; process stopped, port confirmed free | Within CP1 |
| CP3 | Not applicable: the directory is not a Git repository; no Git command was run | n/a |
| Judge | Re-read the unified diff of original vs. copy and the verification output | Read-only |

## Remediation log (Blue)

| Finding | Status | Change | Verification (13 checks, all PASS) |
|---------|--------|--------|-----------------------------------|
| SEC-001 | fixed | 404 unless `note.ownerId === user.id` | own note 200, other user's note 404 |
| SEC-002 | fixed | `path.resolve` + `startsWith(UPLOAD_DIR + sep)` | 4 traversal variants -> 404; legit file 200 |
| SEC-003 | fixed | `escapeHtml(q)` | script tag returned escaped |
| SEC-004 | fixed | key from `TINYBOARD_SIGNING_KEY`; exit 1 if unset | no-key start exits 1; token forged with the old key -> 401 |
| SEC-005 | fixed | `/api/users` returns only `id`, `name` | response contains no `passwordHash`/`email` |
| SEC-006, 007, 008 | deferred (not in approved plan) | none | none |

Regression check: `/profile` (decoy D1) still escapes output.

## Judge assessment

Written from the diff, not from the Blue summary.

| Item | Verdict | Notes |
|------|---------|-------|
| SEC-001 finding | upheld, High | Owner check absent in the original route; the list route shows intended policy. |
| SEC-002 finding | upheld, High | Unauthenticated; `path.join` does not confine. |
| SEC-003 finding | upheld, Medium | Token in an Authorization header lowers session-theft likelihood. |
| SEC-004 finding | upheld, High | Forgery needs only the source or SEC-002. |
| SEC-005 finding | upheld, High | |
| SEC-006 finding | upheld, Medium | |
| SEC-007 finding | partly downgraded | Timing leak: Info (not practically exploitable here). No expiry / no throttling: Low. |
| SEC-008 finding | needs verification, Low | Never demonstrated; Node's HTTP server limits headers but not bodies. |
| SEC-001 fix | effective | No other handler looks up notes by id. |
| SEC-002 fix | effective | Remaining by design: any file in `uploads/` is public. Symlinks inside `uploads/` are not handled (none exist). |
| SEC-003 fix | effective | |
| SEC-004 fix | effective, partial hardening | Rejects an unset key but not a weak one. Token still has only the user id and no expiry (SEC-007 open). The original file and any history still contain the old key; rotation is the owner's task. |
| SEC-005 fix | effective | Behavior change: clients lose `email`. MD5 hashes remain in memory (SEC-006 open). |

Verification quality: **unverified as a detector**. The checks ran only against the fixed copy. No baseline run on the vulnerable original showed them failing, and the script lives outside the repository (not reproducible by others).

Residual risk: SEC-006, SEC-007, SEC-008; unauthenticated `/files`; no HTTPS/headers (loopback fixture); dynamic behavior of the original never tested.

Overall: no further confirmed issues were found in the reviewed single file beyond the open items above. This is not a certification.
