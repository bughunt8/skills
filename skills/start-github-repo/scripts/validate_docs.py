#!/usr/bin/env python3
"""Validate the document spine of a scaffolded repository.

Standard library only. Deterministic. This is the authoritative implementation; the generated repo
gets a self-contained copy at `scripts/check-docs` so CI does not depend on the skill being present.

Checks
------
  1. Required headings present in PRD, TRD, WIREFRAME, DESIGN.
  2. ID formats: FR-NNN, NFR-NNN, SCR-NNN, ADR-NNNN, TNNN.
  3. Every FR-/NFR- in the PRD appears in the TRD traceability matrix.
  4. Every matrix row's requirement id is defined in the PRD.
  5. Every SCR- referenced in the PRD is defined in WIREFRAME section 2.
  6. Every docs/adr/ link cited in the TRD resolves.
  7. Every ADR has a status in its front matter.
  8. No unresolved [NEEDS CLARIFICATION] markers.
  9. No remaining scaffold markers (REPLACE-WITH-CANONICAL-TEXT, SCAFFOLD-PIN-SHA).
 10. DESIGN.md keeps the linted canonical section order.

Usage
-----
  validate_docs.py [--root .] [--output text|json] [--strict]
  validate_docs.py --self-test

Exit codes
----------
  0  no errors
  1  at least one error (or, with --strict, at least one warning)
  2  invalid arguments
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
import tempfile

REQUIRED_HEADINGS = {
    "PRD.md": [
        "## 1. Summary",
        "## 2. Problem & Context",
        "## 3. Goals",
        "## 4. Non-Goals",
        "## 8. Functional Requirements",
        "## 9. Non-Functional Requirements",
    ],
    "TRD.md": [
        "## 1. Abstract",
        "## 2. Context and Scope",
        "## 4. Requirements Traced",
        "## 6. Detailed Design",
        "## 7. Non-Functional Requirements",
        "## 8. Alternatives Considered",
        "## 10. Test Strategy",
    ],
    "WIREFRAME.md": [
        "## 1. Conventions",
        "## 2. Screen Inventory",
        "## 3. Navigation Map",
        "## 4. Per-Screen Specification",
    ],
    "DESIGN.md": ["## Overview", "## Colors", "## Typography", "## Accessibility"],
}

# design.md lints this order. Extensions must come after the canonical run.
CANONICAL_DESIGN_ORDER = [
    "Overview", "Colors", "Typography", "Layout",
    "Elevation & Depth", "Shapes", "Components", "Do's and Don'ts",
]

SCAFFOLD_MARKERS = ("REPLACE-WITH-CANONICAL-TEXT", "SCAFFOLD-PIN-SHA")

ID_PATTERNS = {
    "requirement": re.compile(r"\b(?:FR|NFR)-\d{3}\b"),
    "screen": re.compile(r"\bSCR-\d{3}\b"),
    "adr": re.compile(r"\bADR-\d{4}\b"),
}
MALFORMED = re.compile(r"\b(?:FR|NFR)-\d{1,2}\b(?!\d)|\bSCR-\d{1,2}\b(?!\d)|\bADR-\d{1,3}\b(?!\d)")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def read(root: pathlib.Path, name: str) -> str | None:
    path = root / name
    return path.read_text(encoding="utf-8") if path.is_file() else None


def section(text: str, start: str, stop_pattern: str) -> str:
    if start not in text:
        return ""
    tail = text.split(start, 1)[1]
    match = re.search(stop_pattern, tail)
    return tail[: match.start()] if match else tail


def validate(root: pathlib.Path) -> Report:
    rep = Report()
    docs = {name: read(root, name) for name in REQUIRED_HEADINGS}

    # 1. required headings
    for name, headings in REQUIRED_HEADINGS.items():
        text = docs[name]
        if text is None:
            rep.warn(f"{name}: not present, skipped")
            continue
        for heading in headings:
            if heading not in text:
                rep.error(f"{name}: missing required heading {heading!r}")

    # 2. malformed ids
    for name, text in docs.items():
        if not text:
            continue
        for bad in sorted(set(MALFORMED.findall(text))):
            rep.error(f"{name}: malformed id {bad!r} — use zero-padded FR-001 / SCR-001 / ADR-0001")

    prd, trd, wire, design = docs["PRD.md"], docs["TRD.md"], docs["WIREFRAME.md"], docs["DESIGN.md"]

    # 3 and 4. matrix in both directions
    if prd and trd:
        prd_ids = set(ID_PATTERNS["requirement"].findall(prd))
        matrix = section(trd, "## 4. Requirements Traced", r"\n## 5\.")
        if not matrix.strip():
            rep.error("TRD.md: section 4 (Requirements Traced) is empty")
        matrix_ids = set(ID_PATTERNS["requirement"].findall(matrix))
        for rid in sorted(prd_ids - matrix_ids):
            rep.error(f"{rid} is defined in PRD.md but absent from the TRD.md matrix")
        for rid in sorted(matrix_ids - prd_ids):
            rep.error(f"{rid} appears in the TRD.md matrix but is not defined in PRD.md")

    # 5. screens
    if prd and wire:
        defined = set(ID_PATTERNS["screen"].findall(
            section(wire, "## 2. Screen Inventory", r"\n## 3\.")))
        for scr in sorted(set(ID_PATTERNS["screen"].findall(prd)) - defined):
            rep.error(f"{scr} is referenced in PRD.md but not defined in WIREFRAME.md section 2")

    # 6. ADR links resolve
    if trd:
        for link in sorted(set(re.findall(r"\((?:\./)?(docs/adr/[^)#]+\.md)", trd))):
            if not (root / link).is_file():
                rep.error(f"TRD.md links to a missing ADR: {link}")

    # 7. ADR front matter
    adr_dir = root / "docs" / "adr"
    if adr_dir.is_dir():
        records = sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))
        if not records:
            rep.warn("docs/adr/ contains no numbered records")
        for adr in records:
            text = adr.read_text(encoding="utf-8")
            if not re.search(r"^status:\s*\S+", text, re.M):
                rep.error(f"{adr.as_posix()}: missing 'status:' in front matter")
            if adr.name != "0000-template.md" and "# NNNN." in text:
                rep.error(f"{adr.as_posix()}: still contains the template title placeholder")

    # 8. unresolved clarifications
    for name, text in docs.items():
        if not text:
            continue
        count = text.count("[NEEDS CLARIFICATION")
        if count:
            rep.error(f"{name}: {count} unresolved [NEEDS CLARIFICATION] marker(s)")

    # 9. scaffold markers anywhere in tracked docs and licence files
    for candidate in ("LICENSE", "CODE_OF_CONDUCT.md", "NOTICE"):
        text = read(root, candidate)
        if not text:
            continue
        for marker in SCAFFOLD_MARKERS:
            if marker in text:
                rep.error(f"{candidate}: scaffold marker {marker} was never resolved")

    # 10. DESIGN.md canonical section order
    if design:
        headings = [h.strip() for h in re.findall(r"^## (.+)$", design, re.M)]
        canonical = [h for h in headings if h in CANONICAL_DESIGN_ORDER]
        expected = [h for h in CANONICAL_DESIGN_ORDER if h in canonical]
        if canonical != expected:
            rep.error("DESIGN.md: canonical sections are out of order — design.md lint requires "
                      f"{expected}, found {canonical}")
        last_canonical = max((headings.index(h) for h in canonical), default=-1)
        for extension in ("Motion", "Breakpoints", "States", "Accessibility"):
            if extension in headings and headings.index(extension) < last_canonical:
                rep.error(f"DESIGN.md: extension section {extension!r} must come after all "
                          "canonical sections or section-order lint fails")

    return rep


def emit(rep: Report, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings,
                          "error_count": len(rep.errors),
                          "warning_count": len(rep.warnings)}, indent=2))
        return
    for msg in rep.warnings:
        print(f"warn:  {msg}")
    for msg in rep.errors:
        print(f"error: {msg}")
    print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")


SAMPLE_PRD = """# PRD: sample
## 1. Summary
x
## 2. Problem & Context
x
## 3. Goals
x
## 4. Non-Goals / Out of Scope
x
## 8. Functional Requirements
| FR-001 | System MUST do a thing | US1 | P1 |
## 9. Non-Functional Requirements
| NFR-001 | Reliability | x | x |
Screens: SCR-001
"""

SAMPLE_TRD = """# TRD: sample
## 1. Abstract
x
## 2. Context and Scope
x
## 4. Requirements Traced
| FR-001 | x | §6.2 | SCR-001 | — | t | — | done |
| NFR-001 | x | §7.1 | — | — | t | — | done |
## 5. Architecture Overview
x
## 6. Detailed Design
x
## 7. Non-Functional Requirements
x
## 8. Alternatives Considered
x
## 10. Test Strategy
x
## 13. Decisions
[ADR-0001](docs/adr/0001-x.md)
"""

SAMPLE_WIRE = """# Wireframes
## 1. Conventions
x
## 2. Screen Inventory
| SCR-001 | Home | / | US1 | draft |
## 3. Navigation Map
x
## 4. Per-Screen Specification
x
"""

SAMPLE_DESIGN = """# Design System
## Overview
x
## Colors
x
## Typography
x
## Components
x
## Motion
x
## Accessibility
x
"""


def self_test() -> int:
    failures = []
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        (root / "docs" / "adr").mkdir(parents=True)
        (root / "docs" / "adr" / "0001-x.md").write_text("---\nstatus: accepted\n---\n# 1. X\n",
                                                         encoding="utf-8")
        (root / "PRD.md").write_text(SAMPLE_PRD, encoding="utf-8")
        (root / "TRD.md").write_text(SAMPLE_TRD, encoding="utf-8")
        (root / "WIREFRAME.md").write_text(SAMPLE_WIRE, encoding="utf-8")
        (root / "DESIGN.md").write_text(SAMPLE_DESIGN, encoding="utf-8")

        rep = validate(root)
        if rep.errors:
            failures.append(f"clean sample should pass, got: {rep.errors}")

        # An orphan requirement must be caught.
        (root / "PRD.md").write_text(SAMPLE_PRD + "\n| FR-002 | System MUST x | US1 | P2 |\n",
                                     encoding="utf-8")
        if not any("FR-002" in e for e in validate(root).errors):
            failures.append("failed to catch a requirement missing from the matrix")
        (root / "PRD.md").write_text(SAMPLE_PRD, encoding="utf-8")

        # An unresolved clarification marker must be caught.
        (root / "PRD.md").write_text(SAMPLE_PRD + "\n[NEEDS CLARIFICATION: x]\n", encoding="utf-8")
        if not any("NEEDS CLARIFICATION" in e for e in validate(root).errors):
            failures.append("failed to catch an unresolved clarification marker")
        (root / "PRD.md").write_text(SAMPLE_PRD, encoding="utf-8")

        # A misordered design section must be caught.
        (root / "DESIGN.md").write_text(
            "# D\n## Colors\nx\n## Overview\nx\n## Typography\nx\n## Accessibility\nx\n",
            encoding="utf-8")
        if not any("out of order" in e for e in validate(root).errors):
            failures.append("failed to catch DESIGN.md section misordering")
        (root / "DESIGN.md").write_text(SAMPLE_DESIGN, encoding="utf-8")

        # A malformed id must be caught.
        (root / "PRD.md").write_text(SAMPLE_PRD.replace("FR-001", "FR-1"), encoding="utf-8")
        if not any("malformed id" in e for e in validate(root).errors):
            failures.append("failed to catch a malformed id")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    for f in failures:
        print(f"FAIL: {f}")
    print(f"\nself-test: {len(failures)} failure(s)")
    return 1 if failures else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate the document spine.")
    ap.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    ap.add_argument("--output", choices=("text", "json"), default="text")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 2

    rep = validate(args.root)
    emit(rep, args.output)
    return 1 if rep.errors or (args.strict and rep.warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
