#!/usr/bin/env python3
"""Validate every SKILL.md in this repository.

A skills library is a data set, not an application. Its correctness lives in
metadata, so metadata gets a test.

    scripts/lint_skills.py                    # lint, honouring the baseline
    scripts/lint_skills.py --output json
    scripts/lint_skills.py --strict           # ignore the baseline, show every finding
    scripts/lint_skills.py --write-baseline   # record current violations as accepted
    scripts/lint_skills.py --self-test        # prove the parser rejects what it cannot handle

Rules
    SK001  SKILL.md has a YAML frontmatter block
    SK002  frontmatter declares a non-empty `name`
    SK003  frontmatter declares a non-empty `description`
    SK004  `name` matches its directory name, so /name invocation is predictable
    SK005  `name` is lowercase kebab-case, 1-64 chars
    SK006  `description` is at most 1024 characters
    SK007  `name` is unique across the repository
    SK008  a skill directory under a vendored root carries a PROVENANCE.md
    SK009  frontmatter uses YAML this linter cannot read without guessing

## About SK009, and why the parser is not clever

The first version of this file said "deliberately not a YAML parser" and used a
line regex. An independent review showed what that costs. `description: |`
followed by an indented block parsed as the one-character string `|`, so SK006
could be bypassed by any block scalar, and `description: [unterminated` parsed as
valid. The linter reported success on frontmatter that no YAML loader would
accept.

PyYAML is used when it is importable, which is the correct answer. When it is not,
the fallback reads only the flat `key: value` subset and raises SK009 on anything
outside it, block scalars and flow collections included. It fails loudly instead
of guessing. A checker that silently passes what it cannot understand is worse
than no checker, because it produces confidence.

Exit codes
    0  no unbaselined errors
    1  errors found
    2  usage or environment error
"""

from __future__ import annotations

import argparse
import collections
import fnmatch
import hashlib
import json
import os
import re
import sys
from pathlib import Path

try:  # pragma: no cover - environment dependent
    import yaml  # type: ignore

    HAVE_YAML = True
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore
    HAVE_YAML = False

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
MANIFEST_PATH = SKILLS_ROOT / "vendor.manifest.json"
BASELINE_PATH = REPO_ROOT / "scripts" / "skill_lint_baseline.json"

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$")
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
KEY_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.\-]+):(?P<rest>.*)$")

MAX_DESCRIPTION = 1024


class UnsupportedFrontmatter(Exception):
    """The fallback parser refuses to guess at this construct."""


def vendor_roots() -> list:
    if not MANIFEST_PATH.exists():
        return []
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: {MANIFEST_PATH} is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(2)
    return [s["dest"].strip("/") for s in data.get("sources", []) if s.get("dest")]


def _fallback_parse(block: str) -> dict:
    """Flat `key: value` only. Anything else raises rather than guesses."""
    fields = {}
    lines = block.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] in " \t":
            continue  # part of a nested mapping already accounted for below
        if line.lstrip().startswith("- "):
            raise UnsupportedFrontmatter("top-level sequence item")
        match = KEY_RE.match(line)
        if not match:
            raise UnsupportedFrontmatter(f"cannot parse line: {line.strip()[:60]!r}")
        key = match.group("key")
        value = match.group("rest").strip()
        if value in ("|", ">", "|-", ">-", "|+", ">+") or re.match(r"^[|>][0-9+-]*$", value):
            raise UnsupportedFrontmatter(f"block scalar on `{key}`")
        if value == "":
            fields[key] = ""  # nested mapping or empty; nested content is skipped above
            continue
        if value[0] in "[{":
            opener, closer = ("[", "]") if value[0] == "[" else ("{", "}")
            if value.count(opener) != value.count(closer):
                raise UnsupportedFrontmatter(f"unterminated flow collection on `{key}`")
            fields[key] = value
            continue
        if value[0] in "\"'":
            quote = value[0]
            if len(value) < 2 or value[-1] != quote or value.count(quote) % 2 != 0:
                raise UnsupportedFrontmatter(f"unterminated quoted scalar on `{key}`")
            value = value[1:-1]
        fields[key] = value
    return fields


def parse_frontmatter(text: str) -> "dict | None":
    """Return the frontmatter mapping, or None when there is no block.

    Raises UnsupportedFrontmatter when the document cannot be read reliably.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    block = match.group(1)
    if HAVE_YAML:
        try:
            loaded = yaml.safe_load(block)
        except yaml.YAMLError as exc:  # type: ignore[union-attr]
            raise UnsupportedFrontmatter(f"invalid YAML: {str(exc).splitlines()[0][:80]}")
        if loaded is None:
            return {}
        if not isinstance(loaded, dict):
            raise UnsupportedFrontmatter("frontmatter is not a mapping")
        return {str(k): ("" if v is None else v) for k, v in loaded.items()}
    return _fallback_parse(block)


def _scalar(value) -> str:
    return value if isinstance(value, str) else ("" if value is None else str(value))


def ignore_globs() -> list:
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
        default_severity = "warning" if vendored else "error"

        def add(rule: str, message: str, severity: "str | None" = None) -> None:
            findings.append(
                {
                    "rule": rule,
                    "severity": severity or default_severity,
                    "path": rel,
                    "vendored": vendored,
                    "message": message,
                }
            )

        if vendored and not (skill_dir / "PROVENANCE.md").exists():
            for root in roots:
                if rel_dir.startswith(root + "/"):
                    add(
                        "SK008",
                        "vendored skill has no PROVENANCE.md; run scripts/sync_vendor.py --sync",
                        severity="error",
                    )
                    break

        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            fields = parse_frontmatter(text)
        except UnsupportedFrontmatter as exc:
            add("SK009", f"frontmatter cannot be read reliably: {exc}")
            continue
        if fields is None:
            add("SK001", "no YAML frontmatter block")
            continue

        name = _scalar(fields.get("name", "")).strip()
        description = _scalar(fields.get("description", "")).strip()

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

    for name, paths in sorted(by_name.items()):
        if len(paths) > 1:
            all_vendored = all(any(p.startswith(r + "/") for r in roots) for p in paths)
            for p in sorted(paths):
                findings.append(
                    {
                        "rule": "SK007",
                        "severity": "warning" if all_vendored else "error",
                        "path": p,
                        "vendored": all_vendored,
                        "message": f"duplicate skill name `{name}` also at "
                        + ", ".join(q for q in sorted(paths) if q != p),
                    }
                )

    return sorted(findings, key=lambda f: (f["rule"], f["path"]))


def key(finding: dict) -> str:
    """Suppression identity: rule, path, and a fingerprint of the message.

    Rule plus path alone let a baselined entry launder an unrelated new violation
    of the same rule at the same path. Including the message means replacing a
    skill with different broken metadata produces a different key and fails.
    """
    digest = hashlib.sha256(finding["message"].encode("utf-8")).hexdigest()[:12]
    return f"{finding['rule']}::{finding['path']}::{digest}"


def load_baseline() -> dict:
    if not BASELINE_PATH.exists():
        return {"accepted": []}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def self_test() -> int:
    """Prove the parser either reads a construct correctly or refuses it.

    The two parsers have different, both-acceptable answers for block scalars.
    PyYAML reads them, which is correct. The fallback refuses them, which is also
    correct, because the alternative is the silent mis-parse this rule exists to
    prevent. What is never acceptable is reading `description: |` as the string
    "|" and reporting success, which is what the original line regex did.
    """
    block = "ok" if HAVE_YAML else "reject"
    cases = [
        ("plain", "---\nname: a\ndescription: hello\n---\n", "ok"),
        ("quoted", '---\nname: a\ndescription: "hello: there"\n---\n', "ok"),
        ("nested map", "---\nname: a\ndescription: d\nmetadata:\n  version: 1\n---\n", "ok"),
        ("block scalar", "---\nname: a\ndescription: |\n  long text here\n---\n", block),
        ("folded scalar", "---\nname: a\ndescription: >\n  long text here\n---\n", block),
        ("unterminated flow", "---\nname: a\ndescription: [unterminated\n---\n", "reject"),
        ("not a mapping", "---\n- just\n- a list\n---\n", "reject"),
        ("no frontmatter", "# just a heading\n", "none"),
    ]
    failures = 0
    for label, text, expect in cases:
        try:
            result = parse_frontmatter(text)
            got = "none" if result is None else "ok"
        except UnsupportedFrontmatter as exc:
            got = "reject"
            detail = str(exc)
        else:
            detail = repr(result)
        status = "PASS" if got == expect else "FAIL"
        if status == "FAIL":
            failures += 1
        print(f"{status}  {label:20} expected={expect:6} got={got:6} {detail[:70]}")

    # The specific regression that started this: a block scalar must never be
    # read as the literal marker character.
    try:
        parsed = parse_frontmatter("---\nname: a\ndescription: |\n  " + "x" * 1100 + "\n---\n")
    except UnsupportedFrontmatter:
        regression = "PASS"
        note = "refused, so SK009 fires instead of a false pass"
    else:
        got_desc = _scalar(parsed.get("description", ""))
        if got_desc.strip() in ("|", ">"):
            regression = "FAIL"
            note = "block scalar read as its marker character, SK006 is bypassable"
        else:
            regression = "PASS"
            note = f"read {len(got_desc)} chars, so SK006 can see it"
    if regression == "FAIL":
        failures += 1
    print(f"{regression}  {'oversize block scalar':20} {note}")

    print()
    print(f"parser: {'PyYAML' if HAVE_YAML else 'strict stdlib fallback'}")
    print(f"{len(cases) + 1} case(s), {failures} failure(s)")
    return 1 if failures else 0


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="Validate every SKILL.md in this repository.")
    ap.add_argument("--output", choices=("text", "json"), default="text")
    ap.add_argument("--strict", action="store_true", help="ignore the baseline")
    ap.add_argument("--write-baseline", action="store_true", help="accept current violations")
    ap.add_argument("--self-test", action="store_true", help="test the frontmatter parser")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

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
                        "backlog is worked down. Entries are RULE::path::sha256(message)[:12]; the "
                        "message fingerprint stops a baselined entry from laundering an unrelated "
                        "new violation of the same rule at the same path. Remove an entry once the "
                        "skill is fixed. scripts/lint_skills.py --strict shows everything."
                    ),
                    "ignore_globs": ignore_globs(),
                    "accepted": accepted,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            f"wrote {BASELINE_PATH.relative_to(REPO_ROOT)} with {len(accepted)} accepted finding(s)"
        )
        return 0

    baseline = set() if args.strict else set(load_baseline().get("accepted", []))
    errors = [f for f in findings if f["severity"] == "error" and key(f) not in baseline]
    warnings = [f for f in findings if f["severity"] == "warning"]
    suppressed = [f for f in findings if f["severity"] == "error" and key(f) in baseline]

    if args.output == "json":
        print(
            json.dumps(
                {
                    "parser": "PyYAML" if HAVE_YAML else "stdlib-fallback",
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
            f"{total_skills} skill(s) checked with "
            f"{'PyYAML' if HAVE_YAML else 'the strict stdlib fallback parser'}. "
            f"{len(errors)} error(s), {len(warnings)} warning(s) in vendored trees, "
            f"{len(suppressed)} accepted by baseline."
        )

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
