#!/usr/bin/env python3
"""Check that relative Markdown links in this repository resolve.

This replaces a paste-in shell snippet that used to live in CONTRIBUTING.md. Two
things were wrong with the snippet. It contained a literal `<dest>` placeholder,
so anyone running it verbatim matched zero files and got "0 unresolved", which
reads as success. And the counts quoted in the architecture review came from
running it by hand at one moment, so they were stale the next day.

A verification recipe that cannot fail is not a verification recipe. This is a
real checker: it reports how many files and links it examined, fails when either
count is zero, and is the same command CI runs.

    scripts/check_links.py                          # governance docs plus vendored trees
    scripts/check_links.py --scope vendored
    scripts/check_links.py --path skills/job-hunt   # any subtree
    scripts/check_links.py --output json

Standard library only.

Exit codes
    0  every relative link resolved
    1  an unresolved link, or nothing was checked
    2  usage or environment error
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "skills" / "vendor.manifest.json"
EXEMPTIONS_PATH = REPO_ROOT / "docs" / "link-check-exemptions.json"

# Inline links and reference definitions. Skips images by design: a missing image
# is a different problem and this repository has almost none.
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(\s*<?([^)>\s]+)>?\s*(?:\"[^\"]*\")?\s*\)")

SKIP_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "tel:",
    "#",
    "data:",
    "file:",
    "ftp:",
    "{",
)

GOVERNANCE_FILES = [
    "README.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "SUPPORT.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/ARCHITECTURE_REVIEW.md",
]


def vendored_dests() -> list:
    if not MANIFEST_PATH.exists():
        return []
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [s["dest"].strip("/") for s in data.get("sources", []) if s.get("dest")]


def load_exemptions() -> dict:
    if not EXEMPTIONS_PATH.exists():
        return {"exempt": []}
    return json.loads(EXEMPTIONS_PATH.read_text(encoding="utf-8"))


def gather(scope: str, extra_paths: list) -> list:
    files = []
    if scope in ("all", "governance"):
        files += [REPO_ROOT / f for f in GOVERNANCE_FILES if (REPO_ROOT / f).exists()]
    if scope in ("all", "vendored"):
        for dest in vendored_dests():
            root = REPO_ROOT / dest
            if root.is_dir():
                files += sorted(root.rglob("*.md"))
    for raw in extra_paths or []:
        target = REPO_ROOT / raw
        if target.is_dir():
            files += sorted(target.rglob("*.md"))
        elif target.is_file():
            if target.suffix.lower() != ".md":
                print(f"error: --path {raw} is not a Markdown file", file=sys.stderr)
                raise SystemExit(2)
            files.append(target)
        else:
            print(f"error: --path {raw} does not exist", file=sys.stderr)
            raise SystemExit(2)
    seen, unique = set(), []
    for f in files:
        key = f.resolve()
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def check(files: list, exemptions: dict) -> dict:
    exempt = exemptions.get("exempt", [])
    checked = 0
    unresolved = []
    exempted = []

    for path in files:
        rel_file = path.relative_to(REPO_ROOT).as_posix()
        base = path.parent
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in LINK_RE.finditer(text):
            target = match.group(1).strip()
            if not target or target.lower().startswith(SKIP_PREFIXES):
                continue
            if "://" in target:
                continue
            checked += 1
            bare = unquote(target.split("#")[0].split("?")[0])
            if not bare:
                continue
            if os.path.exists(os.path.normpath(os.path.join(base, bare))):
                continue
            rule = next(
                (
                    e
                    for e in exempt
                    if fnmatch.fnmatch(rel_file, e["file"]) and fnmatch.fnmatch(target, e["link"])
                ),
                None,
            )
            if rule:
                exempted.append(
                    {"file": rel_file, "link": target, "reason": rule.get("reason", "")}
                )
            else:
                unresolved.append({"file": rel_file, "link": target})

    return {
        "files_checked": len(files),
        "links_checked": checked,
        "unresolved": unresolved,
        "exempted": exempted,
    }


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="Check relative Markdown links resolve.")
    ap.add_argument(
        "--scope",
        choices=("all", "governance", "vendored"),
        default="all",
        help="which files to check (default: all)",
    )
    ap.add_argument("--path", action="append", help="extra file or directory (repeatable)")
    ap.add_argument("--output", choices=("text", "json"), default="text")
    args = ap.parse_args(argv)

    files = gather(args.scope, args.path)
    result = check(files, load_exemptions())

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        for item in result["unresolved"]:
            print(f"error  {item['file']} -> {item['link']}")
        for item in result["exempted"]:
            print(f"exempt {item['file']} -> {item['link']}  ({item['reason']})")
        print()
        print(
            f"{result['files_checked']} file(s), {result['links_checked']} relative link(s) checked. "
            f"{len(result['unresolved'])} unresolved, {len(result['exempted'])} exempted."
        )

    # Zero is not success. A recipe that checks nothing and prints a clean result
    # is how the old snippet hid its own uselessness.
    if not result["files_checked"] or not result["links_checked"]:
        print(
            "error: nothing was checked. Widen --scope or --path; an empty run is not a pass.",
            file=sys.stderr,
        )
        return 1
    return 1 if result["unresolved"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
