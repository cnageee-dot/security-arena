# Tests

Behavioral tests for the Security Arena skill (these are not unit tests; the structural checks are in `scripts/validate_repo.py`).

`coverage.md` lists which skill behaviors have been exercised and which have not.

```
fixtures/vulnerable-demo/   fictional vulnerable app (TinyBoard). Do not deploy.
fixtures/expected-findings.md   ANSWER KEY. Keep it out of the auditing session.
runs/                       working copies for full-mode runs (disposable)
results/                    reports and evaluations of past runs
```

## Prepared blind run

**Next stage:** `blind-run-2-instructions.md` (operator steps for run A1 with the skill and run B1 without it) and `control-experiment-protocol.md` (matched conditions, prompts, scoring) describe the controlled comparison. Neither has been run. `verify_blind_workspace.py --control` verifies a workspace that must not contain the skill.

A ready workspace for a blind Red Team run in a new Claude Code session is in `blind-run-workspace/` (skill copy, fixture copy with only the text hints removed, empty `results/`). Operator steps, isolation tiers, the starting prompt and the post-run checks are in `blind-run-instructions.md` (keep that file out of the audit session). `verify_blind_workspace.py` and `blind-run-manifest.sha256` check that the workspace was not altered. The workspace lives inside the repository, so for evidence-grade results copy it out first (Tier B in the instructions).

**Blue Team experiment** (design only, not run): see `blue-experiment/README.md`.

## Running a genuinely blind test (recommended protocol)

The first evaluation (`results/evaluation.md`) was not blind. To get meaningful results:

1. Start a **fresh session** (new conversation, no memory of this repository's tests). Do not mention what is in the fixture.
2. Install the skill from `skills/security-arena` into the tool's skills directory (or a project-local one), as described in the root README.
3. Prepare a **separate directory containing only a copy of `fixtures/vulnerable-demo/`**, with no `expected-findings.md`, no `results/` and no references to them. Open the session in that directory.
4. Ask: `Use security-arena in red mode on this project.` Answer the checkpoints honestly (CP0 yes, CP4 as you like, CP1 no for the first run).
5. Save the report. Only then compare it with `fixtures/expected-findings.md` using its scoring rules: detected / partial / missed / false positive / unsupported claim.
6. For `judge`, start another fresh session and provide only the diff and findings, not the Red/Blue transcripts.
7. Repeat on each supported tool (Claude Code, Codex) and note the tool and model versions in the result file.

Safety: run only on loopback, use only the fictional data, never expose the fixture server to a network.
