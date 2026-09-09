#!/usr/bin/env python3
"""The four-layer hierarchy, and where every node sits.

Why this exists
---------------

The first version of this graph put all 490 skills and 50 Solutions on screen at
once, packed as clusters on a golden-angle spiral. It was correct and unreadable:
540 dots of roughly equal weight, with no statement anywhere in the geometry about
what was important, so it read as a speckle. Adding more nodes to that would have
made it worse.

The library does have a structure, and it turns out to be an almost perfect tree:

    domain (7)  ->  practice (24)  ->  Solution (50)  ->  skill (490)

Measured, not assumed. Every one of the 50 Solutions draws all of its members from a
single category, so no Solution straddles a branch. Exactly one skill belongs to two
Solutions (`code-review`, which serves both `idea-to-shipped-code` and
`hard-to-find-bug`), so there is exactly one edge that a tree cannot express, and it
is drawn as a cross-link rather than pretended away.

The 24 practices are the repository's own directory names — which is why they are
called things like `pstack` and `ra-qm-team` — so they are source layout rather than
a taxonomy, and 24 of anything is too many for an opening view. The 7 domains above
them are the one editorial judgement in the whole page, and they live in
domains.json so that judgement is reviewable in a diff instead of buried in code.

Why left to right rather than rings
-----------------------------------

A radial hierarchy was the obvious first choice and the wrong one here. The graph is
rendered into a box about 2.5 times wider than it is tall, so a circle either wastes
most of the width or becomes an ellipse flat enough that the top and bottom of every
ring crowd together while the sides stretch — and labels around a flat ellipse are
unreadable at exactly the places the nodes are densest.

Four columns fit that box the way it actually is. Depth reads along the long axis,
breadth along the short one, every label runs horizontally, and the eye follows one
direction rather than orbiting.

What is on screen when
----------------------

The default view is 81 nodes: 7 domains, 24 practices, 50 Solutions. That is a
readable diagram. The 490 skills are prerendered but held at zero opacity and only
revealed for the branch being inspected, because 490 leaves in a 560-unit column
would be 1.1 units apart, which is not a visualisation of anything.
"""

import json
import math
from pathlib import Path

# The four columns, as a fraction of the frame width. Depth runs along the long axis
# of the box, so these are x positions, and the gaps between them are where each
# layer's labels live.
COLS = {"domain": 0.128, "practice": 0.371, "solution": 0.629, "skill": 0.886}

# Node radii per layer, largest at the root. A domain is not more important than a
# skill in any absolute sense, but it is a bigger claim about more things, and the
# geometry should say so.
RADII = {"domain": 9.0, "practice": 6.0, "solution": 4.6, "skill": 2.8}

# Vertical padding inside the frame, in frame units, so the outermost label of the
# tallest column is not clipped by the edge of the drawing.
PAD_Y = 26.0


class TreeError(Exception):
    """Raised when the hierarchy does not account for every skill exactly once."""


def load_domains(site_dir: Path) -> dict:
    """Read domains.json and return {domain rows, category -> domain, labels}."""
    data = json.loads((site_dir / "domains.json").read_text(encoding="utf-8"))
    cat_to_domain = {}
    for d in data["domains"]:
        for c in d["categories"]:
            if c in cat_to_domain:
                raise TreeError(
                    f"domains.json maps the category {c!r} to two domains: "
                    f"{cat_to_domain[c]!r} and {d['id']!r}"
                )
            cat_to_domain[c] = d["id"]
    return {
        "domains": data["domains"],
        "cat_to_domain": cat_to_domain,
        "labels": data["categories"],
    }


def build_tree(rows: list, sols: list, spec: dict) -> dict:
    """Assemble the hierarchy and check it accounts for every skill exactly once.

    Returns a dict of nodes keyed by id, each carrying its layer, parent, label and
    the ids of its children, plus the cross-links a tree cannot hold.

    The checks are not decoration. A category that domains.json forgot, or a skill
    that ended up under two practices, would quietly change the numbers printed on
    the page, and those numbers are the page's only claim about itself.
    """
    by_key = {r["key"]: r for r in rows}
    cat_to_domain = spec["cat_to_domain"]
    labels = spec["labels"]

    present = {r["dom"] for r in rows}
    unmapped = sorted(present - set(cat_to_domain))
    if unmapped:
        raise TreeError(
            f"domains.json does not place these categories: {unmapped}. "
            f"Every category must belong to exactly one domain."
        )
    unlabelled = sorted(present - set(labels))
    if unlabelled:
        raise TreeError(f"domains.json has no display label for: {unlabelled}")

    nodes = {}

    def add(node_id, layer, label, parent, **extra):
        if node_id in nodes:
            raise TreeError(f"two {layer} nodes claim the id {node_id!r}")
        nodes[node_id] = dict(
            id=node_id, layer=layer, label=label, parent=parent, kids=[], **extra
        )
        if parent is not None:
            nodes[parent]["kids"].append(node_id)
        return node_id

    # Layer 1. Ordered by the file, which is largest first, and that order is also
    # the top-to-bottom order on screen.
    for d in spec["domains"]:
        add(f"d:{d['id']}", "domain", d["label"], None, blurb=d.get("blurb", ""))

    # Layer 2, in descending size within each domain, so the biggest practice of a
    # domain sits nearest its parent's line.
    counts = {}
    for r in rows:
        counts[r["dom"]] = counts.get(r["dom"], 0) + 1
    for d in spec["domains"]:
        cats = [c for c in d["categories"] if c in present]
        for cat in sorted(cats, key=lambda c: (-counts[c], c)):
            add(f"p:{cat}", "practice", labels[cat], f"d:{d['id']}", cat=cat)

    # Layer 3. Every Solution's members come from one category, verified below, so a
    # Solution belongs to the practice its members belong to. That is stronger than
    # using the Solution's own directory, which for the three curated ones is
    # solutions/ and would put them outside the tree entirely.
    sol_parent = {}
    for s in sols:
        cats = {by_key[m]["dom"] for m in s["members"] if m in by_key}
        if len(cats) != 1:
            raise TreeError(
                f"Solution {s['name']!r} draws members from {sorted(cats)}. The tree "
                f"assumes one category per Solution; give it a home explicitly or "
                f"model it as a cross-cutting node."
            )
        cat = cats.pop()
        sol_parent[s["lead"]] = f"p:{cat}"

    for s in sols:
        add(
            f"s:{s['lead']}",
            "solution",
            s.get("label", s["name"]),
            sol_parent[s["lead"]],
            tier=s["tier"],
            key=s["lead"],
            problem=s.get("problem", ""),
            members=len(s["members"]),
        )

    # Layer 4. A skill hangs off its Solution when one leads it, and off its own
    # practice when none does — which is how 158 unclaimed skills stay visible and
    # navigable instead of being a number in a sentence.
    owner = {}
    for s in sols:
        # The lead is the first child of its own Solution, not a stray skill sitting
        # under the practice. Without this the 47 leads that are real skills appeared
        # twice — once as a Solution node and once as an unclaimed skill — and the
        # unclaimed count read 205 instead of 158.
        if s.get("lead_is_skill"):
            owner.setdefault(s["lead"], []).append(s["lead"])
        for m in s["members"]:
            owner.setdefault(m, []).append(s["lead"])

    cross = []
    for r in rows:
        owners = owner.get(r["key"], [])
        if owners:
            parent = f"s:{owners[0]}"
            for extra in owners[1:]:
                cross.append((f"s:{extra}", f"k:{r['key']}"))
        else:
            parent = f"p:{r['dom']}"
        add(
            f"k:{r['key']}",
            "skill",
            r["n"],
            parent,
            key=r["key"],
            cat=r["dom"],
            claimed=bool(owners),
            lead=bool(owners) and owners[0] == r["key"],
            desc=r["d"],
            repo=r["repo"],
            lic=r["lic"],
            url=r["url"],
        )

    # Every skill exactly once, and every count on the page derived from this tree
    # rather than recomputed beside it.
    skills = [n for n in nodes.values() if n["layer"] == "skill"]
    if len(skills) != len(rows):
        raise TreeError(f"{len(skills)} skill nodes for {len(rows)} skills")
    reachable = set()
    stack = [n["id"] for n in nodes.values() if n["parent"] is None]
    while stack:
        cur = stack.pop()
        if cur in reachable:
            raise TreeError(f"{cur!r} is reachable twice; this is not a tree")
        reachable.add(cur)
        stack.extend(nodes[cur]["kids"])
    if len(reachable) != len(nodes):
        orphans = sorted(set(nodes) - reachable)[:5]
        raise TreeError(f"{len(nodes) - len(reachable)} unreachable nodes, e.g. {orphans}")

    return {"nodes": nodes, "cross": cross}


def _leaves_of(nodes: dict, root: str, stop_layer: str) -> list:
    """Ids at stop_layer under root, in order, or root itself if it has none."""
    out = []
    stack = [root]
    while stack:
        cur = stack.pop()
        node = nodes[cur]
        if node["layer"] == stop_layer:
            out.append(cur)
            continue
        kids = [k for k in node["kids"] if nodes[k]["layer"] != "skill"]
        if not kids and node["layer"] != stop_layer:
            continue
        stack.extend(reversed(kids))
    return out


def layout(tree: dict, width: float = 1400.0, height: float = 560.0) -> dict:
    """Place every node. Deterministic: no randomness, no simulation, no iteration.

    Solutions are the leaves of the visible tree, so they set the vertical rhythm:
    they are spread evenly down the frame, and every parent is centred on the
    children it leads. A practice with no Solution still needs a row of its own, or
    its label would collide with the practice above it, so it takes a slot too.

    Skills are placed in the fourth column relative to their own parent, and only
    one parent is ever revealed at a time, so their slots may overlap between
    branches. That is deliberate: it lets a 21-member Solution use the full height
    of the column instead of a twenty-first of it.
    """
    nodes = tree["nodes"]
    xs = {layer: round(width * f, 1) for layer, f in COLS.items()}
    top, bottom = PAD_Y, height - PAD_Y
    mid = round(height / 2, 1)

    def spread(ids, span_per_item):
        """Evenly place ids about the vertical centre, using at most the full height."""
        if not ids:
            return {}
        if len(ids) == 1:
            return {ids[0]: mid}
        span = min(bottom - top, max(60.0, len(ids) * span_per_item))
        first = mid - span / 2
        gap = span / (len(ids) - 1)
        return {node_id: round(first + i * gap, 1) for i, node_id in enumerate(ids)}

    # One branch is open at a time, and everything below the first layer belongs to
    # exactly one branch, so every node needs exactly one position: where it sits
    # while the branch containing it is the one being read.
    #
    # This is the third arrangement of this layout and the first that is neither
    # crowded nor crossed. Placing all 50 Solutions in one column put them 9 units
    # apart, too close to label. Spreading one domain's Solutions over the full
    # height while its groups stayed on their own rows made 19 edges fan out of a
    # 90-unit cluster into a 508-unit column, crossing each other the whole way.
    # Moving the groups onto their Solutions fixed the crossings and then collided
    # with the groups of every other domain.
    #
    # Revealing one domain at a time removes all three problems at once, because the
    # full height is available to whichever branch is open: at most 19 Solutions, 26
    # units apart, with room for a label on each. The seven domains stay put as a
    # fixed spine so the shape of the library is always on screen, and the right-hand
    # rail lists all 24 groups whether or not their domain is open.
    domains = [n["id"] for n in nodes.values() if n["layer"] == "domain"]
    if not domains:
        raise TreeError("nothing to lay out")
    step = (bottom - top) / max(1, len(domains) - 1) if len(domains) > 1 else 0.0
    y_of = {d: round(top + i * step, 1) for i, d in enumerate(domains)}

    for dom_id in domains:
        # Leaves of this domain: every Solution, and any group leading none, so a
        # group with nothing composed yet still gets a row and stays clickable.
        leaves = []
        for prac in nodes[dom_id]["kids"]:
            sols_here = [
                s for s in nodes[prac]["kids"] if nodes[s]["layer"] == "solution"
            ]
            leaves.extend(sols_here if sols_here else [prac])
        placed = spread(leaves, 26.0)
        y_of.update(placed)
        # Each group sits at the middle of the Solutions it leads, which is what makes
        # the branch read as a tree rather than as a bundle of wires.
        for prac in nodes[dom_id]["kids"]:
            mine = [
                placed[s]
                for s in nodes[prac]["kids"]
                if s in placed and nodes[s]["layer"] == "solution"
            ]
            if mine:
                y_of[prac] = round(sum(mine) / len(mine), 1)
            elif prac not in y_of:
                y_of[prac] = mid

    for node_id, y in y_of.items():
        nodes[node_id]["x"] = xs[nodes[node_id]["layer"]]
        nodes[node_id]["y"] = y

    # A branch's skills, likewise over the full height, lead first.
    for parent_id in [
        n["id"] for n in nodes.values() if n["layer"] in ("solution", "practice")
    ]:
        kids = [k for k in nodes[parent_id]["kids"] if nodes[k]["layer"] == "skill"]
        if not kids:
            continue
        kids.sort(key=lambda k: (not nodes[k].get("lead"), nodes[k]["label"]))
        for kid, y in spread(kids, 15.0).items():
            nodes[kid]["x"] = xs["skill"]
            nodes[kid]["y"] = y

    for node in nodes.values():
        node["r"] = RADII[node["layer"]]
        if "x" not in node:
            raise TreeError(f"{node['id']!r} was never placed")

    return {
        "nodes": nodes,
        "cross": tree["cross"],
        "width": width,
        "height": height,
        "cols": xs,
        "rows": len(domains),
    }


def edges(lay: dict) -> list:
    """Parent-to-child edges as (parent, child, kind), skills last so they paint on top."""
    nodes = lay["nodes"]
    out = []
    for node in nodes.values():
        if node["parent"] is None:
            continue
        kind = "branch" if node["layer"] != "skill" else "leaf"
        out.append((node["parent"], node["id"], kind))
    out.sort(key=lambda e: (e[2] == "leaf", e[0], e[1]))
    return out + [(a, b, "cross") for a, b in lay["cross"]]


def curve(x1, y1, x2, y2) -> str:
    """A cubic between two columns, flat at both ends so it leaves and arrives level.

    Straight lines between four columns produce a lattice of crossings that reads as
    noise; easing the horizontal departure makes the branching legible, which is the
    whole reason to draw a tree rather than a list.
    """
    mx = (x1 + x2) / 2
    return f"M{x1},{y1} C{round(mx, 1)},{y1} {round(mx, 1)},{y2} {x2},{y2}"


def stats(lay: dict) -> dict:
    nodes = lay["nodes"]
    per = {}
    for node in nodes.values():
        per[node["layer"]] = per.get(node["layer"], 0) + 1
    return {
        "per_layer": per,
        "visible": per.get("domain", 0) + per.get("practice", 0) + per.get("solution", 0),
        "total": len(nodes),
        "cross": len(lay["cross"]),
        "unclaimed": sum(
            1 for n in nodes.values() if n["layer"] == "skill" and not n["claimed"]
        ),
    }
