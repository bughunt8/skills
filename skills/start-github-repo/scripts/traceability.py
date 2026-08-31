#!/usr/bin/env python3
"""Rebuild and audit the requirement traceability matrix.

Standard library only. Deterministic. Reads the repository; never writes to it unless --write is
given, and then only to a file you name.

What it does
------------
Scans four independent sources and reports orphans in both directions:

  requirements   PRD.md            FR-NNN / NFR-NNN definitions
  screens        WIREFRAME.md      SCR-NNN definitions
  tests          test/ e2e/ tests/ requirement ids inside describe()/it()/test() names
  commits        `git log` output  Conventional Commit scopes such as feat(FR-001)

Orphans matter in both directions: a requirement with no test is unverified, and a test citing an id
that no longer exists is a stale reference nobody will notice.

Usage
-----
  traceability.py [--root .] [--output text|json|markdown]
  traceability.py --root . --output markdown --write matrix.md
  traceability.py --self-test

Exit codes
----------
  0  every requirement has at least one test and no stale references exist
  1  orphans found
  2  invalid arguments
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REQ_RE = re.compile(r"\b((?:FR|NFR)-\d{3})\b")
SCR_RE = re.compile(r"\b(SCR-\d{3})\b")
TEST_NAME_RE = re.compile(r"""(?:describe|it|test)\s*(?:\.\w+)?\s*\(\s*['"`]([^'"`]+)['"`]""")
COMMIT_SCOPE_RE = re.compile(r"^\w+\(((?:FR|NFR)-\d{3})\)!?:", re.M)
TEST_DIRS = ("test", "tests", "e2e", "src")
TEST_SUFFIXES = (".test.ts", ".spec.ts", ".test.tsx", ".spec.tsx", ".test.js", ".spec.js")


def definitions(root: pathlib.Path) -> tuple[list[str], list[str]]:
    prd = root / "PRD.md"
    wire = root / "WIREFRAME.md"
    reqs = sorted(set(REQ_RE.findall(prd.read_text(encoding="utf-8")))) if prd.is_file() else []
    screens = sorted(set(SCR_RE.findall(wire.read_text(encoding="utf-8")))) if wire.is_file() else []
    return reqs, screens


def matrix_rows(root: pathlib.Path) -> dict[str, str]:
    """Requirement id -> the raw matrix row from TRD section 4."""
    trd = root / "TRD.md"
    if not trd.is_file():
        return {}
    text = trd.read_text(encoding="utf-8")
    if "## 4. Requirements Traced" not in text:
        return {}
    tail = text.split("## 4. Requirements Traced", 1)[1]
    stop = re.search(r"\n## 5\.", tail)
    section = tail[: stop.start()] if stop else tail
    rows = {}
    for line in section.splitlines():
        found = REQ_RE.search(line)
        if found and line.strip().startswith("|"):
            rows[found.group(1)] = line.strip()
    return rows


def tests(root: pathlib.Path) -> dict[str, list[str]]:
    """Requirement id -> list of `path › test name`."""
    found: dict[str, list[str]] = {}
    for directory in TEST_DIRS:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or not path.name.endswith(TEST_SUFFIXES):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            rel = path.relative_to(root).as_posix()
            for name in TEST_NAME_RE.findall(text):
                for rid in REQ_RE.findall(name):
                    found.setdefault(rid, []).append(f"{rel} \u203a {name}")
    return {k: sorted(set(v)) for k, v in sorted(found.items())}


def commits(root: pathlib.Path, limit: int = 500) -> dict[str, int]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", f"-{limit}", "--pretty=%s"],
            capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if out.returncode != 0:
        return {}
    counts: dict[str, int] = {}
    for rid in COMMIT_SCOPE_RE.findall(out.stdout):
        counts[rid] = counts.get(rid, 0) + 1
    return dict(sorted(counts.items()))


def audit(root: pathlib.Path) -> dict:
    reqs, screens = definitions(root)
    rows = matrix_rows(root)
    test_map = tests(root)
    commit_map = commits(root)

    req_set = set(reqs)
    return {
        "requirements": reqs,
        "screens": screens,
        "matrix_ids": sorted(rows),
        "tests": test_map,
        "commits": commit_map,
        "orphans": {
            "requirements_without_matrix_row": sorted(req_set - set(rows)),
            "matrix_rows_without_requirement": sorted(set(rows) - req_set),
            "requirements_without_test": sorted(req_set - set(test_map)),
            "tests_citing_unknown_requirement": sorted(set(test_map) - req_set),
            "commits_citing_unknown_requirement": sorted(set(commit_map) - req_set),
        },
        "coverage": {
            "requirements": len(reqs),
            "with_matrix_row": len(req_set & set(rows)),
            "with_test": len(req_set & set(test_map)),
        },
    }


def as_markdown(result: dict) -> str:
    lines = ["| Req ID | In matrix | Tests | Commits |", "|---|---|---|---|"]
    for rid in result["requirements"]:
        in_matrix = "yes" if rid in result["matrix_ids"] else "**no**"
        test_list = result["tests"].get(rid, [])
        cell = "<br>".join(f"`{t}`" for t in test_list) if test_list else "**none**"
        lines.append(f"| {rid} | {in_matrix} | {cell} | {result['commits'].get(rid, 0)} |")
    return "\n".join(lines) + "\n"


def as_text(result: dict) -> str:
    cov = result["coverage"]
    out = [
        f"requirements: {cov['requirements']}   in matrix: {cov['with_matrix_row']}   "
        f"with tests: {cov['with_test']}",
        f"screens defined: {len(result['screens'])}",
        "",
    ]
    labels = {
        "requirements_without_matrix_row": "requirements with no row in TRD section 4",
        "matrix_rows_without_requirement": "matrix rows citing an undefined requirement",
        "requirements_without_test": "requirements with no test naming them",
        "tests_citing_unknown_requirement": "tests citing a requirement that no longer exists",
        "commits_citing_unknown_requirement": "commit scopes citing an unknown requirement",
    }
    clean = True
    for key, label in labels.items():
        ids = result["orphans"][key]
        if ids:
            clean = False
            out.append(f"{label}:")
            out.extend(f"    {i}" for i in ids)
            out.append("")
    if clean:
        out.append("no orphans in either direction")
    return "\n".join(out).rstrip() + "\n"


SAMPLE_PRD = """## 8. Functional Requirements
| FR-001 | System MUST validate email | US1 | P1 |
| FR-002 | System MUST rate limit | US1 | P2 |
## 9. Non-Functional Requirements
| NFR-001 | Reliability | uptime | 99.9% |
"""
SAMPLE_TRD = """## 4. Requirements Traced
| FR-001 | x | 6.2 | SCR-001 | T1 | t | - | done |
| NFR-001 | x | 7.2 | - | T2 | t | - | done |
## 5. Architecture Overview
"""
SAMPLE_TEST = """
describe('FR-001 email validation', () => {
  it('rejects an address with no domain', () => {});
});
describe('FR-009 removed thing', () => {});
"""


def self_test() -> int:
    failures = []
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        (root / "test").mkdir()
        (root / "PRD.md").write_text(SAMPLE_PRD, encoding="utf-8")
        (root / "TRD.md").write_text(SAMPLE_TRD, encoding="utf-8")
        (root / "WIREFRAME.md").write_text("| SCR-001 | Home | / |\n", encoding="utf-8")
        (root / "test" / "auth.spec.ts").write_text(SAMPLE_TEST, encoding="utf-8")

        result = audit(root)
        o = result["orphans"]

        if result["requirements"] != ["FR-001", "FR-002", "NFR-001"]:
            failures.append(f"requirement extraction wrong: {result['requirements']}")
        if o["requirements_without_matrix_row"] != ["FR-002"]:
            failures.append(f"expected FR-002 missing from matrix, got "
                            f"{o['requirements_without_matrix_row']}")
        if set(o["requirements_without_test"]) != {"FR-002", "NFR-001"}:
            failures.append(f"expected FR-002 and NFR-001 untested, got "
                            f"{o['requirements_without_test']}")
        if o["tests_citing_unknown_requirement"] != ["FR-009"]:
            failures.append(f"expected FR-009 flagged as stale, got "
                            f"{o['tests_citing_unknown_requirement']}")
        if result["screens"] != ["SCR-001"]:
            failures.append(f"screen extraction wrong: {result['screens']}")
        if "FR-001" not in as_markdown(result):
            failures.append("markdown renderer dropped a row")

        commit_line = "feat(FR-001): add validation"
        if COMMIT_SCOPE_RE.findall(commit_line) != ["FR-001"]:
            failures.append("commit scope extraction failed")
        if COMMIT_SCOPE_RE.findall("feat(api)!: breaking") != []:
            failures.append("commit scope matched a non-requirement scope")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    for f in failures:
        print(f"FAIL: {f}")
    print(f"\nself-test: {len(failures)} failure(s)")
    return 1 if failures else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Audit requirement traceability.")
    ap.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    ap.add_argument("--output", choices=("text", "json", "markdown"), default="text")
    ap.add_argument("--write", type=pathlib.Path, help="write the rendered output to this file too")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 2

    result = audit(args.root)
    rendered = {"json": lambda r: json.dumps(r, indent=2),
                "markdown": as_markdown,
                "text": as_text}[args.output](result)
    print(rendered, end="" if rendered.endswith("\n") else "\n")

    if args.write:
        args.write.write_text(rendered, encoding="utf-8")

    return 1 if any(result["orphans"].values()) else 0


if __name__ == "__main__":
    sys.exit(main())
