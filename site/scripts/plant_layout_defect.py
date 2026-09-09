#!/usr/bin/env python3
"""Re-introduce the crossing layout, so CI can prove the tree tests still detect it.

The second arrangement of this layout spread a domain's Solutions over the full height
while leaving its groups on their own evenly spaced rows. Every edge in the largest
domain then ran from a 90-unit cluster of parents into a 508-unit column of children,
crossing its neighbours the whole way. It looked reasonable in code.

This puts that back: groups stop being centred on the Solutions they lead. The tree
tests must fail on it, or their geometry assertions are decorative.

Usage:
  python3 scripts/plant_layout_defect.py plant
  python3 scripts/plant_layout_defect.py restore
"""

import shutil
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
TARGET = SITE / "tree.py"
BACKUP = SITE / ".tree.py.orig"

ANCHOR = """        for prac in nodes[dom_id]["kids"]:
            mine = [
                placed[s]
                for s in nodes[prac]["kids"]
                if s in placed and nodes[s]["layer"] == "solution"
            ]
            if mine:
                y_of[prac] = round(sum(mine) / len(mine), 1)
            elif prac not in y_of:
                y_of[prac] = mid"""

DEFECT = """        for i, prac in enumerate(nodes[dom_id]["kids"]):
            y_of[prac] = round(top + i * 22.0, 1)"""


def plant() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if ANCHOR not in text:
        print(
            "cannot plant the defect: layout() no longer matches the expected shape. "
            "Update ANCHOR in this script, or this proof is not testing what it claims.",
            file=sys.stderr,
        )
        return 1
    shutil.copy2(TARGET, BACKUP)
    TARGET.write_text(text.replace(ANCHOR, DEFECT, 1), encoding="utf-8")
    print("planted: groups are no longer centred on the Solutions they lead")
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
