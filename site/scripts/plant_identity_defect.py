#!/usr/bin/env python3
"""Re-introduce the identity defect, so CI can prove the tests still detect it.

A test suite that has never failed is a suite nobody has checked. The composition
tests exist because the browser tests passed while the graph was drawing one node
for two different skills, so it matters that they would fail again if that returned.

This makes the graph index nodes by display name instead of by identity — exactly
the defect that fused the two `run` skills and pointed agenthub's `init` edge at
playwright-pro's. CI runs it, expects tests/test_compose.py to fail, then restores.

Usage:
  python3 scripts/plant_identity_defect.py plant    # writes the defect in
  python3 scripts/plant_identity_defect.py restore  # puts the original back
"""

import shutil
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
TARGET = SITE / "compose.py"
BACKUP = SITE / ".compose.py.orig"

ANCHOR = '    by_key = {r["key"]: r for r in rows}\n    for s in ordered:'
DEFECT = '''    by_key = {r["key"]: r for r in rows}
    _real_add = add

    def add(key, kind, dom, r, x, y, sol="", label=""):  # noqa: F811
        _real_add(key.split("~")[-1], kind, dom, r, x, y, sol, label)

    for s in ordered:'''


def plant() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if ANCHOR not in text:
        print(
            "cannot plant the defect: layout() no longer matches the expected "
            "shape. Update ANCHOR in this script, or the proof is not testing "
            "what it claims to.",
            file=sys.stderr,
        )
        return 1
    shutil.copy2(TARGET, BACKUP)
    TARGET.write_text(text.replace(ANCHOR, DEFECT, 1), encoding="utf-8")
    print("planted: the graph is indexed by display name instead of identity")
    return 0


def restore() -> int:
    if not BACKUP.exists():
        print("nothing to restore", file=sys.stderr)
        return 1
    shutil.move(str(BACKUP), str(TARGET))
    print("restored")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit(plant() if cmd == "plant" else restore() if cmd == "restore" else 2)
