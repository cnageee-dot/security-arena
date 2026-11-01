#!/usr/bin/env python3
"""Compare a blind-run workspace with tests/blind-run-manifest.sha256.

Usage:
  python tests/verify_blind_workspace.py <workspace_dir>             # with-skill arm
  python tests/verify_blind_workspace.py <workspace_dir> --control   # control arm (no skill)

Ignores everything under results/ (the run's own output). Reports modified,
missing and unexpected files. Exit code 0 only if the workspace matches.
In --control mode the manifest entries under .claude/ (the skill) are not
expected, and any file under .claude/ is reported as UNEXPECTED, so the control
workspace is the same as the skill workspace except for the skill.
"""
import hashlib
import sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith("--")]
control = "--control" in sys.argv[1:]
if len(args) != 1:
    sys.exit(__doc__)

manifest = Path(__file__).resolve().parent / "blind-run-manifest.sha256"
root = Path(args[0]).resolve()

expected = {}
for line in manifest.read_text(encoding="utf-8").splitlines():
    digest, _, rel = line.partition(" ")  # sha256sum format: "<hash> *<path>" or "<hash>  <path>"
    rel = rel.strip().lstrip("*").strip().removeprefix("./")
    if not rel or rel.startswith("results/"):
        continue
    if control and rel.startswith(".claude/"):
        continue
    expected[rel] = digest

actual = {}
for f in root.rglob("*"):
    if f.is_file():
        rel = f.relative_to(root).as_posix()
        if not rel.startswith("results/"):
            actual[rel] = hashlib.sha256(f.read_bytes()).hexdigest()

problems = [f"MODIFIED   {p}" for p in expected if p in actual and actual[p] != expected[p]]
problems += [f"MISSING    {p}" for p in expected if p not in actual]
problems += [f"UNEXPECTED {p}" for p in actual if p not in expected]
if problems:
    print("\n".join(sorted(problems)))
    sys.exit(1)
arm = "control arm, no skill" if control else "with skill"
print(f"OK: {len(expected)} files match the manifest ({arm}; results/ ignored)")
