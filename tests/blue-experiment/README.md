# Blue Team experiment: index (draft 0.4)

**Status: draft 0.4, design only.** Nothing in this folder has been run. No executable test, reference fix, mutant, working copy of TinyBoard, canary file, workspace, account or tool code exists; each needs a separate decision of the project owner. **No project code is executed anywhere at this stage.** No pilot may start until the gates G1 to G6 in `blue-protocol.md` are complete (verified isolated environment, shell tools denied, parameters accepted, workspace template verified, the owner's written go, verified session isolation). **The freeze is not authorized.**

Version 0.2 followed an internal review of draft 0.1; version 0.3 records the owner's decisions O-1, O-2, O-3 and O-5, the sample size and the limits. The internal review was written by the authoring agent and is **not** an independent review. The documents are being prepared for an independent stage-1 review by a model other than the author; it has not been done. Version 0.4 answers the independent static review of v0.3 (CONDITIONAL PASS, four MAJOR points); v0.4 itself has not been independently reviewed.

Question: when given a list of findings, does Blue Team (Security Arena skill, mode `blue`, Arm A) remediate them correctly, minimally, and within the permissions it was given, compared with Claude Code without the skill (Arm B)? One pilot of each arm comes first; pilots are not part of the sample.

## Who may read what

The experiment has three audiences. **Never copy a hidden file into a Blue workspace, paste it into a Blue session, or let the Blue session reach it.** The operator documents name the traps; the evaluator documents contain the pass criteria.

| File | Audience | May go into a Blue workspace? |
|------|----------|-------------------------------|
| `inputs/findings.md` | **Blue Team** (the only file of this folder it sees) | Yes, copied verbatim to `inputs/findings.md` of the workspace |
| `README.md` (this file) | operator | No |
| `blue-protocol.md` | operator | No |
| `blue-runbook.md` | operator | No |
| `operator-ledger-template.md` | operator | No |
| `blue-supplementary-S.md` | operator | No |
| `blue-rubric.md` | evaluator | **No** (contains the expected behavior) |
| `acceptance-properties.md` | evaluator | **No** (contains the pass criteria) |
| `evaluation-tools-design.md` | evaluator | **No** |
| `isolation-architecture.md` | evaluator, operator | **No** |
| `independent-review-checklist.md` | reviewer | **No** |

A Blue workspace, once created, will contain only: `CLAUDE.md` (text in `blue-protocol.md`, section 5), `tinyboard/` (a copy of `tests/blind-run-workspace/tinyboard`, hashes in the runbook), `inputs/findings.md`, an empty `results/`, and, in Arm A only, `.claude/skills/security-arena/`. It lives in the profile of a dedicated Blue-session account that cannot read this repository.

Caveat: this folder is inside the repository, which is reachable by absolute path from any session running under an account that can read it. The mandatory separation (dedicated account, gate G6) and the other controls, and their limits, are in `blue-protocol.md` (section 6) and `isolation-architecture.md` (section 8).

## Sequence

1. Preliminary methodology (these documents, draft 0.4).
2. **Early independent stage-1 review** of the documents (requested by the owner; by a model other than the author; not yet done).
3. **Gates G1 to G6**: verified isolated environment (Windows Sandbox is the priority, if available), shell tools denied, parameters accepted, workspace template verified, the owner's written go, verified session isolation.
4. **Pilot A** and **pilot B**, one run each; both excluded from the sample.
5. **Evaluation dry run** on both pilot outputs, in the environment.
6. Fix the problems the pilots and the dry run reveal; record every change.
7. **Full independent review** (`independent-review-checklist.md`), stages 1 and 2.
8. **Final freeze**: hashes of all frozen materials; no changes afterwards. *Not authorized yet.*
9. **Main runs**: Arm A against Arm B, condition D (mediated execution), 3 runs of A and 3 runs of B, alternating A, B, A, B, A, B.
10. Later and separately: Judge as an independent evaluator of the main-run results (sealed); the supplementary experiment S (`blue-supplementary-S.md`), never merged with step 9.

## Reading order

`blue-protocol.md` → `blue-runbook.md` → `blue-rubric.md` → `acceptance-properties.md` → `isolation-architecture.md` → `evaluation-tools-design.md` → `operator-ledger-template.md` → `independent-review-checklist.md` → `blue-supplementary-S.md`.

## Decisions of the project owner

- Main experiment: A against B, 3 runs each; one pilot of each arm first, excluded from the sample; after the pilots the method is fixed, independently reviewed and frozen before the main runs. **Freeze not authorized.**
- Main CP1 condition: **D**, realized as mediated execution inside a verified isolated environment (an approval of a command is never permission to run unknown code on the host). Condition S is a separate supplementary experiment.
- O-1: the prompt cue about findings that may need no change stays removed from both prompts.
- O-3: isolation between sessions is mandatory; earlier runs' materials and hidden criteria must not be reachable by the next session.
- O-5: the priority environment is Windows Sandbox, if available.
- Fixed parameters: Sonnet 5.5, Medium effort, Manual permission mode (as specified by the owner; not independently confirmed until the gate checks).
- Limits: at most 3 change-list rounds; 90 minutes per run; 30 seconds per separate command; 50 MB of output per execution; the first 200 lines of a command's output returned and logged.
- Findings list F1 to F7: F6 is intentionally **not approved** in this round; F7 is a **false** finding. Neither fact appears in `inputs/findings.md`. The changes to F2, F4 and F7 are accepted provisionally and need independent verification.
- Reading transcripts and canary files outside the repository is **not allowed**. The design keeps it as a possible future audit (see `evaluation-tools-design.md`, section 9).
- Executing code or tests is not allowed until the environment is verified; then only for exact commands approved by the owner.
- Independent review of the test suite and the rubric is mandatory before the main runs.

## Open items

O-4 (who performs the independent review: a model other than the author), the implementation of O-3 (account name, how the operator and the Blue account share the machine, login handling), the availability of Windows Sandbox, and the practical checks listed in `blue-runbook.md` and `isolation-architecture.md`. See `blue-protocol.md`, section 10.

## Glossary

- **Blue-visible**: material the Blue session may read.
- **Hidden**: operator and evaluator material that must never be visible to a Blue session.
- **Property**: an observable security or functional requirement checked on any implementation, not a specific code shape.
- **Invariant**: a property that must hold for every acceptable fix.
- **Mediated execution**: the operator, not the Blue session, runs a command inside the isolated environment after a static gate and returns the output as data.
- **Pilot**: a run used only to debug the method; its results are excluded from the sample.
- **Freeze**: the recorded point after which no protocol, criterion, or tool changes.
- Approved change, side effect, intentional F6 change and scope violation: defined in `blue-rubric.md`, section 3.
