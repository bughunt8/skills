#!/usr/bin/env python3
"""Validate a scaffolded repository's structure and catch the traps that break it silently.

Standard library only. Deterministic. No network access.

Checks
------
Presence
  Required artifacts exist in one of the locations GitHub actually searches
  (.github/ -> root -> docs/), and LICENSE exists at root because it CANNOT be inherited from an
  organization default community health file.

Structural traps
  1. Every workflow declares `permissions:`.
  2. No action is referenced by a bare tag — a SHA is the only immutable reference.
  3. No workflow combines `pull_request_target` with checking out the PR head.
  4. Every pull-request-triggered workflow sets `concurrency`.
  5. `.env` is ignored and `.env.example` is not; same for `.dev.vars`.
  6. `.github/ISSUE_TEMPLATE/config.yml` exists whenever the directory does.
  7. No unresolved scaffold marker remains.
  8. Issue forms do not rely on `required: true` in a private repository without saying so.
  9. No committed `.env` or `.dev.vars` file.

Usage
-----
  validate_repo.py [--root .] [--visibility private|public] [--output text|json]
  validate_repo.py --self-test

Exit codes
----------
  0  no errors        1  at least one error        2  invalid arguments
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
import tempfile

# name -> locations searched, in GitHub's own order
HEALTH_FILES = {
    "README.md": [".github", ".", "docs"],
    "CONTRIBUTING.md": [".github", ".", "docs"],
    "CODE_OF_CONDUCT.md": [".github", ".", "docs"],
    "SECURITY.md": [".github", ".", "docs"],
    "SUPPORT.md": [".github", ".", "docs"],
}
ROOT_ONLY = ["LICENSE"]  # cannot be inherited from an org .github repository
OTHER_REQUIRED = [
    "AGENTS.md",
    ".gitignore",
    ".github/pull_request_template.md",
    ".github/dependabot.yml",
]

USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)", re.M)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SCAFFOLD_MARKERS = ("REPLACE-WITH-CANONICAL-TEXT", "SCAFFOLD-PIN-SHA")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, m: str) -> None:
        self.errors.append(m)

    def warn(self, m: str) -> None:
        self.warnings.append(m)


def found_in(root: pathlib.Path, name: str, locations) -> str | None:
    for loc in locations:
        candidate = root / loc / name if loc != "." else root / name
        if candidate.is_file():
            return candidate.relative_to(root).as_posix()
    return None


def check_presence(root: pathlib.Path, rep: Report) -> None:
    for name, locations in HEALTH_FILES.items():
        if not found_in(root, name, locations):
            rep.error(f"missing {name} (searched {', '.join(locations)})")
    for name in ROOT_ONLY:
        if not (root / name).is_file():
            rep.error(f"missing {name} at the repository root — it cannot be inherited from an "
                      "organization default community health file")
    for rel in OTHER_REQUIRED:
        if not (root / rel).is_file():
            rep.error(f"missing {rel}")

    issue_dir = root / ".github" / "ISSUE_TEMPLATE"
    if issue_dir.is_dir():
        if not (issue_dir / "config.yml").is_file():
            rep.error(".github/ISSUE_TEMPLATE/ exists without config.yml — every surveyed repo "
                      "with this directory ships one; without it, blank issues stay enabled and "
                      "questions land in the tracker")
        forms = sorted(issue_dir.glob("*.yml")) + sorted(issue_dir.glob("*.yaml"))
        if len(forms) <= 1:
            rep.warn(".github/ISSUE_TEMPLATE/ has no issue forms besides config.yml")
    else:
        rep.warn("no .github/ISSUE_TEMPLATE/ directory")

    if (root / ".github" / "PULL_REQUEST_TEMPLATE").is_dir():
        rep.warn("a PULL_REQUEST_TEMPLATE/ directory is present; selection requires a hand-built "
                 "?quick_pull=1&template=... URL, so document those URLs in CONTRIBUTING.md")


def check_workflows(root: pathlib.Path, rep: Report) -> None:
    wf_dir = root / ".github" / "workflows"
    if not wf_dir.is_dir():
        rep.warn("no .github/workflows/ directory")
        return

    files = sorted(list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml")))
    if not files:
        rep.warn(".github/workflows/ contains no workflow files")

    for path in files:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")

        if not re.search(r"^permissions:", text, re.M):
            rep.error(f"{rel}: no top-level `permissions:` — the workflow inherits the default "
                      "token scope")

        # A freshly scaffolded workflow carries the pin marker. Report that once instead of
        # repeating the same finding for every action in the file.
        awaiting_pins = "SCAFFOLD-PIN-SHA" in text
        unpinned = []
        for ref in USES_RE.findall(text):
            if ref.startswith("./") or ref.startswith("docker://"):
                continue
            if "@" not in ref:
                rep.error(f"{rel}: action {ref!r} has no version reference at all")
                continue
            if not SHA_RE.match(ref.rsplit("@", 1)[1]):
                unpinned.append(ref)

        if unpinned and awaiting_pins:
            rep.error(f"{rel}: {len(unpinned)} action(s) still awaiting SHA resolution "
                      f"({', '.join(sorted(set(unpinned)))}) — resolve each to a full-length commit "
                      "SHA and remove the SCAFFOLD-PIN-SHA comments")
        elif unpinned:
            for ref in sorted(set(unpinned)):
                rep.error(f"{rel}: action {ref!r} is pinned to a mutable reference — resolve it to "
                          "a full-length commit SHA")

        triggers = text.split("jobs:", 1)[0]

        # Only a real trigger key counts. Prose mentioning the trigger in a comment does not.
        if re.search(r"^\s{2,}pull_request_target:", triggers, re.M):
            head_checkout = bool(
                re.search(r"ref:\s*\$\{\{\s*github\.event\.pull_request\.head", text)
                or "head.sha" in text
            )
            if head_checkout:
                rep.error(f"{rel}: combines pull_request_target with a checkout of the pull request "
                          "head — this runs untrusted code with a privileged token")
            else:
                rep.warn(f"{rel}: uses pull_request_target; confirm it never checks out PR head code")

        if re.search(r"^\s{2,}pull_request:", triggers, re.M) and not re.search(
                r"^concurrency:", text, re.M):
            rep.warn(f"{rel}: pull-request-triggered without `concurrency:` — runs will pile up")

        for marker in SCAFFOLD_MARKERS:
            if marker in text and marker != "SCAFFOLD-PIN-SHA":
                rep.error(f"{rel}: scaffold marker {marker} was never resolved")


def check_env(root: pathlib.Path, rep: Report) -> None:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return
    ignore = gitignore.read_text(encoding="utf-8")

    for secret, example in ((".env", ".env.example"), (".dev.vars", ".dev.vars.example")):
        has_example = (root / example).is_file()
        ignores_secret = re.search(rf"^{re.escape(secret)}(\.\*)?\s*$", ignore, re.M)
        negates_example = f"!{example}" in ignore

        if has_example and not ignores_secret:
            rep.error(f"{example} is committed but .gitignore does not ignore {secret}")
        if has_example and re.search(rf"^{re.escape(secret)}\.\*", ignore, re.M) and not negates_example:
            rep.error(f".gitignore ignores {secret}.* without a `!{example}` negation, so the "
                      "committed template will be excluded")

    for leaked in (".env", ".dev.vars"):
        if (root / leaked).is_file():
            rep.error(f"{leaked} exists in the working tree — it must never be committed")


def check_markers(root: pathlib.Path, rep: Report) -> None:
    for name in ("LICENSE", "NOTICE", "CODE_OF_CONDUCT.md"):
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in SCAFFOLD_MARKERS:
            if marker in text:
                rep.error(f"{name}: scaffold marker {marker} was never resolved")


def check_forms(root: pathlib.Path, rep: Report, visibility: str) -> None:
    if visibility != "private":
        return
    issue_dir = root / ".github" / "ISSUE_TEMPLATE"
    if not issue_dir.is_dir():
        return
    for path in sorted(issue_dir.glob("*.yml")):
        if path.name == "config.yml":
            continue
        text = path.read_text(encoding="utf-8")
        if "required: true" in text and "*(required)*" not in text:
            rep.warn(f"{path.relative_to(root).as_posix()}: uses `required: true`, which is not "
                     "enforced in a private repository — mark the requirement in the field label too")


def validate(root: pathlib.Path, visibility: str) -> Report:
    rep = Report()
    check_presence(root, rep)
    check_workflows(root, rep)
    check_env(root, rep)
    check_markers(root, rep)
    check_forms(root, rep, visibility)
    return rep


def emit(rep: Report, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings,
                          "error_count": len(rep.errors),
                          "warning_count": len(rep.warnings)}, indent=2))
        return
    for m in rep.warnings:
        print(f"warn:  {m}")
    for m in rep.errors:
        print(f"error: {m}")
    print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")


def self_test() -> int:
    failures = []
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
        for name in ("README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
                     "SUPPORT.md", "LICENSE", "AGENTS.md"):
            (root / name).write_text("x\n", encoding="utf-8")
        (root / ".github" / "pull_request_template.md").write_text("x\n", encoding="utf-8")
        (root / ".github" / "dependabot.yml").write_text("version: 2\n", encoding="utf-8")
        (root / ".github" / "ISSUE_TEMPLATE" / "config.yml").write_text(
            "blank_issues_enabled: false\n", encoding="utf-8")
        (root / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").write_text(
            "name: Bug\nbody: []\n", encoding="utf-8")
        (root / ".gitignore").write_text(".env\n.env.*\n!.env.example\n", encoding="utf-8")
        (root / ".env.example").write_text("A=\n", encoding="utf-8")

        good = ("name: CI\non:\n  pull_request:\npermissions:\n  contents: read\n"
                "concurrency:\n  group: ci\njobs:\n  a:\n    steps:\n"
                "      - uses: actions/checkout@" + "a" * 40 + "\n")
        (root / ".github" / "workflows" / "ci.yml").write_text(good, encoding="utf-8")

        rep = validate(root, "public")
        if rep.errors:
            failures.append(f"clean sample should pass, got: {rep.errors}")

        # unpinned action
        (root / ".github" / "workflows" / "ci.yml").write_text(
            good.replace("a" * 40, "v4"), encoding="utf-8")
        if not any("mutable reference" in e for e in validate(root, "public").errors):
            failures.append("failed to catch an unpinned action")

        # missing permissions
        (root / ".github" / "workflows" / "ci.yml").write_text(
            good.replace("permissions:\n  contents: read\n", ""), encoding="utf-8")
        if not any("permissions" in e for e in validate(root, "public").errors):
            failures.append("failed to catch a workflow without permissions")

        # pull_request_target + head checkout
        danger = good + ("  b:\n    steps:\n      - uses: actions/checkout@" + "b" * 40 +
                         "\n        with:\n          ref: ${{ github.event.pull_request.head.sha }}\n")
        (root / ".github" / "workflows" / "ci.yml").write_text(
            danger.replace("pull_request:", "pull_request_target:"), encoding="utf-8")
        if not any("pull_request_target" in e for e in validate(root, "public").errors):
            failures.append("failed to catch pull_request_target with a head checkout")
        (root / ".github" / "workflows" / "ci.yml").write_text(good, encoding="utf-8")

        # env negation missing
        (root / ".gitignore").write_text(".env\n.env.*\n", encoding="utf-8")
        if not any("negation" in e for e in validate(root, "public").errors):
            failures.append("failed to catch a missing .env.example negation")
        (root / ".gitignore").write_text(".env\n.env.*\n!.env.example\n", encoding="utf-8")

        # missing config.yml
        (root / ".github" / "ISSUE_TEMPLATE" / "config.yml").unlink()
        if not any("config.yml" in e for e in validate(root, "public").errors):
            failures.append("failed to catch a missing ISSUE_TEMPLATE/config.yml")
        (root / ".github" / "ISSUE_TEMPLATE" / "config.yml").write_text("x\n", encoding="utf-8")

        # scaffold marker
        (root / "LICENSE").write_text("SCAFFOLD MARKER: REPLACE-WITH-CANONICAL-TEXT\n",
                                      encoding="utf-8")
        if not any("REPLACE-WITH-CANONICAL-TEXT" in e for e in validate(root, "public").errors):
            failures.append("failed to catch an unresolved scaffold marker")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    for f in failures:
        print(f"FAIL: {f}")
    print(f"\nself-test: {len(failures)} failure(s)")
    return 1 if failures else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate a scaffolded repository.")
    ap.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    ap.add_argument("--visibility", choices=("private", "public"), default="private")
    ap.add_argument("--output", choices=("text", "json"), default="text")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 2

    rep = validate(args.root, args.visibility)
    emit(rep, args.output)
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
