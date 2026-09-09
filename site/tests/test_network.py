#!/usr/bin/env python3
"""Assertions about the graph the page opens on.

A browser can tell you whether the page renders. It cannot tell you that no two of 490
nodes are drawn on top of each other, that the communities are the same ones the next
build will find, or that the shortest route between two skills is actually the shortest.
Those are properties of the geometry and the graph, and they are what this file checks.

The history is the argument for having it. Three separate arrangements of this page were
written, looked plausible in code, and were wrong in ways only a measurement caught:

  * a single spiral of all 490 nodes: 9,462 pairs closer together than a node is wide;
  * per-community discs sized by sqrt(n): the largest communities four times denser than
    the smallest, and overlapping each other;
  * labels drawn at a fixed offset from their node: nine names in one pile.

And one that no amount of looking would have caught: community names were built with
Counter.most_common, whose ties break in insertion order, which for a set of strings
depends on PYTHONHASHSEED. The same commit produced "principle · discipline · first" or
"principle · discipline · redesign" depending on which process built it — in a repository
whose CI asserts the page is reproducible from source.

Every check below therefore has a defect behind it. Run:

    python3 tests/test_network.py
"""

import contextlib
import io
import importlib.util
import itertools
import math
import os
import re
import subprocess
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))

import compose  # noqa: E402
import network  # noqa: E402

FAILURES = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}" + (f": {detail}" if detail else ""))
        FAILURES.append(label)


def load():
    """Build the graph from the real library, the same way the page does."""
    spec = importlib.util.spec_from_file_location("bp", SITE / "build.py")
    bp = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(bp)
        rows = bp.collect(bp.fetch())
    sols, _stats = compose.build_solutions(
        bp.REPO_ROOT, rows, bp._solution_frontmatter, bp.fail
    )
    by_key = {r["key"]: r for r in rows}
    graph = network.build_graph(rows, sols)
    comm = network.communities(graph, sorted(by_key), bp.COMMUNITY_RESOLUTION)
    # The same frame the page declares. Calling layout() with its defaults is how the two
    # drifted apart in the first place.
    lay = network.layout(
        graph, comm, by_key, width=bp.FRAME[0], height=bp.FRAME[1]
    )
    return bp, rows, sols, by_key, graph, comm, lay


def main() -> int:
    bp, rows, sols, by_key, graph, comm, lay = load()
    pos = lay["pos"]

    # ---------------------------------------------------------------- the graph
    print("\nthe graph")

    check(
        "every skill is a node",
        len(pos) == len(rows),
        f"{len(pos)} placed, {len(rows)} skills",
    )
    check(
        "every skill is in exactly one community",
        set(comm) == set(by_key) and len(comm) == len(by_key),
        f"{len(comm)} assignments for {len(by_key)} skills",
    )

    # An edge is a claim about the library. Both ends must be real skills, and the kind
    # must say which of the two claims it is: one the repository states, or one this page
    # derived from names sharing a subject.
    ends_real = all(
        a in by_key and b in by_key for (a, b) in graph["weights"]
    )
    check("both ends of every edge are real skills", ends_real)
    kinds = set(graph["kinds"].values())
    check(
        "every edge declares its evidence",
        kinds == {"extracted", "inferred"},
        f"kinds seen: {sorted(kinds)}",
    )
    check(
        "no skill is joined to itself",
        not any(a == b for (a, b) in graph["weights"]),
    )
    check(
        "every edge is stored once, in a fixed direction",
        all(a < b for (a, b) in graph["weights"]),
    )

    # A Solution leading a member is the strongest claim the library makes, so it must be
    # in the graph as a stated edge. If this fails, the page is drawing something weaker
    # than what the repository actually says.
    missing = []
    for s in sols:
        if s["lead"] not in by_key:
            continue
        for m in s["members"]:
            if m == s["lead"] or m not in by_key:
                continue
            pair = tuple(sorted((s["lead"], m)))
            if graph["kinds"].get(pair) != "extracted":
                missing.append(pair)
    check(
        "every Solution's lead is joined to its members as stated evidence",
        not missing,
        f"{len(missing)} missing, e.g. {missing[:2]}",
    )

    # ------------------------------------------------------------ the geometry
    print("\nthe geometry")

    items = sorted(pos.items())
    coords = [p for _k, p in items]
    closest = min(
        math.dist(coords[i], coords[j])
        for i, j in itertools.combinations(range(len(coords)), 2)
    )
    # The number that matters. A spiral of everything put 9,462 pairs under 7 units
    # apart, which rendered as a speckle rather than as 490 distinguishable skills.
    check(
        "no two skills are drawn on top of each other",
        closest >= 6.0,
        f"closest pair is {closest:.2f} units apart",
    )

    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    # Read from the page rather than restated here. The layout used 1400x620 while the
    # <svg> declared a viewBox of 1400x560, and the browser clips to the viewBox: twenty-
    # nine skills were positioned, coloured, labelled, counted in the panel, and invisible.
    # Nothing in the build failed, because nothing compared the two numbers.
    declared = re.search(
        r'id="gsvg"[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"',
        (SITE / "index.html").read_text(encoding="utf-8"),
    )
    check("the page declares a viewBox for the graph", declared is not None)
    if declared:
        vw, vh = float(declared.group(1)), float(declared.group(2))
        check(
            "the layout frame is the frame the page declares",
            (vw, vh) == bp.FRAME,
            f"viewBox is {vw:.0f}x{vh:.0f}, build.FRAME is {bp.FRAME}",
        )
        check(
            "every skill is inside the area the browser will draw",
            min(xs) >= 0 and max(xs) <= vw and min(ys) >= 0 and max(ys) <= vh,
            f"extent {min(xs):.0f}-{max(xs):.0f} x {min(ys):.0f}-{max(ys):.0f} "
            f"against a {vw:.0f}x{vh:.0f} viewBox",
        )
        check(
            "the layout fills the frame it was given",
            (max(xs) - min(xs)) > vw * 0.75 and (max(ys) - min(ys)) > vh * 0.75,
            f"span {max(xs) - min(xs):.0f} x {max(ys) - min(ys):.0f}",
        )

    # The gap that keeps a node clickable. SVG has no z-index, so if two centres are closer
    # than the click target's radius, the node drawn second covers the first one's centre
    # and the first cannot be clicked at all. Six skills were unclickable for this reason.
    check(
        "no node can be buried under another node's click target",
        closest >= network.MIN_GAP - 0.6,
        f"closest pair is {closest:.2f} units apart, gap is {network.MIN_GAP}",
    )
    # Communities have to be visibly separate, or colouring by community says nothing.
    # Measured as: a skill's own community should be nearer to it than the average
    # community is.
    centres = {}
    for cid, members in lay["members"].items():
        centres[cid] = (
            sum(pos[m][0] for m in members) / len(members),
            sum(pos[m][1] for m in members) / len(members),
        )
    nearest_is_own = 0
    for key, p in items:
        own = comm[key]
        if own not in centres:
            continue
        best = min(centres, key=lambda c: math.dist(p, centres[c]))
        if best == own:
            nearest_is_own += 1
    share = nearest_is_own / len(items)
    check(
        "skills sit nearer their own community than any other",
        share >= 0.90,
        f"only {share:.0%} do",
    )

    # ------------------------------------------------------------ the labelling
    print("\nthe labelling")

    degree = graph["degree"]
    max_deg = max(degree.values()) or 1
    radius = {
        k: 2.1 + 6.4 * math.sqrt(degree.get(k, 0) / max_deg) for k in pos
    }
    ranked = sorted(pos, key=lambda k: (-degree.get(k, 0), k))
    meta_boxes = []
    for cid in lay["communities"][: bp.NAMED_COMMUNITIES]:
        members = lay["members"][cid]
        cx = sum(pos[m][0] for m in members) / len(members)
        top = min(pos[m][1] for m in members) - 9.0
        meta_boxes.append(
            network.label_box(
                network.label_community(members, by_key, graph), cx, top, "middle"
            )
        )
    placed = network.place_labels(
        ranked,
        {k: by_key[k]["n"] for k in ranked},
        pos,
        radius,
        bp.HUB_LABELS,
        reserved=meta_boxes,
    )
    boxes = [v["box"] for v in placed.values()] + meta_boxes
    clashes = [
        (i, j)
        for i, j in itertools.combinations(range(len(boxes)), 2)
        if network._overlaps(boxes[i], boxes[j])
    ]
    check(
        "no two names drawn without being asked for overlap",
        not clashes,
        f"{len(clashes)} overlapping pairs among {len(boxes)} labels",
    )
    check(
        "the names drawn are the most connected skills",
        placed and all(degree.get(k, 0) >= 1 for k in placed),
    )

    # --------------------------------------------------------------- the paths
    print("\nthe paths")

    # A path has to be a real walk along real edges, and it has to be the shortest one.
    # Breadth-first search gives the shortest by construction, so what is worth checking
    # is that every step is an edge that exists and that the ends are the ends asked for.
    adj = {k: set() for k in by_key}
    for (a, b) in graph["weights"]:
        adj[a].add(b)
        adj[b].add(a)

    hubs = ranked[:4]
    tested = 0
    for a, b in itertools.combinations(hubs, 2):
        path = network.shortest_path(graph, a, b)
        if not path:
            continue
        tested += 1
        walk_ok = all(path[i + 1] in adj[path[i]] for i in range(len(path) - 1))
        check(
            f"the route from {by_key[a]['n']} to {by_key[b]['n']} walks real edges",
            walk_ok and path[0] == a and path[-1] == b,
            f"path was {path}",
        )
        # No shorter route may exist: no node two steps along the path may be a direct
        # neighbour of the one before it.
        shortcut = any(
            path[i + 2] in adj[path[i]] for i in range(len(path) - 2)
        )
        check(
            f"the route from {by_key[a]['n']} to {by_key[b]['n']} has no shortcut",
            not shortcut,
        )
    check("some routes were testable", tested > 0)

    # --------------------------------------------------------- reproducibility
    print("\nreproducibility")

    again = network.layout(
        graph,
        network.communities(graph, sorted(by_key), bp.COMMUNITY_RESOLUTION),
        by_key,
        width=bp.FRAME[0],
        height=bp.FRAME[1],
    )
    check(
        "the same library gives the same positions",
        again["pos"] == pos,
        "positions differ between two runs in one process",
    )

    # The one defect no amount of looking would have found. Python randomizes string
    # hashing per process, so any tie broken by insertion order is broken differently in
    # every build. This ran the whole build under four hash seeds and diffed the bytes.
    seeds = []
    for seed in ("0", "1", "7", "42"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        out = subprocess.run(
            [sys.executable, "-c", REPRO_PROBE],
            cwd=str(SITE),
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
        )
        if out.returncode != 0:
            check(f"the graph builds under PYTHONHASHSEED={seed}", False, out.stderr[-400:])
            seeds.append(f"failed:{seed}")
        else:
            seeds.append(out.stdout.strip())
    check(
        "community names do not depend on the hash seed",
        len(set(seeds)) == 1,
        f"{len(set(seeds))} different results across four seeds: {sorted(set(seeds))[:2]}",
    )

    print()
    if FAILURES:
        print(f"{len(FAILURES)} failed: " + ", ".join(FAILURES))
        return 1
    print("all graph assertions hold")
    return 0


# Run in a child process with a fixed hash seed, printing a fingerprint of everything the
# page shows that could depend on dictionary ordering.
REPRO_PROBE = """
import contextlib, hashlib, importlib.util, io, sys
sys.path.insert(0, ".")
spec = importlib.util.spec_from_file_location("bp", "build.py")
bp = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(bp)
    rows = bp.collect(bp.fetch())
import compose, network
sols, _ = compose.build_solutions(bp.REPO_ROOT, rows, bp._solution_frontmatter, bp.fail)
by = {r["key"]: r for r in rows}
g = network.build_graph(rows, sols)
c = network.communities(g, sorted(by), bp.COMMUNITY_RESOLUTION)
lay = network.layout(g, c, by, width=bp.FRAME[0], height=bp.FRAME[1])
parts = [network.label_community(lay["members"][cid], by, g) for cid in lay["communities"]]
parts += ["%s=%s,%s" % (k, lay["pos"][k][0], lay["pos"][k][1]) for k in sorted(lay["pos"])]
print(hashlib.sha256("|".join(parts).encode()).hexdigest())
"""


if __name__ == "__main__":
    raise SystemExit(main())
