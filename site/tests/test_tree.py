#!/usr/bin/env python3
"""Unit tests for the four-layer hierarchy and its layout.

The browser tests can see whether the drawing is legible. They cannot see whether it
is true — whether every skill is a leaf exactly once, whether a group's count is the
size of its own subtree, whether the arrangement of a branch is free of crossings.
Those are properties of the data and the geometry, so they are asserted here against
the engine, before anything is drawn.

Several of these exist because the same defect appeared three times in three
different arrangements of this layout, and the browser passed each time.

Run: python3 tests/test_tree.py
"""

import contextlib
import importlib.util
import io
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))

import compose  # noqa: E402
import tree  # noqa: E402

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label}" + (f"\n        {detail}" if detail else ""))
        FAILURES.append(label)


def load():
    spec = importlib.util.spec_from_file_location("bp", SITE / "build.py")
    bp = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(bp)
    rows = bp.collect(bp.fetch())
    sols, stats = compose.build_solutions(
        bp.REPO_ROOT, rows, bp._solution_frontmatter, bp.fail
    )
    spec2 = tree.load_domains(SITE)
    hier = tree.build_tree(rows, sols, spec2)
    lay = tree.layout(hier)
    return rows, sols, stats, spec2, lay


# ------------------------------------------------------------------ the top layer


def test_domains(rows, spec):
    """domains.json is the only editorial judgement on the page, so it is checked.

    Every category exactly once, no category invented, none forgotten, all labelled.
    A category that slipped out of this file would silently vanish from the top layer
    while its skills still appeared in the library, and the two halves of the page
    would disagree about how big the library is.
    """
    present = {r["dom"] for r in rows}
    mapped = set(spec["cat_to_domain"])
    check("every category belongs to a domain", not (present - mapped),
          f"unmapped: {sorted(present - mapped)}")
    check("no domain claims a category that does not exist", not (mapped - present),
          f"phantom: {sorted(mapped - present)}")
    check("every category has a display label",
          not (present - set(spec["labels"])),
          f"unlabelled: {sorted(present - set(spec['labels']))}")

    seen = {}
    dupes = []
    for d in spec["domains"]:
        for c in d["categories"]:
            if c in seen:
                dupes.append((c, seen[c], d["id"]))
            seen[c] = d["id"]
    check("no category is in two domains", not dupes, str(dupes))

    # The repository's own directory names are not a taxonomy: `pstack`, `shuohao`
    # and `ra-qm-team` mean nothing to a reader, which is the reason this layer
    # exists. So a label may not simply be the directory name.
    lazy = [c for c, lab in spec["labels"].items() if lab == c]
    check("no label is just the directory name", not lazy, str(lazy))


# ---------------------------------------------------------------- the tree itself


def test_shape(rows, sols, stats, lay):
    nodes = lay["nodes"]
    per = {}
    for n in nodes.values():
        per[n["layer"]] = per.get(n["layer"], 0) + 1

    check("one node per skill", per["skill"] == len(rows),
          f'{per["skill"]} vs {len(rows)}')
    check("one node per Solution", per["solution"] == len(sols),
          f'{per["solution"]} vs {len(sols)}')
    check("one node per category", per["practice"] == len({r["dom"] for r in rows}))
    check("seven domains", per["domain"] == 7, str(per.get("domain")))

    # A skill is a leaf exactly once. Its lead is a child of its own Solution rather
    # than a stray under the practice: when it was both, 47 leads were counted twice
    # and the unclaimed figure read 205 instead of 158.
    keys = [n["key"] for n in nodes.values() if n["layer"] == "skill"]
    check("no skill is drawn twice", len(set(keys)) == len(keys))
    check("every skill in the library is a leaf",
          set(keys) == {r["key"] for r in rows})

    unclaimed = sum(
        1 for n in nodes.values() if n["layer"] == "skill" and not n["claimed"]
    )
    check("the unclaimed count agrees with the composition engine",
          unclaimed == stats["unclaimed"],
          f'tree says {unclaimed}, compose says {stats["unclaimed"]}')

    # Exactly one parent each, and a parent one layer up — except a skill, which may
    # hang off a Solution or, when nothing leads it, off its own group.
    order = ["domain", "practice", "solution", "skill"]
    bad = []
    for n in nodes.values():
        if n["parent"] is None:
            if n["layer"] != "domain":
                bad.append(f'{n["id"]} is a root {n["layer"]}')
            continue
        parent_layer = nodes[n["parent"]]["layer"]
        if n["layer"] == "skill":
            ok = parent_layer in ("solution", "practice")
        else:
            ok = order.index(parent_layer) == order.index(n["layer"]) - 1
        if not ok:
            bad.append(f'a {n["layer"]} hangs off a {parent_layer}')
    check("the layers nest", not bad, str(bad[:3]))


def test_counts(lay):
    """A node's count is the size of its own subtree.

    Every group label read "0" on the first build, because the count was being looked
    up under the domain's key rather than the node's. The label is the only place a
    reader is told how big a group is, so a wrong number there is a wrong page.
    """
    nodes = lay["nodes"]

    def subtree_skills(node_id):
        node = nodes[node_id]
        if node["layer"] == "skill":
            return 1
        return sum(subtree_skills(k) for k in node["kids"])

    total = sum(
        subtree_skills(n["id"]) for n in nodes.values() if n["layer"] == "domain"
    )
    check("the domains account for every skill between them",
          total == sum(1 for n in nodes.values() if n["layer"] == "skill"),
          str(total))

    for n in nodes.values():
        if n["layer"] == "practice":
            mine = subtree_skills(n["id"])
            check(
                f'{n["label"]} counts its own {mine} skills',
                mine > 0,
                "a group with no skills should not exist",
            ) if mine == 0 else None


# ---------------------------------------------------------------------- geometry


def test_geometry(lay):
    """No crossings inside a branch, and enough room to label what is on screen.

    This is the third arrangement of this layout. The first put all 50 Solutions in
    one column, 9 units apart, too close to label. The second spread one domain's
    Solutions over the full height while its groups stayed on their own rows, so 19
    edges fanned out of a 90-unit cluster and crossed each other the whole way. The
    third moved the groups onto their Solutions, which fixed the crossings and
    collided with the groups of every other domain. Each of those looked plausible in
    code and wrong on screen, so the properties are asserted rather than eyeballed.
    """
    nodes = lay["nodes"]
    height = lay["height"]

    for n in nodes.values():
        check(f'{n["id"]} is inside the frame',
              0 <= n["y"] <= height and 0 <= n["x"] <= lay["width"],
              f'({n["x"]}, {n["y"]})') if not (
            0 <= n["y"] <= height and 0 <= n["x"] <= lay["width"]
        ) else None

    domains = [n for n in nodes.values() if n["layer"] == "domain"]
    ys = sorted(d["y"] for d in domains)
    gaps = [b - a for a, b in zip(ys, ys[1:])]
    check("the domain spine is evenly spaced and legible",
          min(gaps) > 40, f"smallest gap {min(gaps)}")

    for dom in domains:
        # Within a branch, going down the groups in order must give Solutions in
        # order. Any inversion is an edge crossing another edge.
        ordered = [
            s
            for prac in dom["kids"]
            for s in nodes[prac]["kids"]
            if nodes[s]["layer"] == "solution"
        ]
        sol_ys = [nodes[s]["y"] for s in ordered]
        check(f'{dom["label"]}: no crossings among its Solutions',
              sol_ys == sorted(sol_ys), str(sol_ys))

        prac_ys = [nodes[p]["y"] for p in dom["kids"]]
        check(f'{dom["label"]}: its groups stay in order',
              prac_ys == sorted(prac_ys), str(prac_ys))

        # The property that actually makes a branch readable: a group sits on the
        # middle of the Solutions it leads.
        #
        # Order alone is not enough, and asserting only order is a mistake this test
        # made first. The second arrangement of this layout kept every group and every
        # Solution in order — no line technically crossed another — and still looked
        # like a bundle of wires, because the six groups sat inside a 90-unit cluster
        # while their 19 Solutions were spread over 508 units, so every edge left the
        # same small region at a different steep angle. Distance from the middle of
        # its own children is the thing to measure.
        for prac in dom["kids"]:
            kids = [
                nodes[s]["y"]
                for s in nodes[prac]["kids"]
                if nodes[s]["layer"] == "solution"
            ]
            if not kids:
                continue
            middle = sum(kids) / len(kids)
            off = abs(nodes[prac]["y"] - middle)
            check(
                f'{dom["label"]}: {nodes[prac]["label"]} sits on its Solutions',
                off <= 1.0,
                f"{off:.1f} units away from the middle of its {len(kids)} children",
            )

        if len(sol_ys) > 1:
            gap = min(b - a for a, b in zip(sol_ys, sol_ys[1:]))
            # 13 units is about 11 rendered pixels at the width the drawing gets,
            # which is the floor for an 11px label on every row.
            check(f'{dom["label"]}: room to label all {len(sol_ys)} Solutions',
                  gap >= 13.0, f"{gap} units apart")

    # And the densest state the drawing ever reaches: the largest Solution's skills.
    worst = None
    for n in nodes.values():
        if n["layer"] not in ("solution", "practice"):
            continue
        kids = [k for k in n["kids"] if nodes[k]["layer"] == "skill"]
        if len(kids) > 1:
            kys = sorted(nodes[k]["y"] for k in kids)
            gap = min(b - a for a, b in zip(kys, kys[1:]))
            if worst is None or gap < worst[1]:
                worst = (n["label"], gap, len(kids))
    check(f"room to label the densest branch ({worst[0]}, {worst[2]} skills)",
          worst[1] >= 11.0, f"{worst[1]} units apart")


def test_determinism(rows, sols, spec):
    a = tree.layout(tree.build_tree(rows, sols, spec))
    b = tree.layout(tree.build_tree(rows, sols, spec))
    check(
        "the layout is identical when computed twice",
        [(n["id"], n["x"], n["y"]) for n in a["nodes"].values()]
        == [(n["id"], n["x"], n["y"]) for n in b["nodes"].values()],
    )


def test_rejects_bad_input(rows, sols, spec):
    """A category missing from domains.json must fail the build, not be dropped."""
    broken = {
        "domains": [
            {**d, "categories": [c for c in d["categories"] if c != "engineering"]}
            for d in spec["domains"]
        ],
        "cat_to_domain": {
            k: v for k, v in spec["cat_to_domain"].items() if k != "engineering"
        },
        "labels": spec["labels"],
    }
    try:
        tree.build_tree(rows, sols, broken)
        check("a category missing from domains.json fails the build", False,
              "it was accepted")
    except tree.TreeError as e:
        check("a category missing from domains.json fails the build",
              "engineering" in str(e), str(e))

    no_label = {**spec, "labels": {k: v for k, v in spec["labels"].items()
                                   if k != "design"}}
    try:
        tree.build_tree(rows, sols, no_label)
        check("a category with no label fails the build", False, "it was accepted")
    except tree.TreeError as e:
        check("a category with no label fails the build", "design" in str(e), str(e))


def main():
    rows, sols, stats, spec, lay = load()
    per = {}
    for n in lay["nodes"].values():
        per[n["layer"]] = per.get(n["layer"], 0) + 1
    print(
        f"\n{per['domain']} domains, {per['practice']} groups, "
        f"{per['solution']} Solutions, {per['skill']} skills\n"
    )
    print("the top layer")
    test_domains(rows, spec)
    print("the tree")
    test_shape(rows, sols, stats, lay)
    test_counts(lay)
    print("geometry")
    test_geometry(lay)
    test_determinism(rows, sols, spec)
    print("bad input")
    test_rejects_bad_input(rows, sols, spec)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} failed: {', '.join(FAILURES)}")
        return 1
    print("all tree checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
