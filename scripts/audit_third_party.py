#!/usr/bin/env python3
"""Reconcile every third-party licence marker in the tree against the inventory.

This exists because the first attempt at a consolidated notices file was
hand-written and wrong. It listed five upstream projects. The tree contains 86
licence, notice and attribution files, covering nineteen distinct projects, and
one of them, mattpocock/skills, was redistributed with prose saying "preserved
verbatim (MIT)" and no copy of the MIT notice anywhere. An independent review
found that, not this repository's own checks. So the check exists now.

The rule: every licence, notice or attribution marker under `skills/` must be
either covered by an entry in docs/third-party-inventory.json, owned by a source
in skills/vendor.manifest.json, or explicitly ignored with a stated reason.

    scripts/audit_third_party.py            # reconcile, exit 1 on any gap
    scripts/audit_third_party.py --output json
    scripts/audit_third_party.py --list     # print what was discovered and move on

Standard library only.

Exit codes
    0  every marker is accounted for
    1  a marker is unaccounted for, or an inventory entry is incomplete
    2  usage or environment error
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
INVENTORY_PATH = REPO_ROOT / "docs" / "third-party-inventory.json"
MANIFEST_PATH = SKILLS_ROOT / "vendor.manifest.json"

MARKER_PREFIXES = ("license", "licence", "notice", "copying")
MARKER_NAMES = {"attribution.md", "provenance.md", "ofl.txt"}
REQUIRED_FIELDS = ("id", "name", "author", "license", "notice", "paths")


def discover_markers() -> list:
    """Every path in skills/ that looks like a licence or attribution record."""
    found = []
    for dirpath, dirnames, filenames in os.walk(SKILLS_ROOT):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for name in sorted(filenames):
            low = name.lower()
            if low in MARKER_NAMES or low.startswith(MARKER_PREFIXES):
                found.append((Path(dirpath) / name).relative_to(REPO_ROOT).as_posix())
    return sorted(found)


def vendored_prefixes() -> list:
    if not MANIFEST_PATH.exists():
        return []
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [s["dest"].strip("/") for s in data.get("sources", []) if s.get("dest")]


def audit() -> dict:
    if not INVENTORY_PATH.exists():
        print(f"error: missing {INVENTORY_PATH}", file=sys.stderr)
        raise SystemExit(2)
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    legacy = inventory.get("legacy", [])
    ignores = inventory.get("ignore_globs", [])
    ignore_reasons = inventory.get("ignore_reasons", {})
    vendored = vendored_prefixes()

    problems = []

    # An ignore without a stated reason is how a real gap gets buried.
    for pattern in ignores:
        if not ignore_reasons.get(pattern):
            problems.append(f"ignore_globs contains `{pattern}` with no entry in ignore_reasons")

    covered_prefixes = []
    seen_ids = set()
    for entry in legacy:
        eid = entry.get("id", "<missing id>")
        for field in REQUIRED_FIELDS:
            if not entry.get(field):
                problems.append(f"[{eid}] inventory entry is missing required field `{field}`")
        if eid in seen_ids:
            problems.append(f"[{eid}] duplicate inventory id")
        seen_ids.add(eid)

        for rel in ("notice", "license_file"):
            target = entry.get(rel)
            if target and not (REPO_ROOT / target).exists():
                problems.append(f"[{eid}] `{rel}` points at a missing file: `{target}`")
        for path in entry.get("paths", []):
            if not (REPO_ROOT / path).exists():
                problems.append(f"[{eid}] declared path does not exist: `{path}`")
            covered_prefixes.append(path.strip("/"))
        if entry.get("notice"):
            covered_prefixes.append(entry["notice"])
        if entry.get("license_file"):
            covered_prefixes.append(entry["license_file"])

    markers = discover_markers()
    unaccounted, accounted, ignored = [], [], []
    for marker in markers:
        if any(fnmatch.fnmatch(marker, pat) for pat in ignores):
            ignored.append(marker)
            continue
        if any(marker == p or marker.startswith(p + "/") for p in vendored):
            accounted.append((marker, "manifest"))
            continue
        if any(marker == p or marker.startswith(p.rstrip("/") + "/") for p in covered_prefixes):
            accounted.append((marker, "inventory"))
            continue
        unaccounted.append(marker)

    for marker in unaccounted:
        problems.append(
            f"`{marker}` is a third-party licence or attribution marker that no manifest source "
            f"and no inventory entry covers. Add it to docs/third-party-inventory.json, or to "
            f"ignore_globs with a reason if it is not really a third-party notice."
        )

    return {
        "markers_found": len(markers),
        "accounted_by_manifest": sum(1 for _, w in accounted if w == "manifest"),
        "accounted_by_inventory": sum(1 for _, w in accounted if w == "inventory"),
        "ignored": ignored,
        "unaccounted": unaccounted,
        "legacy_projects": len(legacy),
        "problems": problems,
    }


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="Reconcile third-party licence markers.")
    ap.add_argument("--output", choices=("text", "json"), default="text")
    ap.add_argument("--list", action="store_true", help="print every discovered marker")
    args = ap.parse_args(argv)

    if not SKILLS_ROOT.is_dir():
        print(f"error: no skills/ directory at {SKILLS_ROOT}", file=sys.stderr)
        return 2

    result = audit()

    if args.list:
        for marker in discover_markers():
            print(marker)

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        for problem in result["problems"]:
            print(f"error: {problem}")
        print()
        print(
            f"{result['markers_found']} licence/attribution marker(s) found. "
            f"{result['accounted_by_manifest']} covered by the vendor manifest, "
            f"{result['accounted_by_inventory']} by the inventory "
            f"({result['legacy_projects']} projects), "
            f"{len(result['ignored'])} explicitly ignored, "
            f"{len(result['unaccounted'])} unaccounted for."
        )

    return 1 if result["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
