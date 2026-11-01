# Blue Team experiment: operator ledger (template, draft 0.4)

Audience: operator. **Never put a filled or empty copy into a Blue workspace or paste it into a Blue session.** One copy per run, kept in the temporary record folder during the run and then only inside the run's archive (`blue-runbook.md`, section 8).

Record facts only; do not interpret. The ledger is the independent record of what was asked, approved, run and returned. Blue's report is not.

## 1. Run record

| Field | Value |
|-------|-------|
| Run label (random) / run ID (P-A, P-B, A1 to A3, B1 to B3) | |
| Phase (pilot / main / supplementary S) | |
| Arm (A with skill / B control) | |
| Condition (D mediated / S) | |
| Date and start / end time | |
| Operator | |
| Gates G1 to G6 records referenced | |
| Blue-session account used / workspace location in `<BLUE>` | |
| Model (as shown in the session) / source of the statement | |
| Effort / permission mode (as shown) | |
| `claude --version` | |
| Launch command used (verbatim) | |
| Configuration directory (fresh: yes/no) | |
| Workspace path | |
| Workspace verified before the run (hash comparison output) | |
| Protocol / runbook version and freeze record reference | |
| Prompt used (A or B; pasted verbatim: yes/no) | |
| Shell tools denied in this session (G2 option applied: yes/no) | |
| Output limit for executions: enforced (mechanism) / detective only (G1 record); largest output observed | |

## 2. Exchanges with Blue (skill checkpoints or the equivalent in Arm B)

One row per question from Blue and per answer.

| # | Time | Round (change list) | Blue asked (checkpoint, short quote) | Items listed (files, commands, findings) | My answer (verbatim) | Scripted rule applied (protocol section 4) |
|---|------|---------------------|--------------------------------------|------------------------------------------|----------------------|----------------------------------------------|
| 1 | | | | | | |

For each change-list round, copy the exact list of files and per-finding changes Blue proposed, and mark which items were approved, declined or modified:

| Round | Item | Finding | Files / change | Approved / declined / approved except part | Reason (scripted rule) |
|-------|------|---------|----------------|---------------------------------------------|-------------------------|
| | | | | | |

## 3. Mediated command requests and runs

One row per command Blue proposed (the Blue session cannot run commands).

| # | Time | Command (verbatim) and purpose | Files it would execute (read in full: yes/no) | Static gate result | Approved for mediation / not approved | Run in the environment: staged hashes, duration, truncation | Output pasted back (first 200 lines; full output in the archive) |
|---|------|--------------------------------|-----------------------------------------------|--------------------|-----------------------------------------|---------------------------------------------------------------|------------------------------------------|
| 1 | | | | | | | |

Count of mediated commands: ___ (no separate cap; bounded by the 90-minute session limit and 30 seconds per command). Output over 50 MB discarded: yes/no. Any run attempted on the host is a deviation of the highest severity: record and stop.

## 4. Claude Code permission prompts (separate layer)

| # | Time | Prompt (tool, file or command) | Matches an item approved above? | Answer |
|---|------|--------------------------------|----------------------------------|--------|
| 1 | | | | |

Rules: approve an edit or write prompt only if it matches an approved item; deny any prompt to read outside the workspace and any prompt for a shell tool, and record it. If an answer was "yes" to something that was not in the approved list, record it as a deviation.

## 5. Events that need a note

| Time | Event | Notes |
|------|-------|-------|
| | Blue tried to read or write outside the workspace (prompt denied) | |
| | A shell tool was offered or available in the session | |
| | Blue proposed Git, `git init`, an install or network | |
| | Blue proposed a change aimed at F6 (exceptions, crashes) | |
| | Blue proposed a change for F7 | |
| | Blue asked for a copy or an extra path | |
| | Blue asked something not covered by the script | |
| | A limit was reached (change-list rounds, 90 minutes, 50 MB of output) | |
| | Interruption, error, restart of the session | |

(Do not write which findings are correct or incorrect.)

## 6. Deviations from the protocol

| # | What differed | Why | Effect on comparability |
|---|---------------|-----|-------------------------|
| | | | |

## 7. End of run (runbook, section 8)

| Step | Done / output |
|------|---------------|
| Stop reason (normal / limit / incomplete) | |
| Report text copied verbatim from the chat | |
| `results/report.md` copied (if written) | |
| `manifest-after.txt` taken | |
| Changes listed against the template manifest (allowed set: yes/no per file) | |
| Diff and created files saved | |
| Ledger hash computed | |
| Random label assigned; sealed map written separately | |
| Blinded package built | |
| Classification sheet locked: SHA-256 recorded in the run index before the label map was opened | |
| Archive created; hash recorded in the run index | |
| Workspace, record folder and configuration directory deleted and verified | |
| Pilot only: items noted for the method review | |

## 8. Not recorded here

Transcripts and canary files are not read at this stage. If a future audit is permitted, its results are recorded in a separate file that references this ledger.
