# SEC-008 verification (unbounded request body, `POST /login`)

Fictional fixture, local only. Original, unmodified `tests/fixtures/vulnerable-demo/server.js`.

## Static evidence

`server.js` `readBody()` appends every `data` chunk to a string with no size check; `POST /login` runs before authentication. Node's HTTP server limits header size but not body size.

## Approved test (CP1)

User-approved, with extra limits: loopback `127.0.0.1:8080` only, heap cap 256 MB (`--max-old-space-size=256`), RSS watchdog 600 MB, hard timeout 30 s, one 1 KiB control request and one 64 MiB request, no repeats, no concurrency. The server was loaded by a wrapper kept outside the repository (scratchpad), so no fixture file was changed (SHA-256 of `server.js` unchanged).

## Result

| Step | Response | Server RSS |
|------|----------|-----------|
| Baseline | - | 36.7 MB |
| 1 KiB body | 400 `bad json` in 10 ms | 37.9 MB |
| 64 MiB body, unauthenticated | 400 `bad json` after 242 ms (whole body was read first) | 99.7 MB (+63 MB, still held after the response) |

No limit tripped; the process was stopped by the script; port 8080 was confirmed free afterwards.

## Assessment

- **Reproduced:** the mechanism. An unauthenticated client can make the server read and hold a body of arbitrary size; memory grows in proportion to the body.
- **Not demonstrated:** denial of service. Exhaustion would need larger or repeated or concurrent requests, which the approval excluded. The memory was not shown to be non-reclaimable after garbage collection.
- **Impact (evidence-based):** resource consumption proportional to attacker effort, no amplification observed, and typical for a minimal server without a body-size limit. Severity: Low. Confidence of the weakness: confirmed. Confidence of DoS impact: hypothetical.

## Decision for the answer key

The weakness is real and reproducible, so it is recorded in `expected-findings.md` as an **incidental** issue (acceptable to report, not required, not a false positive if reported). It is not counted as a planted vulnerability. Any claim of "denial of service achieved" still needs a separately approved, larger bounded test.
