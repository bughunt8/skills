#!/usr/bin/env python3
"""Re-introduce the graph's real defects, so CI can prove the tests still catch them.

A test suite that has never failed is a suite nobody has checked. Each defect below was
actually written, actually shipped into a build, and actually found by measuring rather
than by looking. Planting one must make `tests/test_network.py` fail; if it passes, the
corresponding assertion is decorative and should be deleted or rewritten.

  spacing  No separation pass. Springs and repulsion do not guarantee a minimum gap, and
           a clique makes it worse: every skill sharing a name token attracts every other
           one, so a dozen collapse onto a single point. Without this pass the first
           layout put 9,462 pairs of nodes closer together than a node is wide.

           Note what this defect is NOT. Sizing the community discs by sqrt(n) instead of
           by area — the second real defect this page had — no longer fails the spacing
           assertion, because the separation pass corrects for it. That was checked, and
           it is why this planted defect targets the pass itself: the assertion protects
           the guarantee, and the guarantee lives in _separate.

  labels   Names drawn at a fixed offset from their own node, with no collision test. In
           the densest community nine of them landed on top of each other.

  seed     Community names built with Counter.most_common, whose ties break in insertion
           order — which, for a set of strings, depends on PYTHONHASHSEED. The same commit
           produced "principle · discipline · first" or "principle · discipline · redesign"
           depending on which process built the page.

Usage:
  python3 scripts/plant_network_defect.py plant <spacing|labels|seed>
  python3 scripts/plant_network_defect.py restore
"""

import shutil
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
TARGET = SITE / "network.py"
BACKUP = SITE / ".network.py.orig"

DEFECTS = {
    # ---------------------------------------------------------------- spacing
    "spacing": (
        """    n = len(points)
    for _ in range(passes):
        moved = False""",
        """    n = len(points)
    for _ in range(0):
        moved = False""",
    ),
    # ----------------------------------------------------------------- labels
    "labels": (
        """        for ox, oy, anchor in options:
            box = label_box(name, ox, oy, anchor)
            if box[0] < frame[0] or box[2] > frame[2]:
                continue
            if box[1] < frame[1] or box[3] > frame[3]:
                continue
            if any(_overlaps(box, other) for other in boxes):
                continue
            placed[key] = {""",
        """        for ox, oy, anchor in options[:1]:
            box = label_box(name, ox, oy, anchor)
            placed[key] = {""",
    ),
    # ------------------------------------------------------------------- seed
    "seed": (
        """    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]""",
        """    top = counts.most_common(3)""",
    ),
}


def plant(name: str) -> int:
    if name not in DEFECTS:
        print(f"unknown defect {name!r}; choose from {sorted(DEFECTS)}")
        return 2
    anchor, defect = DEFECTS[name]
    text = TARGET.read_text(encoding="utf-8")
    if anchor not in text:
        print(
            f"cannot plant {name!r}: network.py no longer matches the expected shape.\n"
            "Update the anchor in this script, or this proof is not testing what it "
            "claims to test."
        )
        return 2
    if not BACKUP.exists():
        shutil.copy2(TARGET, BACKUP)
    TARGET.write_text(text.replace(anchor, defect, 1), encoding="utf-8")
    print(f"planted {name!r}: the graph tests must now fail")
    return 0


def restore() -> int:
    if not BACKUP.exists():
        print("nothing to restore")
        return 0
    shutil.copy2(BACKUP, TARGET)
    BACKUP.unlink()
    print("restored network.py")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "plant":
        raise SystemExit(plant(sys.argv[2] if len(sys.argv) > 2 else ""))
    if len(sys.argv) >= 2 and sys.argv[1] == "restore":
        raise SystemExit(restore())
    print(__doc__)
    raise SystemExit(2)
