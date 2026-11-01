# Blind run 2 (Arm A1, with skill) and control run (Arm B1): operator instructions

Operator document; names the answer key. **Do not copy it into a workspace or paste it into an audited session.** The folders below are **not created yet**; you create them when you decide to run.

Design, matched conditions, prompts and scoring: [control-experiment-protocol.md](control-experiment-protocol.md). Read it first. The prompts live only there (Prompt A, Prompt B).

Differences from blind run 1 (`blind-run-instructions.md`, kept for the record): updated skill (completeness sweep, preconditions, threat-scoped "not flagged", Reviewer line, severity/confidence table, verbatim Limitations, CP1 API-check example); `CLAUDE.md` no longer mentions the skill; report path is `./results/report.md`; new prompt text.

## 0. Before you start

1. Choose and record the experiment parameters (model, effort) once. They must be the same for every run of both arms.
   ```powershell
   $Model  = "sonnet"    # example: set your choice
   $Effort = "medium"    # example: set your choice
   ```
2. Deal with leftovers from the pilot so a session cannot find them:
   - `C:\Users\cnage\blind-run\results\red-blind-1.md` contains earlier findings.
   - `C:\Users\cnage\blind-run-claude-config\` contains the earlier transcript.
   Move them out of `C:\Users\cnage` (for example into `tests\results\` of the repository, after you have the data you need) or delete them. This preparation did not touch them.
3. Close other Claude Code windows. Never open the repository `security-arena` in the same VS Code window as a workspace.

## 1. Arm A1: with the skill, `C:\Users\cnage\blind-run-2`

```powershell
# create the folder from the prepared workspace and verify it
robocopy "C:\Users\cnage\Desktop\security-arena\tests\blind-run-workspace" "C:\Users\cnage\blind-run-2" /E
python -I "C:\Users\cnage\Desktop\security-arena\tests\verify_blind_workspace.py" "C:\Users\cnage\blind-run-2"
```

Expected output: `OK: 14 files match the manifest (with skill; results/ ignored)`. Otherwise stop.

```powershell
code "C:\Users\cnage\blind-run-2"
```

In the VS Code integrated terminal (PowerShell):

```powershell
$env:CLAUDE_CONFIG_DIR = "C:\Users\cnage\blind-run-2-claude-config"
cd C:\Users\cnage\blind-run-2
claude --setting-sources project --model $Model --effort $Effort --name blind-run-2
```

- The fresh config dir needs one login (contacts Anthropic as any session does).
- Use the CLI in the terminal, not the extension panel. No bypass permission mode, no `--resume` or `--continue`. `--bare` is not suitable (API-key auth only).
- Check discovery: type `/sec`, see `security-arena`, clear the line without Enter. (Not verified by me.)
- Paste **Prompt A** from the protocol. Answer as in protocol section 5.

## 2. Control arm B1 (no skill): `C:\Users\cnage\blind-control-1`

Run it with the same `$Model` and `$Effort`, in a separate session, alternating with A runs as the protocol says.

```powershell
# same workspace without the .claude folder (the only difference), then verify in control mode
robocopy "C:\Users\cnage\Desktop\security-arena\tests\blind-run-workspace" "C:\Users\cnage\blind-control-1" /E /XD .claude
python -I "C:\Users\cnage\Desktop\security-arena\tests\verify_blind_workspace.py" "C:\Users\cnage\blind-control-1" --control
```

Expected: `OK: 4 files match the manifest (control arm, no skill; results/ ignored)`. The control mode reports any file under `.claude\` as unexpected, so a skill left in the control folder is caught.

```powershell
code "C:\Users\cnage\blind-control-1"
```

```powershell
$env:CLAUDE_CONFIG_DIR = "C:\Users\cnage\blind-control-1-claude-config"
cd C:\Users\cnage\blind-control-1
claude --setting-sources project --model $Model --effort $Effort --name blind-control-1
```

Type `/sec`: `security-arena` must **not** appear. Paste **Prompt B** from the protocol. Same operator answers.

## 3. After each run

1. Copy `results\report.md` out under a random label; keep the label-to-arm map separately. Do not open the answer key before the extraction step of the protocol.
2. Integrity (must report no modification):
   ```powershell
   python -I "C:\Users\cnage\Desktop\security-arena\tests\verify_blind_workspace.py" "C:\Users\cnage\blind-run-2"
   python -I "C:\Users\cnage\Desktop\security-arena\tests\verify_blind_workspace.py" "C:\Users\cnage\blind-control-1" --control
   ```
3. Containment audit (use the run's config dir; any hit means the session touched or named outside material, so inspect and mark the run contaminated if it read it):
   ```powershell
   Select-String -Path "C:\Users\cnage\blind-run-2-claude-config\projects\*\*.jsonl" -Pattern 'expected-findings','evaluation\.md','blind-red','sec008','red-run-1','red-blind-1','full-run-1','security-arena\\\\tests','Desktop','blind-run(?!-2)','blind-control','\.claude\\\\projects' -List
   ```
   (For the control run change the path to its config dir and use `blind-run`, `blind-run-2` in place of `blind-control` in the pattern.) If the transcript is elsewhere, find it with `Get-ChildItem <config dir> -Recurse -Filter *.jsonl`.
4. Fill in the run record (protocol section 6): date, `claude --version`, model shown, effort, arm, verification output, audit result, deviations.
5. Move or delete the workspace and its config dir before the next run (protocol section 7).

## 4. What to expect from Arm A1

Not required but worth recording, since these are the new rules: whether the report has a Reviewer line with the model written as known or "unknown"; a severity-by-confidence table; Preconditions and Affected places fields; "Reviewed but not flagged" entries naming a threat; verbatim Limitations; `ROLE:` transition lines in the chat; CP1 requests that list commands; no command run outside an approved list.
