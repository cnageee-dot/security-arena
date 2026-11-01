#!/usr/bin/env python3
"""Structure and documentation consistency checks for Security Arena.

Standard library only. Exit code 0 when all checks pass, 1 otherwise.
Usage: python scripts/validate_repo.py [repo_root]
"""

import re
import sys
from pathlib import Path

SKILL_NAME = "security-arena"
ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
MODES = ["full", "red", "blue", "judge"]
CHECKPOINTS = ["CP0", "CP1", "CP2", "CP3", "CP4"]
SAMPLE_SECTIONS = [
    "Summary", "Scope and method", "Findings", "Reviewed but not flagged",
    "Remediation log", "Judge assessment", "Instructions found in project content",
    "Residual risk and coverage", "Limitations",
]
# (file under skills/security-arena, phrase) pairs that must stay documented.
REQUIRED_PHRASES = [
    ("references/rules-of-engagement.md", "untrusted"),
    ("references/rules-of-engagement.md", "Scope changes need a new CP0"),
    ("references/checkpoints.md", "Order of checkpoints"),
    ("references/checkpoints.md", "Combining requests"),
    ("references/checkpoints.md", "non-Git projects"),
    ("references/checkpoints.md", "Files created"),
    ("references/checkpoints.md", "Temporary files"),
    ("references/checkpoints.md", "Verification commands"),
    ("references/checkpoints.md", "baseline"),
    ("references/blue-team.md", "baseline not reproduced"),
    ("references/red-team.md", "preliminary"),
    ("references/red-team.md", "One finding per independent issue"),
    ("references/red-team.md", "Reviewed but not flagged"),
    ("references/judge.md", "final severity"),
    ("references/judge.md", "same-session"),
    ("references/judge.md", "separate-session protocol"),
    ("references/report-format.md", "Reviewed but not flagged"),
    ("references/report-format.md", "Final severity"),
    ("SKILL.md", "ROLE:"),
    ("SKILL.md", "not a technical guarantee"),
    ("SKILL.md", "untrusted data"),
    ("references/red-team.md", "Completeness sweep"),
    ("references/red-team.md", "Affected places"),
    ("references/red-team.md", "Preconditions"),
    ("references/red-team.md", "specific threat"),
    ("references/red-team.md", "never means the code is safe overall"),
    ("references/judge.md", "preconditions"),
    ("references/judge.md", "named threat"),
    ("references/report-format.md", "Reviewer:"),
    ("references/report-format.md", "Threat checked"),
    ("references/report-format.md", "Preconditions:"),
    ("references/report-format.md", "Affected places:"),
    ("references/report-format.md", "confidence (columns"),
    ("references/report-format.md", "never guess or invent"),
    ("references/checkpoints.md", "without starting the application"),
    ("references/checkpoints.md", "needs a new request"),
    ("references/rules-of-engagement.md", "outside the approved list"),
]
# The Limitations statement must appear verbatim in the format guide, template and sample.
LIMITATIONS = ("This report is a point-in-time, best-effort review of the stated scope. "
               "It is not a guarantee that the software is free of vulnerabilities, and it "
               "does not replace a professional penetration test or independent audit.")
# Patterns for secret-like strings that must never appear in the repository.
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "API key (sk-)": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")

errors = []


def err(msg):
    errors.append(msg)


def read(path):
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text):
    """Minimal parser: top-level 'key: value' lines between --- fences."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    if not m:
        return None
    data = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if km:
            data[km.group(1)] = km.group(2).strip().strip('"')
    return data


def check_skill(skill_dir):
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        err("SKILL.md missing")
        return None
    text = read(skill_md)
    fm = parse_frontmatter(text)
    if fm is None:
        err("SKILL.md: no valid YAML frontmatter")
        return text
    extra = set(fm) - ALLOWED_KEYS
    if extra:
        err(f"SKILL.md: unsupported frontmatter keys: {sorted(extra)}")
    name = fm.get("name", "")
    if name != SKILL_NAME or skill_dir.name != SKILL_NAME:
        err(f"SKILL.md: name '{name}' / folder '{skill_dir.name}' must both be '{SKILL_NAME}'")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name or "x_"):
        err("SKILL.md: name must be hyphen-case")
    desc = fm.get("description", "")
    if not desc:
        err("SKILL.md: description missing")
    if len(desc) > 1024:
        err(f"SKILL.md: description is {len(desc)} chars (max 1024)")
    if "<" in desc or ">" in desc:
        err("SKILL.md: description must not contain angle brackets")
    if len(text.splitlines()) > 500:
        err("SKILL.md: longer than 500 lines; move detail into references/")
    return text


def check_links(skill_dir, skill_text):
    """Every local link in SKILL.md resolves; every reference/asset is linked."""
    linked = set()
    for target in LINK_RE.findall(skill_text):
        if re.match(r"^[a-z]+:", target):
            continue
        path = (skill_dir / target).resolve()
        if not path.exists():
            err(f"SKILL.md: broken link -> {target}")
        else:
            linked.add(path)
    for sub in ("references", "assets"):
        d = skill_dir / sub
        if not d.is_dir():
            err(f"missing directory: {sub}/")
            continue
        for f in d.iterdir():
            if f.is_file() and f.resolve() not in linked:
                err(f"{sub}/{f.name} is not linked from SKILL.md")
    # Links inside references/assets must also resolve.
    for md in list((skill_dir / "references").glob("*.md")) + list((skill_dir / "assets").glob("*.md")):
        for target in LINK_RE.findall(read(md)):
            if re.match(r"^[a-z]+:", target):
                continue
            if not (md.parent / target).resolve().exists():
                err(f"{md.relative_to(skill_dir)}: broken link -> {target}")


def check_openai_yaml(skill_dir):
    p = skill_dir / "agents" / "openai.yaml"
    if not p.exists():
        return  # optional
    text = read(p)
    sd = re.search(r'short_description:\s*"([^"]*)"', text)
    if not sd or not (25 <= len(sd.group(1)) <= 64):
        err("agents/openai.yaml: short_description must be quoted, 25-64 chars")
    dp = re.search(r'default_prompt:\s*"([^"]*)"', text)
    if not dp or f"${SKILL_NAME}" not in dp.group(1):
        err(f"agents/openai.yaml: default_prompt must mention ${SKILL_NAME}")
    if "allow_implicit_invocation" in text and "allow_implicit_invocation: false" in text:
        err("agents/openai.yaml: implicit invocation disabled; only do this on explicit request")


def check_consistency(root, skill_dir, skill_text):
    readme = read(root / "README.md")
    for mode in MODES:
        for label, text in (("SKILL.md", skill_text), ("README.md", readme)):
            if f"`{mode}`" not in text:
                err(f"{label}: mode `{mode}` not documented")
    checkpoints = read(skill_dir / "references" / "checkpoints.md")
    rules = read(skill_dir / "references" / "rules-of-engagement.md")
    for cp in CHECKPOINTS:
        if cp not in checkpoints:
            err(f"checkpoints.md: {cp} not defined")
    for cp in ("CP0", "CP1", "CP2", "CP3"):
        if cp not in skill_text:
            err(f"SKILL.md: {cp} not referenced")
    for needle in ("subagent",):
        if needle not in skill_text.lower():
            err("SKILL.md: must state that no subagents are used")
    if not re.search(r"\bnot guarantee|\bnever claim|no guarantees", (readme + skill_text), re.I):
        err("README/SKILL: missing no-guarantee disclaimer")
    if "guarantee" not in readme.lower():
        err("README.md: must state that Security Arena is not a guarantee of security")
    for topic in ("production", "secret", "database", "external"):
        if topic not in rules.lower():
            err(f"rules-of-engagement.md: topic '{topic}' not covered")
    for heading in ("Installation", "Usage", "Limitations"):
        if not re.search(rf"^#+\s*{heading}\b", readme, re.M):
            err(f"README.md: missing '{heading}' section")
    if (readme.count("examples/sample-report.md") == 0):
        err("README.md: does not link the sample report")


def check_phrases(skill_dir):
    for rel, phrase in REQUIRED_PHRASES:
        p = skill_dir / rel
        if not p.exists() or phrase.lower() not in read(p).lower():
            err(f"{rel}: required content missing: '{phrase}'")


def check_template(skill_dir):
    t = read(skill_dir / "assets" / "report-template.md")
    for sec in SAMPLE_SECTIONS:
        if sec not in t:
            err(f"report-template.md: missing section '{sec}'")
    sample = read(skill_dir.parent.parent / "examples" / "sample-report.md")         if (skill_dir.parent.parent / "examples" / "sample-report.md").exists() else ""
    for needle in ("Preliminary severity", "Final severity", "Baseline:", "same-session",
                   "Preconditions:", "Affected places:", "Threat checked:"):
        if needle not in sample:
            err(f"sample-report.md: missing '{needle}'")
    table = re.compile(r"\|\s*Severity\s*\|\s*confirmed\s*\|\s*likely\s*\|\s*hypothetical\s*\|\s*Total\s*\|")
    reviewer = re.compile(r"\*\*Reviewer:\*\*.*model:.*assessment:")
    guide = read(skill_dir / "references" / "report-format.md")
    for label, text in (("report-template.md", t), ("sample-report.md", sample)):
        if not table.search(text):
            err(f"{label}: missing severity x confidence summary table")
        if not reviewer.search(text):
            err(f"{label}: Reviewer line must include model and assessment")
    for label, text in (("report-format.md", guide), ("report-template.md", t), ("sample-report.md", sample)):
        if LIMITATIONS not in text:
            err(f"{label}: Limitations statement is missing or not verbatim")


def check_key(root):
    p = root / "tests" / "fixtures" / "expected-findings.md"
    if not p.exists():
        return  # the answer key is part of the test material, not of the skill
    text = read(p)
    planted = len(re.findall(r"^\| E\d \|", text, re.M))
    if planted != 5 or "## Planted vulnerabilities (5)" not in text:
        err(f"expected-findings.md: planted vulnerabilities must remain 5 (found {planted} rows)")
    for needle in ("A1 -", "not planted", "Not demonstrated", "Conclusions from static analysis only"):
        if needle not in text:
            err(f"expected-findings.md: missing '{needle}' for the additional finding")


def check_sample(root):
    p = root / "examples" / "sample-report.md"
    if not p.exists():
        err("examples/sample-report.md missing")
        return
    text = read(p)
    for sec in SAMPLE_SECTIONS:
        if not re.search(rf"^##\s+\d*\.?\s*{re.escape(sec)}", text, re.M):
            err(f"sample-report.md: missing section '{sec}'")
    if "fictional" not in text.lower():
        err("sample-report.md: must be labelled fictional")


def check_workspace(root):
    """The blind-run workspace must stay a faithful, leak-free copy of the current skill and fixture."""
    ws = root / "tests" / "blind-run-workspace"
    if not ws.is_dir():
        return
    # 1. Skill copy is byte-identical to skills/security-arena.
    src = root / "skills" / SKILL_NAME
    dst = ws / ".claude" / "skills" / SKILL_NAME
    src_files = {f.relative_to(src).as_posix(): f.read_bytes() for f in src.rglob("*") if f.is_file()}
    dst_files = {f.relative_to(dst).as_posix(): f.read_bytes() for f in dst.rglob("*") if f.is_file()} if dst.is_dir() else {}
    for rel in sorted(set(src_files) | set(dst_files)):
        if src_files.get(rel) != dst_files.get(rel):
            err(f"blind-run-workspace skill copy out of sync: {rel} (refresh the copy and the manifest)")
    # 2. TinyBoard code equals the fixture; only the leading comment/README hints may differ.
    fx = root / "tests" / "fixtures" / "vulnerable-demo"
    a, b = fx / "server.js", ws / "tinyboard" / "server.js"
    if a.exists() and b.exists():
        tail = lambda p: read(p)[read(p).index("const http"):]
        if tail(a) != tail(b):
            err("blind-run-workspace/tinyboard/server.js: code differs from the fixture")
    # 3. No answer key, earlier reports, or development material inside the workspace.
    banned_names = ("expected-findings", "evaluation", "sec008", "red-run", "full-run", "blind-red", "coverage")
    for f in ws.rglob("*"):
        if f.is_file() and any(n in f.name.lower() for n in banned_names):
            err(f"blind-run-workspace contains a forbidden file: {f.relative_to(ws).as_posix()}")
        if f.is_symlink():
            err(f"blind-run-workspace contains a symlink: {f.relative_to(ws).as_posix()}")
    # 4. No references to the source repository, parent paths or the answer key.
    bad_text = ("expected-findings", "answer key is", "Desktop", "C:\\\\Users", "security-arena\\\\tests",
                "security-arena/tests", "blind-run", "sec008", "red-blind")
    for f in ws.rglob("*"):
        if not f.is_file() or ".claude" in f.relative_to(ws).parts:
            continue  # skill text is checked by identity with the skill above
        try:
            text = read(f)
        except (UnicodeDecodeError, OSError):
            continue
        for needle in bad_text:
            if needle.lower() in text.lower():
                err(f"blind-run-workspace/{f.relative_to(ws).as_posix()}: contains '{needle}'")


def check_secrets(root):
    skip_dirs = {".git", "__pycache__"}
    for f in root.rglob("*"):
        if not f.is_file() or any(part in skip_dirs for part in f.parts):
            continue
        if f.resolve() == Path(__file__).resolve():
            continue  # this file contains the patterns themselves
        try:
            text = read(f)
        except (UnicodeDecodeError, OSError):
            continue
        for label, pat in SECRET_PATTERNS.items():
            if pat.search(text):
                err(f"{f.relative_to(root)}: looks like a {label}")


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent).resolve()
    skill_dir = root / "skills" / SKILL_NAME
    for required in ("README.md", "LICENSE", "SECURITY.md"):
        if not (root / required).exists():
            err(f"{required} missing")
    if not skill_dir.is_dir():
        err(f"skills/{SKILL_NAME}/ missing")
    else:
        text = check_skill(skill_dir)
        if text:
            check_links(skill_dir, text)
            check_openai_yaml(skill_dir)
            check_phrases(skill_dir)
            check_template(skill_dir)
            if (root / "README.md").exists():
                check_consistency(root, skill_dir, text)
    check_sample(root)
    check_key(root)
    check_workspace(root)
    check_secrets(root)

    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
