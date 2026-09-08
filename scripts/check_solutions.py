#!/usr/bin/env python3
"""Validate the solutions/ collection against the skills/ tree.

A Solution Skill references existing skills by frontmatter `name` — it never
copies them. This script proves every reference resolves, so a renamed or removed
skill cannot leave a solution pointing at nothing. Mirrors scripts/lint_skills.py
in shape: standard library plus PyYAML, offline, exit 0 when clean, 1 on error.

    python3 scripts/check_solutions.py            # full report, fails on error
    python3 scripts/check_solutions.py --strict   # also print every OK
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("error: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parent.parent
SOLUTIONS = ROOT / "solutions"
SKILLS = ROOT / "skills"


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---", 2)  # ["", frontmatter, body]
    if len(parts) < 3:
        return {}
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        return {"_yaml_error": str(exc)}
    return data if isinstance(data, dict) else {}


def collect_skill_names() -> dict:
    names = {}
    for p in sorted(SKILLS.rglob("SKILL.md")):
        fm = _frontmatter(p)
        nm = str(fm.get("name", "")).strip().strip('"').strip("'")
        if nm:
            names.setdefault(nm, []).append(str(p.relative_to(ROOT)))
    return names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true", help="also print every OK")
    args = ap.parse_args()

    if not SOLUTIONS.is_dir():
        print(f"error: no {SOLUTIONS.relative_to(ROOT)} directory", file=sys.stderr)
        return 2

    skill_names = collect_skill_names()
    errors: list[str] = []
    seen: dict[str, str] = {}
    solutions = sorted(SOLUTIONS.glob("*.md"))

    for sol in solutions:
        rel = sol.relative_to(ROOT)
        fm = _frontmatter(sol)
        if "_yaml_error" in fm:
            errors.append(f"{rel}: frontmatter YAML error: {fm['_yaml_error']}")
            continue
        name = str(fm.get("name", "")).strip().strip('"').strip("'")
        if not name:
            errors.append(f"{rel}: missing frontmatter `name`")
            continue
        if name in seen:
            errors.append(f"{rel}: duplicate solution name `{name}` (also {seen[name]})")
            continue
        seen[name] = str(rel)
        if not str(fm.get("summary", "")).strip():
            errors.append(f"{rel}: missing frontmatter `summary`")
        if not str(fm.get("prompt", "")).strip():
            errors.append(f"{rel}: missing frontmatter `prompt` (the hand-off prompt for another LLM)")
        steps = fm.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{rel}: `steps` must be a non-empty list")
            continue
        step_skills = []
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"{rel}: step {i + 1} is not a mapping")
                continue
            skill = str(step.get("skill", "")).strip().strip('"').strip("'")
            handoff = str(step.get("handoff", "")).strip()
            why = str(step.get("why", "")).strip()
            if not skill:
                errors.append(f"{rel}: step {i + 1} has no `skill`")
                continue
            if not handoff:
                errors.append(f"{rel}: step {i + 1} ({skill}) has no `handoff`")
            if not why:
                errors.append(f"{rel}: step {i + 1} ({skill}) has no `why`")
            step_skills.append(skill)
            if skill not in skill_names:
                errors.append(f"{rel}: step {i + 1} references `{skill}`, which is not "
                              f"a skill in {SKILLS.relative_to(ROOT)}/")
            elif len(skill_names[skill]) > 1:
                errors.append(f"{rel}: step {i + 1} references `{skill}`, which is ambiguous — "
                              f"it matches {len(skill_names[skill])} skills")
        dupes = {s for s in step_skills if step_skills.count(s) > 1}
        for d in sorted(dupes):
            errors.append(f"{rel}: skill `{d}` appears more than once in the steps")
        if args.strict and not any(e.startswith(str(rel)) for e in errors):
            print(f"OK   {rel}: {len(steps)} steps, all resolve")

    if args.strict:
        print(f"\n{len(solutions)} solutions, {len(skill_names)} named skills in the tree")

    if errors:
        print("\n".join(f"error: {e}" for e in errors), file=sys.stderr)
        print(f"\n{len(errors)} error(s)", file=sys.stderr)
        return 1

    print(f"{len(solutions)} solutions OK; every step resolves to a real skill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
