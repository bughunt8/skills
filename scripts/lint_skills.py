#!/usr/bin/env python3
"""Validate every SKILL.md in this repository.

A skills library is a data set, not an application. Its correctness lives in
metadata, so metadata gets a test. Standard library only.

    scripts/lint_skills.py                    # lint, honouring the baseline
    scripts/lint_skills.py --output json
    scripts/lint_skills.py --strict           # ignore the baseline, show every finding
    scripts/lint_skills.py --write-baseline   # record current violations as accepted

Rules
    SK001  SKILL.md has a YAML frontmatter block
    SK002  frontmatter declares a non-empty `name`
    SK003  frontmatter declares a non-empty `description`
    SK004  `name` matches its directory name, so /name invocation is predictable
    SK005  `name` is lowercase kebab-case, 1-64 chars
    SK006  `description` is at most 1024 characters
    SK007  `name` is unique across the repository
    SK008  a directory under a vendored root carries a PROVENANCE.md

Vendored directories listed in skills/vendor.manifest.json are reported as
warnings, never errors: their content belongs upstream and cannot be corrected
here. SK008 is the exception, because this repository owns provenance.

Exit codes
    0  no unbaselined errors
    1  errors found
    2  usage or environment error
"""

from __future__ import annotations

import argparse
import collections
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
MANIFEST_PATH = SKILLS_ROOT / "vendor.manifest.json"
BASELINE_PATH = REPO_ROOT / "scripts" / "skill_lint_baseline.json"

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$")
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):[ \t]*(.*)$")

MAX_DESCRIPTION = 1024


def vendor_roots() -> list:
    if not MANIFEST_PATH.exists():
        return []
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: {MANIFEST_PATH} is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(2)
    return [s["dest"].strip("/") for s in data.get("sources", []) if s.get("dest")]


def parse_frontmatter(text: str) -> "dict | None":
    """Extract top-level scalar keys. Deliberately not a YAML parser.

    Only the keys this linter judges are needed, and depending on PyYAML would
    make the check unrunnable without installing anything.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    fields = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if line[:1] in " \t-":  # nested mapping or sequence item
            continue
        key_match = KEY_RE.match(line)
        if key_match:
            key, value = key_match.group(1), key_match.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[key] = value
    return fields


def ignore_globs() -> list:
    """Paths that look like skills but are not, such as test fixtures."""
    if not BASELINE_PATH.exists():
        return []
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8")).get("ignore_globs", [])


def discover(ignores: "list | None" = None) -> list:
    ignores = ignores if ignores is not None else ignore_globs()
    found = []
    for dirpath, dirnames, filenames in os.walk(SKILLS_ROOT):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if "SKILL.md" not in filenames:
            continue
        path = Path(dirpath) / "SKILL.md"
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(fnmatch.fnmatch(rel, pat) for pat in ignores):
            continue
        found.append(path)
    return sorted(found)


def lint() -> list:
    roots = vendor_roots()
    findings = []
    by_name = collections.defaultdict(list)

    for path in discover():
        rel = path.relative_to(REPO_ROOT).as_posix()
        skill_dir = path.parent
        rel_dir = skill_dir.relative_to(REPO_ROOT).as_posix()
        vendored = any(rel_dir == r or rel_dir.startswith(r + "/") for r in roots)
        sev = "warning" if vendored else "error"

        def add(rule: str, message: str, severity: "str | None" = None) -> None:
            findings.append(
                {
                    "rule": rule,
                    "severity": severity or sev,
                    "path": rel,
                    "vendored": vendored,
                    "message": message,
                }
            )

        if vendored and rel_dir.count("/") == len(rel_dir.strip("/").split("/")) - 1:
            pass  # provenance is checked below for the whole vendored dir

        text = path.read_text(encoding="utf-8", errors="replace")
        fields = parse_frontmatter(text)
        if fields is None:
            add("SK001", "no YAML frontmatter block")
            continue

        name = fields.get("name", "").strip()
        description = fields.get("description", "").strip()

        if not name:
            add("SK002", "frontmatter has no `name`")
        if not description:
            add("SK003", "frontmatter has no `description`")

        if name:
            by_name[name].append(rel)
            if name != skill_dir.name:
                add("SK004", f"`name: {name}` does not match directory `{skill_dir.name}`")
            if not NAME_RE.match(name):
                add("SK005", f"`name: {name}` is not lowercase kebab-case")
        if description and len(description) > MAX_DESCRIPTION:
            add("SK006", f"description is {len(description)} chars, limit is {MAX_DESCRIPTION}")

        if vendored and not (skill_dir / "PROVENANCE.md").exists():
            # Nested helper dirs inside a vendored skill are fine; only the skill
            # directory directly under a vendored root must carry provenance.
            for root in roots:
                if rel_dir.startswith(root + "/") and rel_dir[len(root) + 1 :].count("/") == 0:
                    add(
                        "SK008",
                        "vendored skill has no PROVENANCE.md; run scripts/sync_vendor.py --sync",
                        severity="error",
                    )

    for name, paths in sorted(by_name.items()):
        if len(paths) > 1:
            vend = all(any(p.startswith(r + "/") for r in roots) for p in paths)
            for p in sorted(paths):
                findings.append(
                    {
                        "rule": "SK007",
                        "severity": "warning" if vend else "error",
                        "path": p,
                        "vendored": vend,
                        "message": f"duplicate skill name `{name}` also at "
                        + ", ".join(q for q in sorted(paths) if q != p),
                    }
                )

    return sorted(findings, key=lambda f: (f["rule"], f["path"]))


def key(f: dict) -> str:
    return f"{f['rule']}::{f['path']}"


def load_baseline() -> dict:
    if not BASELINE_PATH.exists():
        return {"accepted": []}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="Validate every SKILL.md in this repository.")
    ap.add_argument("--output", choices=("text", "json"), default="text")
    ap.add_argument("--strict", action="store_true", help="ignore the baseline")
    ap.add_argument("--write-baseline", action="store_true", help="accept current violations")
    args = ap.parse_args(argv)

    if not SKILLS_ROOT.is_dir():
        print(f"error: no skills/ directory at {SKILLS_ROOT}", file=sys.stderr)
        return 2

    findings = lint()
    total_skills = len(discover())

    if args.write_baseline:
        accepted = sorted({key(f) for f in findings if f["severity"] == "error"})
        BASELINE_PATH.write_text(
            json.dumps(
                {
                    "$comment": (
                        "Pre-existing SKILL.md violations accepted so CI blocks new ones while the "
                        "backlog is worked down. Entries are RULE::path. Remove an entry once the "
                        "underlying skill is fixed; scripts/lint_skills.py --strict shows everything."
                    ),
                    "ignore_globs": ignore_globs(),
                    "accepted": accepted,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {BASELINE_PATH.relative_to(REPO_ROOT)} with {len(accepted)} accepted finding(s)")
        return 0

    baseline = set() if args.strict else set(load_baseline().get("accepted", []))
    errors = [f for f in findings if f["severity"] == "error" and key(f) not in baseline]
    warnings = [f for f in findings if f["severity"] == "warning"]
    suppressed = [f for f in findings if f["severity"] == "error" and key(f) in baseline]

    if args.output == "json":
        print(
            json.dumps(
                {
                    "skills_checked": total_skills,
                    "errors": errors,
                    "warnings": warnings,
                    "suppressed_by_baseline": len(suppressed),
                },
                indent=2,
            )
        )
    else:
        for f in errors:
            print(f"error  {f['rule']}  {f['path']}: {f['message']}")
        for f in warnings:
            print(f"warn   {f['rule']}  {f['path']}: {f['message']}")
        print()
        print(
            f"{total_skills} skill(s) checked. "
            f"{len(errors)} error(s), {len(warnings)} warning(s) in vendored trees, "
            f"{len(suppressed)} accepted by baseline."
        )

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
