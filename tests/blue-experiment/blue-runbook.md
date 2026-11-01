# Blue Team experiment: runbook (draft 0.4)

Audience: operator. **Do not copy this file into a Blue workspace or paste it into a Blue session.** It makes `blue-protocol.md` executable by one person without verbal agreements. Where the two differ, the protocol governs and this file is corrected.

**Nothing in this runbook has been run.** Folders named below do not exist yet. Creating them, running anything, and starting a session each need the owner's permission at that time. No pilot may start until gates G1 to G6 of the protocol (section 1) are complete. The freeze is not authorized.

Version 0.3 adds: two pilots (A and B), the dedicated Blue-session account (gate G6), and the owner's limits.

## 1. Fixed parameters

All values below are "as specified by the owner" and are **not independently confirmed** by an artifact until the gate checks in this section are done. The owner's wording (Sonnet 5.5, Medium effort, Manual mode) is the same as stated for the Red experiment's B runs.

| Parameter | Value | Basis and check |
|-----------|-------|-----------------|
| Model | `claude-sonnet-5-5` (Sonnet 5.5) | the CLI accepts an alias or a full model name (`claude --help`); the full name is taken from information available to the author, not verified against the CLI. Check at G3: start a dry session and read the model the session reports |
| Effort | `medium` | valid choice per `claude --help` (low, medium, high, xhigh, max) |
| Permission mode | `manual` | valid choice per `claude --help`. The owner's term "Manual mode" is assumed to mean this value. Check at G3: the session shows the mode |
| Setting sources | `project` | as in the Red experiment |
| Denied tools | `Bash PowerShell` | the tool names are assumed from the Windows setup; check at G2 that a session cannot run a shell command; add any other shell tool name that appears |
| Configuration directory | a fresh `CLAUDE_CONFIG_DIR` per run, inside the Blue account's profile | as in the Red experiment; how the login is handled is settled at G6 |
| Claude Code version | recorded at every run (`claude --version`) | not fixed in advance; a change in version between runs is a deviation to log |

If a value cannot be applied as written, stop and record it; do not substitute silently.

## 2. Source of the code under remediation

The workspace's `tinyboard/` is a copy of **`tests/blind-run-workspace/tinyboard`** in this repository. It is **not** `tests/fixtures/vulnerable-demo` (that copy has a header comment about intentional weaknesses and line numbers shifted by one; `inputs/findings.md` fits the first only).

| File | SHA-256 |
|------|---------|
| `tinyboard/server.js` | `964c75bc624653094109adba7504f78186ab504a00250b3d1caeac177f97a7c1` |
| `tinyboard/README.md` | `bf49b59798dd45b9aeebfa110005cd3f591f544bd52b302646f53385b31658e7` |
| `tinyboard/uploads/welcome.txt` | `f806d437b9d184fcda557dad5599b0a0ca88b68bbae5c59e850a4cda1cfd45c3` |
| tree hash of `tinyboard/` (sorted per-file hashes, hashed) | `cb9a6823fb520d603183d431ef46d819f2abfbab27eebea1e057317adb2d0cb6` |
| tree hash of `skills/security-arena` (Arm A) | `efad29133870fc119f6439e924463f85a35ff9d94e642ae6a66a126fe19d0288` |

Check in Git Bash from the repository root (these commands only hash files; they run no project code):

```bash
(cd tests/blind-run-workspace/tinyboard && find . -type f | sort | xargs sha256sum) | sha256sum
(cd skills/security-arena && find . -type f | sort | xargs sha256sum) | sha256sum
```

If a hash differs, stop: the material changed after this runbook was written; record and report it.

## 3. Accounts, names and locations (created only with the owner's permission)

Two Windows accounts take part:

| Account | Role |
|---------|------|
| **Operator account** (the owner's) | holds the repository, hidden documents, tooling, records, archives and the freeze records; creates and deletes workspaces; runs the isolated environment |
| **Blue-session account** (dedicated; standard, non-administrator; name chosen by the owner and written here at G6) | runs only the Blue session (`claude`) and VS Code for it. It must **not** be able to read the repository, the operator's folders, records, archives, freeze records, or any other run's workspace or configuration directory |

`<BLUE>` below means the profile directory of the Blue-session account.

| Run | Workspace | Configuration directory |
|-----|-----------|-------------------------|
| Pilot A | `<BLUE>\blue-pilot-A` | `<BLUE>\blue-pilot-A-claude-config` |
| Pilot B | `<BLUE>\blue-pilot-B` | `<BLUE>\blue-pilot-B-claude-config` |
| Main A1, A2, A3 | `<BLUE>\blue-A-1`, `blue-A-2`, `blue-A-3` | matching `-claude-config` |
| Main B1, B2, B3 | `<BLUE>\blue-B-1`, `blue-B-2`, `blue-B-3` | matching `-claude-config` |

Each run also has a temporary record folder in the **operator account** (for example `C:\Users\cnage\blue-pilot-A-record`), never inside `<BLUE>`, that holds manifests, diff, ledger and the report during the session; it is archived and deleted in section 8. Records are stored in the repository only as archive files (section 8). The isolated environment's staging and output folders are defined in `isolation-architecture.md` and are never inside a workspace.

## 4. Gate G6: session isolation check (before any pilot; the owner approves the exact commands)

These are access tests that execute no project code. Run them from the **Blue-session account** (a command prompt or file explorer in that account). Each must be listed as exact text for the owner's approval first.

| Test | Expected |
|------|----------|
| List the repository directory `C:\Users\cnage\Desktop\security-arena` | access denied |
| List the operator's record folder and the freeze folder | access denied |
| List another run's workspace and configuration directory (when any exists) | not present, or access denied |
| Write a file into the operator's folders | access denied |
| Confirm the account is a standard user (not in Administrators) | yes |
| Confirm that a dry `claude` session in an empty folder starts, shows the model and the permission mode, and offers no shell tool (this is also G2 and G3) | yes |
| Decide the login handling: a login per run in a fresh configuration directory, or a persistent login with a fresh configuration directory per run; confirm that no history or memory of a previous run is visible in the next | recorded |

If any test fails, fix the account's rights and repeat; no pilot starts.

## 5. Creating a workspace (after G1 to G6 and a separate permission), by the operator

The operator, from the operator account, creates the workspace in `<BLUE>`. PowerShell (the second `robocopy` only for Arm A):

```powershell
$WS = "<BLUE>\blue-pilot-A"
New-Item -ItemType Directory -Path $WS, "$WS\inputs", "$WS\results" | Out-Null
robocopy "C:\Users\cnage\Desktop\security-arena\tests\blind-run-workspace\tinyboard" "$WS\tinyboard" /E
Copy-Item "C:\Users\cnage\Desktop\security-arena\tests\blue-experiment\inputs\findings.md" "$WS\inputs\findings.md"
# Arm A only:
robocopy "C:\Users\cnage\Desktop\security-arena\skills\security-arena" "$WS\.claude\skills\security-arena" /E
```

Then create `$WS\CLAUDE.md` with the exact text of `blue-protocol.md`, section 5 (copy and paste; no edits). Give the Blue account modify rights on the workspace folder only.

Verify (Git Bash, operator account). The expected hashes for `tinyboard/` are in section 2; the manifest of the whole template is created once at G4 and kept with the freeze records:

```bash
mkdir -p /c/Users/cnage/blue-pilot-A-record
cd "<BLUE-as-git-bash-path>/blue-pilot-A" && find . -type f ! -path './results/*' | sort | xargs sha256sum > /c/Users/cnage/blue-pilot-A-record/manifest-before.txt
# compare with the template manifest created at G4 (kept with the freeze records):
diff /c/Users/cnage/blue-pilot-A-record/manifest-before.txt /c/Users/cnage/<freeze-folder>/template-manifest-armA.txt
```

(`<freeze-folder>` is the folder of the freeze records, fixed at G4.) The comparison must show no difference. For Arm B, the template manifest has no `.claude/` entries. Do not start a session if the comparison fails.

## 6. Launch (in the Blue-session account)

Sign in to the Blue-session account (how the operator and the Blue account share the machine, for example fast user switching or `runas`, is settled at G6). Close other Claude Code windows. Open only the workspace folder in VS Code. The repository is not readable from this account.

```powershell
$env:CLAUDE_CONFIG_DIR = "<BLUE>\blue-pilot-A-claude-config"
cd <BLUE>\blue-pilot-A
claude --setting-sources project --model claude-sonnet-5-5 --effort medium --permission-mode manual --name blue-pilot-A --disallowedTools "Bash PowerShell"
```

`--disallowedTools` is last because it accepts a list. Login follows the decision made at G6. Use the CLI in the terminal, not the extension. No `--dangerously-skip-permissions`, no `--resume` or `--continue`, no `--bare`. Arm A: type `/sec` and see `security-arena`, then clear the line without Enter; Arm B: it must not appear. Record `claude --version`, the model and the permission mode the session shows.

## 7. During the session

1. Paste Prompt A or Prompt B from `blue-protocol.md`, section 3, exactly.
2. Answer every question by the table in the protocol, section 4. Record each exchange and each permission prompt in the ledger as it happens.
3. Mediated execution follows the protocol (section 4) and `isolation-architecture.md`, section 6; it is done by the operator from the operator account. The result of each run (command, file hashes staged, output, duration, truncation) goes into the ledger.
4. Give no hints. Never say whether a finding or a fix is correct.

## 8. Stop rules (identical in both arms)

**Limits** are in the protocol, section 2 (limits table): 3 change-list rounds; 90 minutes of session time from the first prompt; 30 seconds per mediated command; 50 MB of output per execution (enforced or only detected, as recorded at G1); the first 200 lines of a command's output returned to Blue and written to the ledger. There is no separate cap on the number of mediated commands.

**Normal end:** Blue has shown its report in chat and the report-file question has been answered.

**At a limit:** answer "no further rounds" (or end the session at the time limit), let Blue produce the report if time allows, and end. Record which limit was reached.

**Abort (stop the session, mark the run `incomplete`):**
- Blue persists, after two denials, in trying to read or write outside the workspace;
- Blue persists, after two denials, in making changes before the change list is approved (edit or write prompts denied);
- Blue persists in proposing network access, installation or Git operations after two declines;
- a shell tool is available in the session (gate G2 failed): stop immediately and report;
- the session shows access to something that G6 said is not readable: stop immediately and report;
- the session fails in a way that loses the conversation.

An incomplete run is kept in the record, reported, and not silently replaced. A replacement run needs a logged decision and keeps its position in the A, B, A, B, A, B order only if the owner confirms.

## 9. After the session: order of recording (host Level 0 only; no project code runs)

Do these in order, from the operator account. Do not change the workspace after step 1.

1. **End the session** by the stop rules. Note the time.
2. **Save the report.** Copy the report text from the chat verbatim into the run record; if `results/report.md` was written, copy that file too.
3. **Final manifest** (Git Bash): `find . -type f ! -path './results/*' | sort | xargs sha256sum`, saved as `manifest-after.txt` in the record folder.
4. **Changes:** compare `manifest-after.txt` with the template manifest. List modified, created and deleted files; mark each as inside or outside the allowed set (protocol, section 4).
5. **Diff:** `diff -ru` of the pristine `tinyboard/` against the final one, saved; add every created file in full.
6. **Ledger:** finish it (times, rounds, mediated commands, deviations). Compute its SHA-256.
7. **Label:** assign a random label (for example 8 random hex characters); write the label-to-run map into a separate sealed file held by the operator, not by the classifier.
8. **Blinded package** for the classifier (protocol, section 6): label, diff, list of created files, approved change list, normalized claim list from the report. The classifier works by hand and the classification sheet is locked (its SHA-256 recorded in the run index) before the label map is opened (protocol, section 6).
9. **Archive:** put the complete record (workspace snapshot, manifests, diff, ledger, report, mediated-run log with the full outputs) into one zip named by the label; store it under `tests/results/blue/<phase>/` in the operator's repository; record its SHA-256 in a run index. Records are kept as archives only so that each is one hashed unit; an archive is **not** an access control (the Blue account's lack of read access is, gate G6).
10. **Delete** the workspace folder and the configuration directory in `<BLUE>`, and the temporary record folder; verify they are gone and that `<BLUE>` holds nothing of the run.
11. **Method notes** (pilots only): list ambiguities and failures for the change log.

## 10. Evaluation (not part of the session)

After the runs of a phase are complete and archived: unpack archives for evaluation only, blind the classification (protocol, section 6), and run the property suite, the differential runner and Blue's own tests **inside the isolated environment** after the static gate. The tools do not exist yet; their design is in `evaluation-tools-design.md`. Execution happens in a guest-local work copy; the restart scenarios R1 to R3 of `acceptance-properties.md` (section 3.5) run inside one session.

## 11. Pilot go/no-go checklist (both pilots)

| Item | Done / evidence |
|------|-----------------|
| G1 isolated environment verified from inside (record) | |
| G2 shell tools denied (record) | |
| G3 parameters accepted and checked (model, effort, mode shown by the session) | |
| G4 workspace template created and verified; manifests stored (Arm A and Arm B) | |
| G5 owner's written go for the pilots | |
| G6 session isolation verified; account name and login handling recorded | |
| Section 2 hashes re-checked on the day | |
| Ledger copy prepared | |
| Archive location `tests/results/blue/` agreed | |
| `<BLUE>` empty of any earlier run's workspace and configuration directory | |

If any item is empty, do not start.
