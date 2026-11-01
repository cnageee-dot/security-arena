# Blue Team experiment: isolation architecture (draft 0.4)

Audience: evaluator, reviewer and operator. **Hidden. Never copy it into a Blue workspace.** Design only: nothing here has been verified or run. The availability of every option on this machine is **unknown**; checking it needs the owner's approval of exact commands. Version 0.2 follows the internal review of draft 0.1 (not an independent review). Version 0.3 records the owner's decisions: session isolation is mandatory (O-3); Windows Sandbox is the priority environment if available (O-5); output limit 50 MB per execution; the first 200 lines of a command's output are returned and logged.

## 1. Policy

1. **No project code runs on the host**, by anyone: not the tested application, not a test, not a script written by Blue, not the evaluation suite, not a parse-only command such as `node --check`.
2. **Code runs only inside the isolated environment described here, after the environment has been verified (gate G1 of `blue-protocol.md`) and after the code passed the static gate.** Until G1 holds, no pilot starts and nothing is executed.
3. **A CP1 approval is not permission to execute unknown code on the host.** It means that the operator may run the command in the environment on Blue's behalf.
4. Stubs for `http` or `fs` make checks faster and observable, but **do not isolate anything**. Isolation comes only from the environment.
5. Host operations that execute no project code (hashing, listing, text diff, archiving, reading text files) are allowed.

## 2. Why isolation is needed

Evaluating a fix, and answering Blue's requests for baseline or verification checks, means executing code that Blue wrote or changed, with inputs chosen by the evaluator. Blue's code is untrusted: a model may produce faulty, destructive or (after an injection in the project text) deliberately harmful code, and tests written by Blue are code too. A command text does not show what the code it runs does.

## 3. Assets and threats

| Asset | Threat |
|-------|--------|
| Personal files and credentials on the host | read, copy, delete or encrypt by executed code |
| The Claude session's credentials (the host session is logged in) | read by executed code; never run code in the session's context |
| The repository, including hidden evaluation material | read by executed code; modification |
| Network and other machines | outbound requests, data exfiltration, scanning |
| Host resources | infinite loops, memory or disk exhaustion (including filling the writable output folder), fork bombs |
| Evaluation integrity | executed code that tampers with its results or inputs |
| The evaluator's own tooling | crafted output (file names, huge or malformed files) that harms the parser that reads it |
| Later Blue sessions | reading earlier runs' records or the hidden documents (see section 8) |

## 4. Requirements for the isolated environment

| ID | Requirement |
|----|-------------|
| R1 | No network except loopback **inside the environment** (needed by socket-based checks); no route to the host, to any other machine, or to DNS |
| R2 | No access to personal files; only explicitly provided inputs are visible |
| R3 | Inputs are read-only: the staged application copy, the property suite, the case corpus. The application is run from a **guest-local writable work copy** made inside the environment from the staged copy; the work copy is not mapped to the host and is destroyed with the environment |
| R4 | One writable location **visible to the host**: the output folder, empty at start, containing nothing personal. Its 50 MB limit (set by the owner) is either **enforced** by a mechanism verified at G1 (section 4a) or is only a **detective** limit, and the run record says which |
| R5 | Ephemeral: the environment, including the work copy, is destroyed after each execution session and no state carries over. Restart persistence is therefore tested only inside one session |
| R6 | Limits on time (per case and total), memory, and output size |
| R7 | No clipboard, audio, printer or device sharing with the host |
| R8 | Outputs are transferred one way and treated as **data** on the host: never executed or opened with active content; a schema, a size limit and a file-name allow-list apply |
| R9 | No real secrets of any kind (credentials, tokens, personal data) and no Claude credentials in the environment. Throwaway values that the application under evaluation generates inside its work copy (for example a generated test key) are allowed; they never leave the environment and are never written to the output folder |
| R10 | The environment's setup is reproducible and its isolation is itself checked (section 7) |

## 4a. The output limit: enforcement, or an honest limitation

The owner's limit is 50 MB of output per execution. A limit that is only checked after the run does not stop a faulty or hostile program from filling the disk that holds the output folder. The mechanisms differ:

| Mechanism | What it gives | Status |
|-----------|---------------|--------|
| Q1 fixed-size volume: a virtual disk of fixed size (about 50 MB plus file-system overhead) mounted on the host, with the output folder on it | a hard limit: writes fail when the volume is full | feasibility unverified; needs administrator rights and the owner's approval |
| Q2 disk quota for a user on an NTFS volume | a hard limit if the sandbox's writes are accounted to that user | unverified; how the sandbox's writes are accounted is unknown |
| Q3 watchdog: the host polls the output folder and stops the environment above the limit | a detective limit with a bounded overshoot (depends on the polling interval and the write speed); not a guarantee | feasible; the overshoot is not measured |
| Q4 post-run check only | detection after the fact; no protection against disk exhaustion | always available; the weakest |

Rule: gate G1 records which mechanism is in place and, where possible, demonstrates the limit with an approved test (a write above the limit is stopped or detected). If only Q3 or Q4 is available, the run record says "detective only", the methodology records a **limitation** (a faulty program can write beyond 50 MB before detection; the free space of the host volume is the real bound), and the output folder is placed on a volume with limited free space. The 200-line limit is a presentation limit for what is shown to Blue and logged; it is not a disk limit.

## 5. Contexts: what runs where

| Activity | Where |
|----------|-------|
| The Blue session (model conversation, reading, editing the workspace) | host, under the dedicated Blue-session account (section 8). Shell tools are denied (launch options in the runbook), so the session cannot execute anything |
| Commands requested by Blue (condition D) | inside the environment, run by the operator, only after the static gate; output pasted back as data |
| Evaluation: property suite, differential runner, Blue's own tests | inside the environment, after the static gate |
| Hashing, diff, archiving, reading reports | host (Level 0; no project code) |

The environment never holds Claude credentials and the Blue session never runs there. This separates the credential holder from the code that is executed.

## 6. Procedure for one execution session (mediated commands and evaluation)

1. **Static gate (host, no execution).** A reviewer reads the Blue diff, every file Blue created, the proposed command and the full text of every file the command would execute: no network calls, no child-process creation, no `eval` or dynamic `require` with computed names, no file-system access outside the project, no obfuscation, size within limits. A failure is recorded as a violation (or, for a mediated command, as a declined request) and **nothing is executed**.
2. **Snapshot.** A manifest of the workspace is taken and stored.
3. **Stage.** Copy to a staging folder outside every workspace: the application copy to be executed (a copy of the current workspace `tinyboard/`), and, for evaluation, the pristine copy, the property suite and corpus, and the Blue-authored tests. Compute and record hashes.
4. **Start the environment** with R1 to R9 in force. Staging is mapped read-only; the output folder is the only writable location visible to the host.
5. **Run** from a guest-local work copy made from the staged copy (R3). Run the command, or the suite on the pristine application first (the suite's own baseline), then on the final application, then Blue's tests on both. For the restart scenarios the process is stopped and started again in the same work copy within the session. Limits per R6 and `acceptance-properties.md`, section 6.
6. **Collect** outputs from the output folder only; close the environment (destroyed, with the work copy). Check the output size against R4 and record whether the limit was enforced or only detected (section 4a). Secret values never go to the output folder.
7. **Parse** outputs on the host as data under R8. For a mediated command, paste the output into the Blue session as data (the first 200 lines, with a notice if truncated; the full output within the 50 MB limit stays in the archive); record command, staged hashes, output and duration in the ledger.

## 7. Checking the isolation itself (gate G1; needs the owner's approval of exact commands)

Before the pilot, and at each freeze, an operator-approved check demonstrates from **inside** the environment: no external network (an attempt to resolve a name or reach any address fails); in-environment loopback works; the read-only mapping rejects a write; the output folder is the only writable path visible to the host (the guest-local work copy is writable but is not mapped to the host); the output-limit mechanism of section 4a is demonstrated (a write above the limit is stopped or detected; if only a detective mechanism exists, the run records say "detective only"); no personal folders are visible; the clipboard is not shared; no Claude credentials are present; the environment is gone after closing. Each check is listed as an exact command for approval beforehand, and the result is recorded in the freeze folder. Until it has been done, the isolation is **unverified**: the pilot is forbidden and no code runs anywhere.

## 8. Contamination between sessions and runs

The hidden documents and earlier runs' records live on the same disk as later Blue sessions. Controls (they reduce the risk and do not remove it):
- shell tools denied in both arms, so a session cannot list or read files through a shell;
- permission mode `manual`, with every prompt to read outside the workspace denied and logged;
- the workspace and configuration directory deleted after each run; run records kept as archive files only so that each record is one hashed unit. **An archive is not an access control**: any account that can read the file can open it. The protection comes from the Blue account having no read access to where the records are stored (gate G6), not from the file format; archives are unpacked only for evaluation, by the operator, after the phase;
- **mandatory (owner decision O-3):** Blue sessions run under a dedicated standard Windows account that cannot read the repository, the operator's folders, the records and archives of runs, the freeze records, or any other run's workspace or configuration directory; this is verified at gate G6 (`blue-protocol.md`, section 6; `blue-runbook.md`, section 4);
- a future transcript audit and a canary file (`evaluation-tools-design.md`, section 9) would add evidence; the canary is a signal only.

Whether a read of an absolute path outside the workspace raises a permission prompt in this setup is **not verified**; it is checked in the G2 and G6 dry sessions.

## 9. Options for the environment

| Option | Isolation | Notes and unverified points |
|--------|-----------|-----------------------------|
| **A. Windows Sandbox** (priority environment, owner decision O-5, if available) | Lightweight disposable virtual environment; configuration can disable networking, virtual GPU, clipboard, and map folders read-only or writable; destroyed on close | The host runs Windows 10 Pro; the feature must be enabled, which was **not checked**. The configuration keys must be confirmed against Microsoft's documentation (not consulted; no network use). Needs a Node runtime inside: a portable `node.exe` copied into a read-only mapped folder (creating that copy and verifying its hash is a separate permission). Starts fresh each time. Loopback inside the guest is expected to work with networking disabled (to be verified at G1) |
| B. Hyper-V virtual machine with no network adapter | Strong; reversible with checkpoints | Needs Hyper-V (Pro supports it) and a guest image with Node; heavier to maintain |
| C. WSL2 distribution or container with networking disabled | Strong if the network is truly off and mounts are read-only | Availability **unknown**; mounts of host drives in WSL are on by default and must be switched off; backslash-path variants are not meaningful on Linux |
| D. Separate Windows user account | For code execution: weak (same kernel, same disks, file-rights mistakes). For Blue sessions: the **mandatory separation mechanism** (O-3), valid only if the account cannot read the operator's side (tested at G6) | Not an execution environment. How the operator and the Blue account share the machine, and how the login is handled, are not decided |
| E. Node `--permission` flag | Defence in depth only | Whether the installed Node supports and enforces the needed restrictions (file reads and writes, child processes, workers) was **not verified**; it does not replace the environment |
| F. No environment | No execution | The pilot is **not run**; there is no static-only fallback pilot. A static evaluation of existing outputs remains possible but is not an experiment run |

Recommendation: A (or B, if A is unavailable). If neither is available, the Blue experiment does not start; the owner decides whether to prepare an environment or to shelve the experiment.

## 10. Data flow

```
host (trusted): static gate -> staging folder (read-only into the environment)
                                      |
                                      v
                  isolated environment: run command, suite or tests (no external network)
                                      |
                                      v  (the only host-visible writable folder; limit per section 4a)
host: output folder -> parse as data (schema, size) -> ledger / results records
```

Nothing flows from the environment to anywhere except the output folder. Nothing from the host (other than the staged inputs) is visible inside. Nothing from the environment is ever executed on the host.

## 11. Limits

- Windows Sandbox and virtual machines share the host's hardware and hypervisor; they are strong but not absolute.
- A malicious executed program could tamper with the outputs it writes. The suite's outputs are therefore compared with an independently produced baseline (suite on the pristine application) and with sanity checks; anomalies are reviewed by a person.
- Time-based checks and resource limits can produce flaky results; each result needing a limit is recorded with the limit.
- The static gate is a reading of code by a person; it can miss things (`evaluation-tools-design.md`, T5). It is a gate in front of the environment, not a replacement for it.
- The only writable places for executed code are the guest-local work copy and the output folder; the work copy is not visible to the host. Restart persistence is tested inside one session only and says nothing about persistence across the destruction of the environment.
- The 50 MB limit is a hard limit only if a mechanism of section 4a was verified at G1; otherwise it is detective and recorded as a limitation.

## 12. Open questions

1. Whether Windows Sandbox (the priority, O-5) is available and enabled here; if not, which alternative.
2. Where the portable Node runtime for the environment comes from, and who verifies its hash.
3. Whether `--permission` is available and behaves as needed.
4. Whether reading an absolute path outside the workspace raises a prompt in the `manual` mode (checked at G2).
5. How the operator and the Blue-session account share the machine and how the login is handled (implementation of O-3).
