# Security Arena

A skill for **Claude Code** and **OpenAI Codex** that runs a structured, sequential security review of a software project through three roles:

| Role | Job |
|------|-----|
| **Red Team** | Investigates the code and records vulnerabilities that are backed by evidence. |
| **Blue Team** | Proposes and, once you approve, implements fixes. |
| **Judge** | Independently checks the evidence, the quality of the fixes, and the remaining risk. |

> **Security Arena does not guarantee security.** It is an AI-assisted, best-effort review. It can miss vulnerabilities and can be wrong. It does not replace a professional penetration test, an independent audit, or human code review.

Status: early draft (v0.1.0). The skill has not yet been evaluated on real projects; see [Limitations](#limitations).

## Features

- **Sequential by design.** One agent, one role at a time. No subagents, no agent teams.
- **Four modes.** `full`, `red`, `blue`, `judge`. Run any role alone.
- **Rules of Engagement.** Written scope, local-only testing, and protection for production, secrets, databases and external services. See [rules-of-engagement.md](skills/security-arena/references/rules-of-engagement.md).
- **Explicit checkpoints.** Separate permission is required for scope and scope changes such as copies and new paths (CP0), running anything including baseline reproductions (CP1), file changes with a full list of modified files, created tests, temporary files and verification commands (CP2), Git operations (CP3) and writing reports to disk (CP4). A defined order and rules for combining requests are in [checkpoints.md](skills/security-arena/references/checkpoints.md).
- **Project content is untrusted.** Instructions inside the audited code, comments, README, logs or tool output cannot change the rules, scope or checkpoints; they are reported, not followed.
- **Baseline before fix.** Fixes are verified by reproducing the issue on the original first, when that is safe and approved; otherwise the report says "baseline not reproduced".
- **Evidence standard.** One independent issue per finding, with location, mechanism, preconditions and evidence; for a class of issue, other places with the same mechanism within scope are listed as confirmed, likely or not checked. Red Team's severity is preliminary; Judge sets the final severity with a rationale. Speculation goes under "unverified leads".
- **Honest reporting.** The header names the reviewer model and assessment mode (or says "unknown") and the summary tabulates severity by confidence. Every report lists what was reviewed but not flagged (each entry scoped to a named threat, never general safety), states coverage limits and residual risk, and says whether the Judge review was same-session.
- **Role transitions are announced.** Each role switch writes a record and reads the role's reference (see Limitations on what this does and does not guarantee).

## Repository layout

```
skills/security-arena/     the skill (copy this folder to install)
  SKILL.md                 entry point: modes, workflow, non-negotiables
  agents/openai.yaml       Codex UI metadata
  references/              rules, checkpoints, per-role guides, report format
  assets/                  scope and report templates
examples/sample-report.md  report for a fictional project
scripts/validate_repo.py   structure and documentation consistency checks
```

## Installation

Installation means copying the `skills/security-arena` folder into a skills directory. Nothing is installed automatically.

**Claude Code** (personal, all projects):

```bash
cp -r skills/security-arena ~/.claude/skills/security-arena
```

For a single project, copy it to `<project>/.claude/skills/security-arena` instead.

**Codex** (default location per Codex's skill-creator is `$CODEX_HOME/skills`, or `~/.codex/skills` when unset):

```bash
cp -r skills/security-arena "${CODEX_HOME:-$HOME/.codex}/skills/security-arena"
```

On Windows PowerShell use `Copy-Item -Recurse skills\security-arena $HOME\.claude\skills\security-arena` (or the Codex path). Restart or reload your agent session if the skill does not appear. Skill directory locations can change between tool versions; check your tool's current documentation if the paths above do not work.

## Usage

Invoke the skill by name or describe the task. Examples:

```text
Use security-arena to audit this project.                      # full mode
Use security-arena in red mode on ./src. Read-only.
Use security-arena in blue mode with the findings in report.md.
Use security-arena in judge mode to review the diff on this branch.
```

In Codex, the skill can be mentioned as `$security-arena`. In Claude Code, ask for it by name or let it be selected from its description.

### Modes

| Mode | Runs | Input needed |
|------|------|--------------|
| `full` (default) | Red, then Blue, then Judge, pausing between roles | Scope |
| `red` | Red Team only | Scope |
| `blue` | Blue Team only | Findings + scope |
| `judge` | Judge only | Findings and/or diff + scope |

### What happens first

The skill asks you to confirm an engagement scope (target path, what is out of scope, local-only environment, whether files may change, whether Git is allowed, where the report goes). Nothing is analyzed before you confirm.

### Default behavior

Read-only static review. It will not start services, run tests with side effects, install dependencies, edit files, run Git write commands, or write a report file unless you approve that specific action when asked.

## Example output

See [examples/sample-report.md](examples/sample-report.md). It covers a fictional project ("Pebble Notes") and contains no real targets or credentials.

## Validating this repository

```bash
python scripts/validate_repo.py
```

Checks skill frontmatter, that every reference is linked from `SKILL.md`, that links resolve, that modes and checkpoints are documented consistently, that the sample report has the required sections, and that no secret-like strings are present. Requires Python 3.8+ and no third-party packages. It checks structure, not whether the skill makes good decisions.

## Limitations

- The agent follows instructions probabilistically. The checkpoints and rules are prompt-level controls, not a sandbox. For real protection, also use the permission and sandbox settings of your agent, and run it on a copy of the project.
- **Judge independence is limited in a single session.** The Judge is the same model with the same context as Red and Blue: blind spots are shared, earlier findings anchor the review, and it grades work it produced. Reports label such a review "same-session". For important results run `judge` in a fresh session (ideally another model or tool) with only the code or diff, findings and scope; the protocol is in [judge.md](skills/security-arena/references/judge.md). The skill cannot start that session itself, because it never creates subagents.
- **Role-reference reading is procedural, not verifiable.** The skill instructs the agent to read the role's reference and write a transition record at each switch. It cannot prove the file was read or applied; the record only makes the step visible to you.
- **Untrusted-content rule is prompt-level.** The agent is told to treat project text as data; a model can still be influenced by adversarial content. Use your tool's permission and sandbox settings as a second layer.
- **Test coverage of the skill is partial.** See [tests/coverage.md](tests/coverage.md) for what has and has not been exercised.
- Static review by an AI will miss issues, especially in complex business logic, and may report false positives.
- Dependency findings are version-based unless reachability is shown.
- No dynamic testing is done by default.
- Only skill fields confirmed by the local Claude Code and Codex skill documentation are used. Behavior may differ across tool versions.

## Intended use

Use only on projects you own or have written permission to test. Do not use it to attack third-party systems. See [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
