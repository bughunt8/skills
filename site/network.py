#!/usr/bin/env python3
"""The library as a knowledge graph: evidence, communities, hubs, paths, layout.

Why this exists
---------------

The page has had three previous openings. A spiral packing of all 540 Solutions and
skills, which was an even speckle. A four-column dendrogram of the taxonomy, which was
organised and inert — it showed the filing system, and a filing system is not a
finding. Both drew the structure someone had already decided on.

This draws the structure the library actually has. Skills are nodes, relationships are
edges with stated evidence, communities are detected rather than declared, and the
things everything flows through are visible because they are large.

Two kinds of edge, and the difference is stated on screen
--------------------------------------------------------

EXTRACTED — the repository says so:
  * a Solution's lead to each skill it leads
  * skills that are siblings inside the same bundle directory

INFERRED — derived, and weaker:
  * skills whose names share a meaningful token, weighted down as the token gets more
    common, because `stitch-code-to-design` and `stitch-design-md` sharing "stitch" is
    strong evidence and two skills both containing "review" is weak evidence

Nothing here invents a skill, renames one, or asserts a relationship with no basis in
the files. An inferred edge is drawn faintly and dashed and says what it is when you
select it.

Communities are detected, not declared
--------------------------------------

Louvain modularity maximisation, two-phase, deterministic: nodes are visited in sorted
order and ties break on the lower community id, so the same input always gives the same
partition. This matters twice — the build is byte-compared in CI, and a colouring that
moved between runs would be a colouring that means nothing.

The detected communities are then compared against the seven editorial domains in
domains.json, and where they disagree that disagreement is worth showing: a community
holding `board-deck-builder`, `email-template-builder` and `helm-chart-builder` is a
real shared concern that the filing system splits across three domains.
"""

import collections
import itertools
import json
import math
import re
from pathlib import Path

# Tokens that carry no information about what a skill is for. Every skill in a library
# of agent skills is a skill, about an agent, by an expert.
# Words that say nothing about what a skill is about.
#
# The first list was function words plus a few repo conventions, and it was not enough. An
# independent review found `customer-success-manager` joined to `env-secrets-manager`, and
# `board-prep` joined to `gdpr-audit-prep`, on the strength of "manager" and "prep". Those
# are job titles and generic actions: two skills sharing one is evidence of nothing.
#
# So the list now covers three kinds of empty word: function words, the repository's own
# packaging conventions, and — the ones that were doing the damage — seniority, role and
# artefact-shape nouns that describe the wrapper rather than the subject.
STOP = {
    # function words
    "the", "and", "for", "with", "your", "you", "from", "this", "that", "all", "new",
    "get", "use", "using", "into", "via", "per", "any", "one", "two", "sub", "non",
    # repository conventions and generic skill words
    "skill", "skills", "agent", "agents", "init", "run", "status", "core", "team",
    "auto", "full", "pro", "max", "mini", "basic", "advanced", "general", "custom",
    # seniority and role: a title, not a subject
    "senior", "junior", "staff", "principal", "chief", "head", "officer", "director",
    "manager", "advisor", "adviser", "consultant", "specialist", "expert", "analyst",
    "coordinator", "assistant", "associate", "partner", "executive", "operator",
    # artefact shape: describes the wrapper, not what it is about
    "builder", "generator", "creator", "maker", "helper", "wizard", "toolkit",
    "template", "checklist", "guide", "playbook", "handbook", "pack", "kit", "suite",
    "tool", "tools", "helper", "assist", "prep", "setup", "config", "util", "utils",
    "manager", "handler", "wrapper", "engine", "service", "system",
}

# A token shared by more than this many skills is a word, not a subject.
TOKEN_CAP = 28

# A shared word this common or rarer is specific enough to imply a relationship on its own.
# Above it, a single word in common is not evidence and the pair needs a second one.
NARROW_TOKEN = 8
MIN_TOKEN = 3

# Weights. A lead leading a skill is the strongest statement the repository makes; a
# shared bundle is next; a shared name token is graded down by how common it is.
W_LEAD = 4.0
W_SIBLING = 1.5


def _token_weight(n: int) -> float:
    return 2.2 / math.log2(n + 2)


def build_graph(rows: list, sols: list) -> dict:
    """Return nodes, edges and per-node degree for the skill network."""
    by_key = {r["key"]: r for r in rows}
    weights: dict = collections.defaultdict(float)
    kinds: dict = {}
    why: dict = collections.defaultdict(list)

    def link(a, b, w, kind, reason):
        if a == b or a not in by_key or b not in by_key:
            return
        pair = (a, b) if a < b else (b, a)
        weights[pair] += w
        # An edge with both kinds of evidence is an extracted one: the stronger claim
        # is the true one, and the inferred agreement is a coincidence on top of it.
        if kinds.get(pair) != "extracted":
            kinds[pair] = kind
        if reason not in why[pair]:
            why[pair].append(reason)

    for s in sols:
        label = s.get("label", s["name"])
        lead = s["lead"] if s["lead"] in by_key else None
        if lead:
            for member in s["members"]:
                link(lead, member, W_LEAD, "extracted", f"led by {label}")
            continue
        # Three of the curated Solutions are written as a document rather than led by one
        # of the 490 skills, so there is no lead node to hang them from. Skipping them
        # silently was wrong twice over: their relationships vanished from the graph, and
        # five of their members were left with no edges at all and drawn on the frontier
        # ring as though nothing in the library connected them.
        #
        # What the repository states about them is that these skills work together, so
        # that is what goes in: the members joined to each other, as stated evidence.
        members = sorted(m for m in s["members"] if m in by_key)
        for a, b in itertools.combinations(members, 2):
            link(a, b, W_SIBLING, "extracted", f"steps of {label}")

    bundles: dict = collections.defaultdict(list)
    for r in rows:
        if r["bundle"]:
            bundles[(r["dom"], r["bundle"])].append(r["key"])
    for (dom, bundle), members in sorted(bundles.items()):
        if 2 <= len(members) <= 14:
            for a, b in itertools.combinations(sorted(members), 2):
                link(a, b, W_SIBLING, "extracted", f"siblings in {bundle}")

    # ---------------------------------------------------------------- inferred
    #
    # Two skills whose names share a subject. This is the weaker half of the graph and the
    # page says so: these edges are drawn dashed and faint, and one control throws them all
    # away.
    #
    # The first version made a clique for every shared token, and an independent review was
    # right that the result was often meaningless — `creative-research` joined to
    # `clinical-research` because both contain "research". One word in common is not
    # evidence, so an edge now needs one of two things:
    #
    #   * two or more shared subject words — `stitch-design-md` and `stitch-code-to-design`
    #     share both "stitch" and "design", which is a real family; or
    #   * one shared word that is specific enough to mean something, which is defined as
    #     being used by at most NARROW_TOKEN skills. "cro" across 8 skills says something.
    #     "research" across 12 does not.
    #
    # Broad words are still allowed to reinforce an edge that qualifies on other grounds;
    # they are simply not allowed to create one on their own.
    tokens: dict = collections.defaultdict(list)
    for r in rows:
        for t in re.split(r"[^a-z0-9]+", r["n"].lower()):
            if len(t) >= MIN_TOKEN and t not in STOP:
                tokens[t].append(r["key"])
    # A name's first word is a family prefix in this repository: the 21 `principle-*` skills
    # and the 15 `stitch-*` skills are deliberately named as sets. That convention is worth
    # trusting even when the word is common, so a shared prefix qualifies on its own —
    # otherwise the rule above would dissolve two of the library's most real families for
    # being too large.
    prefix_of = {}
    for r in rows:
        head = re.split(r"[^a-z0-9]+", r["n"].lower())
        prefix_of[r["key"]] = head[0] if head and head[0] not in STOP else None

    shared: dict = collections.defaultdict(list)
    token_used = 0
    for token, holders in sorted(tokens.items()):
        holders = sorted(set(holders))
        if not 2 <= len(holders) <= TOKEN_CAP:
            continue
        token_used += 1
        for a, b in itertools.combinations(holders, 2):
            shared[(a, b)].append((token, len(holders)))

    for (a, b), found in sorted(shared.items()):
        narrow = [t for t, n in found if n <= NARROW_TOKEN]
        family = (
            prefix_of.get(a) is not None and prefix_of.get(a) == prefix_of.get(b)
        )
        if len(found) < 2 and not narrow and not family:
            continue
        weight = sum(_token_weight(n) for _t, n in found)
        words = ", ".join(f'"{t}"' for t, _n in found[:3])
        reason = f"named {prefix_of[a]}-*" if family and len(found) < 2 else (
            f"names share {words}"
        )
        link(a, b, weight, "inferred", reason)

    degree = collections.Counter()
    strength = collections.Counter()
    for (a, b), w in weights.items():
        degree[a] += 1
        degree[b] += 1
        strength[a] += w
        strength[b] += w

    return {
        "weights": dict(weights),
        "kinds": kinds,
        "why": {k: v for k, v in why.items()},
        "degree": degree,
        "strength": strength,
        "tokens_used": token_used,
        "tokens_seen": len(tokens),
    }


# ------------------------------------------------------------------ communities


def _one_level(adj: dict, nodes: list, resolution: float) -> dict:
    comm = {n: n for n in nodes}
    m2 = sum(sum(d.values()) for d in adj.values())
    if m2 <= 0:
        return comm
    k = {n: sum(adj[n].values()) for n in nodes}
    tot = collections.Counter()
    for n in nodes:
        tot[comm[n]] += k[n]

    for _ in range(30):
        moved = False
        for n in nodes:
            c0 = comm[n]
            tot[c0] -= k[n]
            links = collections.Counter()
            for nb, w in sorted(adj[n].items()):
                if nb != n:
                    links[comm[nb]] += w
            best, best_gain = c0, links[c0] - resolution * tot[c0] * k[n] / m2
            for c, w in sorted(links.items()):
                gain = w - resolution * tot[c] * k[n] / m2
                # Deterministic tie-break, so the same graph always partitions the same
                # way. The colouring is compared byte for byte by the build gate.
                if gain > best_gain + 1e-12 or (
                    abs(gain - best_gain) < 1e-12 and str(c) < str(best)
                ):
                    best, best_gain = c, gain
            tot[best] += k[n]
            comm[n] = best
            if best != c0:
                moved = True
        if not moved:
            break
    return comm


def communities(graph: dict, nodes: list, resolution: float = 1.0,
                levels: int = 6) -> dict:
    """Two-phase Louvain: move nodes, aggregate, repeat.

    The aggregation phase is the half that was missing first time round. Without it
    only local moves are possible, so the partition stalls at around a hundred
    communities — most of them two or three nodes — and the resolution parameter has no
    effect at all, which is how the omission announced itself.
    """
    adj: dict = collections.defaultdict(dict)
    for n in nodes:
        adj[n] = {}
    for (a, b), w in graph["weights"].items():
        adj[a][b] = adj[a].get(b, 0.0) + w
        adj[b][a] = adj[b].get(a, 0.0) + w

    membership = {n: n for n in nodes}
    current_nodes = list(nodes)
    current_adj = adj

    for _ in range(levels):
        part = _one_level(current_adj, current_nodes, resolution)
        if len(set(part.values())) == len(current_nodes):
            break
        membership = {n: part[membership[n]] for n in nodes}

        merged: dict = collections.defaultdict(dict)
        for a in current_nodes:
            ca = part[a]
            # Touch it even when it has no edges. 34 skills share a name token with
            # nothing and belong to no Solution, so their communities have no edges at
            # all, and building the aggregate graph only from edges dropped them —
            # after which the next level could not find them and the whole run failed.
            merged[ca]
            for b, w in current_adj[a].items():
                cb = part[b]
                merged[ca][cb] = merged[ca].get(cb, 0.0) + w
        current_nodes = sorted(merged, key=str)
        current_adj = merged
        if len(current_nodes) <= 1:
            break

    # Stable, readable ids: largest community first.
    sizes = collections.Counter(membership.values())
    order = sorted(sizes, key=lambda c: (-sizes[c], str(c)))
    rename = {c: i for i, c in enumerate(order)}
    return {n: rename[c] for n, c in membership.items()}


def label_community(members: list, rows_by_key: dict, graph: dict) -> str:
    """Name a community from the tokens its members actually share.

    No language model and no hand-written list: the label is the most common meaningful
    token among the members, which is the same evidence the inferred edges came from,
    so the name and the shape agree by construction.
    """
    counts = collections.Counter()
    for key in members:
        for t in set(re.split(r"[^a-z0-9]+", rows_by_key[key]["n"].lower())):
            if len(t) >= MIN_TOKEN and t not in STOP:
                counts[t] += 1
    if not counts:
        return "unnamed"
    # Sorted by count and then by the token itself. Counter.most_common breaks ties in
    # insertion order, and the insertion order here comes from iterating a set of
    # strings, whose order depends on PYTHONHASHSEED. Community 6 was named
    # "principle · discipline · first" or "principle · discipline · redesign" depending
    # on which process built the page — a reproducibility failure in the output of a
    # build the repository claims is reproducible from source.
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    if top[0][1] < 2:
        # Nothing shared: name it after the strongest member instead.
        hub = max(members, key=lambda k: (graph["degree"][k], k))
        return rows_by_key[hub]["n"]
    return " · ".join(t for t, n in top if n >= 2)


# The distance every pair of nodes must clear. It is not a cosmetic minimum: the click
# target around a node has a radius of about 6.5 units, and SVG has no z-index, so if two
# centres are closer than that the node drawn second covers the first one's centre and the
# first cannot be clicked at all. Four skills were unclickable for exactly this reason.
MIN_GAP = 15.0

# The graph's coordinate system. build.FRAME passes this in explicitly; these defaults
# exist only so the module is usable on its own, and they match, because the layout using
# 620 while the page's <svg> declared 560 clipped twenty-nine skills out of view without
# anything failing.
FRAME = (1400.0, 560.0)


# ------------------------------------------------------------------------ paths


def shortest_path(graph: dict, a: str, b: str) -> list:
    """Breadth-first hops between two skills, or [] if they are not connected.

    Unweighted on purpose: "how many steps from here to there" is the question a reader
    asks, and a strong edge is not a shorter one.
    """
    if a == b:
        return [a]
    adj: dict = collections.defaultdict(list)
    for (x, y) in graph["weights"]:
        adj[x].append(y)
        adj[y].append(x)
    seen = {a: None}
    queue = collections.deque([a])
    while queue:
        cur = queue.popleft()
        for nb in sorted(adj[cur]):
            if nb in seen:
                continue
            seen[nb] = cur
            if nb == b:
                path = [nb]
                while path[-1] is not None:
                    path.append(seen[path[-1]])
                return list(reversed(path[:-1]))
            queue.append(nb)
    return []


# ----------------------------------------------------------------------- layout


GOLDEN = math.pi * (3 - math.sqrt(5))


def _spiral(n: int, radius: float) -> list:
    """n deterministic starting points on a golden-angle spiral. No randomness anywhere
    in this module: the build is byte-compared, so a seeded shuffle would be a liability
    with no upside."""
    out = []
    for i in range(n):
        r = radius * math.sqrt((i + 0.5) / max(1, n))
        a = i * GOLDEN
        out.append([math.cos(a) * r, math.sin(a) * r])
    return out


def _relax(points: list, edges: list, iterations: int, k: float,
           gravity: float = 0.02) -> None:
    """Fruchterman-Reingold in place: springs along edges, repulsion between all pairs.

    Small enough to be exact rather than approximated, because it only ever runs over
    one community at a time — the largest is 50 nodes — plus once over the 53 community
    centroids. An all-pairs pass over all 490 at once would be 120,000 distances per
    iteration in pure Python, which is why the layout is done per community and then
    assembled.
    """
    n = len(points)
    if n < 2:
        return
    temp = k * 0.9
    cool = temp / (iterations + 1)
    for _ in range(iterations):
        disp = [[0.0, 0.0] for _ in range(n)]
        for i in range(n):
            xi, yi = points[i]
            for j in range(i + 1, n):
                dx = xi - points[j][0]
                dy = yi - points[j][1]
                d2 = dx * dx + dy * dy
                if d2 < 1e-9:
                    # Two nodes on the same spot have no direction to separate along, so
                    # push them apart along a fixed axis derived from their indices —
                    # deterministic, unlike the usual random jitter.
                    dx, dy, d2 = (1e-3 * (1 + (i % 3)), 1e-3 * (1 + (j % 5)), 1e-6)
                d = math.sqrt(d2)
                f = (k * k) / d
                disp[i][0] += dx / d * f
                disp[i][1] += dy / d * f
                disp[j][0] -= dx / d * f
                disp[j][1] -= dy / d * f
        for (i, j, w) in edges:
            dx = points[i][0] - points[j][0]
            dy = points[i][1] - points[j][1]
            d = math.sqrt(dx * dx + dy * dy) or 1e-6
            f = (d * d) / k * min(3.0, w)
            disp[i][0] -= dx / d * f
            disp[i][1] -= dy / d * f
            disp[j][0] += dx / d * f
            disp[j][1] += dy / d * f
        for i in range(n):
            # A little pull to the middle, or a component with no edges to the rest
            # drifts away forever and the drawing ends up mostly empty space.
            disp[i][0] -= points[i][0] * gravity
            disp[i][1] -= points[i][1] * gravity
            dx, dy = disp[i]
            d = math.sqrt(dx * dx + dy * dy) or 1e-6
            step = min(d, temp)
            points[i][0] += dx / d * step
            points[i][1] += dy / d * step
        temp -= cool


def _separate(points: list, min_dist: float, passes: int = 6) -> None:
    """Push points apart until none are closer than min_dist. In place, deterministic.

    Springs and repulsion do not guarantee this on their own, and a clique makes it
    worse: every skill whose name contains the same token is attracted to every other
    one, so a dozen of them collapse onto a single spot. Relaxation decides the shape;
    this decides that two nodes are never drawn on top of each other.
    """
    n = len(points)
    for _ in range(passes):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                dx = points[j][0] - points[i][0]
                dy = points[j][1] - points[i][1]
                d = math.hypot(dx, dy)
                if d >= min_dist:
                    continue
                if d < 1e-9:
                    dx, dy, d = 1.0 + (i % 3) * 0.3, 0.4 + (j % 4) * 0.3, 1.0
                push = (min_dist - d) / 2
                points[i][0] -= dx / d * push
                points[i][1] -= dy / d * push
                points[j][0] += dx / d * push
                points[j][1] += dy / d * push
                moved = True
        if not moved:
            break


def _pack_discs(radii: list, edges: list, width: float, height: float) -> list:
    """Place non-overlapping discs, pulled together by the edges that cross between them.

    Relaxation alone cannot do this: springs and repulsion know nothing about how big a
    disc is, so communities of 50 and of 4 were pushed the same distance apart and
    overlapped each other. Every iteration here ends with a separation pass, which is
    what actually guarantees the discs stay apart, and the springs only decide which
    neighbours end up near which.
    """
    n = len(radii)
    if n == 0:
        return []
    cx, cy = width / 2, height / 2
    order = sorted(range(n), key=lambda i: -radii[i])
    # Largest in the middle, the rest spiralling out: a deterministic start that is
    # already roughly right, so the relaxation has little to undo.
    points = [[0.0, 0.0] for _ in range(n)]
    step = max(radii) * 1.7
    for rank, i in enumerate(order):
        r = step * math.sqrt(rank)
        a = rank * GOLDEN
        points[i] = [cx + math.cos(a) * r, cy + math.sin(a) * r * 0.62]

    for _ in range(260):
        disp = [[0.0, 0.0] for _ in range(n)]
        for (i, j, w) in edges:
            dx = points[i][0] - points[j][0]
            dy = points[i][1] - points[j][1]
            d = math.hypot(dx, dy) or 1e-6
            f = min(2.4, w) * 0.9
            disp[i][0] -= dx / d * f
            disp[i][1] -= dy / d * f
            disp[j][0] += dx / d * f
            disp[j][1] += dy / d * f
        for i in range(n):
            disp[i][0] += (cx - points[i][0]) * 0.012
            disp[i][1] += (cy - points[i][1]) * 0.02
            points[i][0] += disp[i][0]
            points[i][1] += disp[i][1]

        # Separation, twice, because one pass can push a disc into a third one.
        for _ in range(2):
            for a in range(n):
                for b in range(a + 1, n):
                    dx = points[b][0] - points[a][0]
                    dy = points[b][1] - points[a][1]
                    d = math.hypot(dx, dy)
                    # 24 rather than 14. Tightening the edge rules split the library into
                    # 31 communities from 19, and at 14 units apart only 88% of skills sat
                    # nearer their own community's centre than any other's - which makes
                    # colouring by community say less than it claims.
                    want = radii[a] + radii[b] + 24.0
                    if d < want:
                        if d < 1e-9:
                            dx, dy, d = 1.0 + (a % 3), 0.5 + (b % 3), 1.0
                        push = (want - d) / 2
                        points[a][0] -= dx / d * push
                        points[a][1] -= dy / d * push
                        points[b][0] += dx / d * push
                        points[b][1] += dy / d * push
        for i in range(n):
            points[i][0] = min(width - radii[i] - 6, max(radii[i] + 6, points[i][0]))
            points[i][1] = min(height - radii[i] - 6, max(radii[i] + 6, points[i][1]))
    return points


def layout(graph: dict, comm: dict, rows_by_key: dict,
           width: float = FRAME[0], height: float = FRAME[1]) -> dict:
    """Force-directed, computed per community and then assembled.

    Laid out in three stages, for the reason a single global simulation cannot be used
    here: 490 nodes all-pairs is 120,000 distances an iteration in pure Python, and the
    build runs in CI with the standard library only. Per community it is about 17,000,
    which is seconds rather than minutes.

      1. every community becomes one super-node, and those are relaxed against each
         other using the edges that cross between them, so related subjects end up near
         each other rather than in filing order
      2. each community is relaxed internally using only its own edges
      3. members are placed around their community's centre, scaled by how many there
         are, and the whole drawing is fitted to the frame

    The 34 skills that share a name token with nothing and belong to no Solution have no
    edges at all. They are not hidden and not dropped: they sit on a ring around
    everything else, which is a fair picture of what they are — the part of the library
    nothing has connected yet.
    """
    nodes = sorted(rows_by_key)
    degree = graph["degree"]

    members: dict = collections.defaultdict(list)
    for n in nodes:
        members[comm[n]].append(n)
    # Isolated skills form their own single-member communities; keep them apart from the
    # ones with real structure so they can be drawn as a frontier.
    linked = {c: m for c, m in members.items() if any(degree[n] for n in m)}
    lone = sorted(n for c, m in members.items() if c not in linked for n in m)

    order = sorted(linked, key=lambda c: (-len(linked[c]), c))
    index = {c: i for i, c in enumerate(order)}

    between: dict = collections.defaultdict(float)
    for (a, b), w in graph["weights"].items():
        ca, cb = comm[a], comm[b]
        if ca in index and cb in index and ca != cb:
            pair = (index[ca], index[cb]) if index[ca] < index[cb] else (index[cb], index[ca])
            between[pair] += w

    # Each community gets area in proportion to how many skills it holds, so the
    # spacing between neighbouring skills is about the same everywhere. Sizing the
    # radius by sqrt(n) alone left the big communities four times denser than the small
    # ones, and 9,462 pairs of nodes ended up closer together than a node is wide.
    frame_area = width * height
    fill = 0.30
    per_node = frame_area * fill / max(1, len(nodes))
    radii = [
        max(18.0, math.sqrt(len(linked[c]) * per_node / math.pi)) for c in order
    ]

    edges_between = [
        (i, j, w / 6.0) for (i, j), w in sorted(between.items())
    ]
    centres = _pack_discs(radii, edges_between, width, height)

    placed: dict = {}
    for c in order:
        mine = sorted(linked[c], key=lambda n: (-degree[n], n))
        local_index = {n: i for i, n in enumerate(mine)}
        radius = radii[index[c]] * 0.82
        pts = _spiral(len(mine), radius)
        edges = []
        for (a, b), w in graph["weights"].items():
            if a in local_index and b in local_index:
                edges.append((local_index[a], local_index[b], w))
        _relax(
            pts,
            sorted(edges),
            iterations=220,
            k=radius / max(1.4, math.sqrt(len(mine))),
            gravity=0.05,
        )
        # No two skills drawn on top of each other. The gap is derived from the room
        # the community actually has, so a crowded community is tight but still legible
        # rather than collapsed.
        _separate(
            pts,
            min_dist=max(MIN_GAP, radius * 2.0 / max(2.0, math.sqrt(len(mine)))),
        )
        # Keep every member inside its own disc, or a community with one loosely
        # attached member throws it into the next community and the colours interleave.
        for pt in pts:
            d = math.hypot(pt[0], pt[1])
            if d > radius:
                pt[0] *= radius / d
                pt[1] *= radius / d
        # Clamping can push two nodes back together on the rim, so separate once more
        # and accept a slightly larger disc rather than an overlap.
        _separate(pts, min_dist=MIN_GAP, passes=4)
        cx0, cy0 = centres[index[c]]
        for n in mine:
            px, py = pts[local_index[n]]
            placed[n] = [cx0 + px, cy0 + py]

    # One last pass over everything. Two discs that end up touching can still put a
    # node from each within a few units of the other, which no per-community pass can
    # see because neither community knows about the other.
    keys = sorted(placed)
    pts = [placed[k] for k in keys]
    _separate(pts, min_dist=MIN_GAP, passes=4)
    for k, pt in zip(keys, pts):
        placed[k] = pt

    # Fit what has been placed, then put the unconnected skills outside it.
    xs = [p[0] for p in placed.values()] or [0.0]
    ys = [p[1] for p in placed.values()] or [0.0]
    span_x = max(xs) - min(xs) or 1.0
    span_y = max(ys) - min(ys) or 1.0
    pad = 30.0
    # Never magnify: the discs were packed to fit already, and scaling up would undo
    # the spacing they were sized for.
    scale = min(1.0, (width - 2 * pad) / span_x, (height - 2 * pad) / span_y)
    off_x = (width - span_x * scale) / 2 - min(xs) * scale
    off_y = (height - span_y * scale) / 2 - min(ys) * scale

    out: dict = {}
    for n, (x, y) in placed.items():
        out[n] = [x * scale + off_x, y * scale + off_y]

    # The skills nothing references and no Solution leads: 34 of them, on a ring outside
    # the body of the graph. Drawn faintly rather than dropped, because the frontier of a
    # library is a fact about it.
    cx, cy = width / 2, height / 2
    rx, ry = width / 2 - 12.0, height / 2 - 12.0
    for i, n in enumerate(lone):
        a = -math.pi / 2 + math.tau * i / max(1, len(lone))
        out[n] = [cx + math.cos(a) * rx, cy + math.sin(a) * ry]

    # One separation pass over everything, the ring included. The ring was placed after
    # the body and never checked against it, so four skills ended up close enough to a
    # neighbour that the neighbour's click target covered their centre: they were drawn,
    # labelled, and could not be clicked. The gap has to exceed the click target's radius,
    # or a node can be buried under one drawn after it.
    keys = sorted(out)
    pts = [out[k] for k in keys]
    _separate(pts, min_dist=MIN_GAP, passes=6)

    # Rounded and clamped FIRST, then separated, then rounded again with a margin.
    #
    # Separating and then rounding is what the first version did, and rounding moves a
    # point by up to 0.05 in each axis while clamping can move it much further: the closest
    # pair came out at 14.75 units against a guarantee of 15. A review caught it, and the
    # honest fix is to make the guarantee true of the coordinates that are actually written
    # into the page rather than of an intermediate the page never sees.
    for i, pt in enumerate(pts):
        pts[i] = [
            round(min(width - 4.0, max(4.0, pt[0])), 1),
            round(min(height - 4.0, max(4.0, pt[1])), 1),
        ]
    _separate(pts, min_dist=MIN_GAP + 0.3, passes=8)
    for k, pt in zip(keys, pts):
        out[k] = (
            round(min(width - 4.0, max(4.0, pt[0])), 1),
            round(min(height - 4.0, max(4.0, pt[1])), 1),
        )

    return {
        "pos": out,
        "communities": order,
        "members": {c: sorted(linked[c], key=lambda n: (-degree[n], n)) for c in order},
        "lone": lone,
        "width": width,
        "height": height,
    }


def load_domains(site_dir: Path) -> dict:
    """The declared taxonomy, kept for comparison rather than for drawing.

    It used to be the top layer of the page. It is now the thing the detected
    communities are measured against: a community holding `board-deck-builder`,
    `email-template-builder` and `helm-chart-builder` spans three declared domains, and
    the interesting part of the page is that disagreement rather than either side of it.
    """
    data = json.loads((site_dir / "domains.json").read_text(encoding="utf-8"))
    cat_to_domain = {}
    for d in data["domains"]:
        for c in d["categories"]:
            cat_to_domain[c] = d["id"]
    return {
        "domains": data["domains"],
        "cat_to_domain": cat_to_domain,
        "labels": data["categories"],
        "titles": {d["id"]: d["label"] for d in data["domains"]},
    }


def agreement(comm: dict, rows: list, spec: dict, degree: dict = None) -> dict:
    """Majority-label purity of the detected communities against the declared domains.

    Not "agreement", which is what this was called and what it is not. A detected community
    has no domain label of its own; this assigns it whichever declared domain its members
    are most often filed under, then counts the members in that majority. That is purity
    measured after seeing the answer, and it can only ever flatter the clustering.

    A review was right to object to the earlier framing on two counts. Calling it agreement
    implied the two labellings were compared independently, which is impossible. And every
    isolated skill is its own single-member community, so it scores a point automatically —
    45 free points out of 490. Both numbers are now reported separately: `linked` excludes
    single-member communities, and `automatic` says how many of the points were free.

    Purity means nothing on its own, so `nmi` reports normalised mutual information between
    the two labellings as well. That one is symmetric, needs no majority assignment, and is
    0 when the two are independent and 1 when either determines the other — so it cannot be
    inflated by having many small communities, which is exactly how purity can be.

    A first attempt at a baseline here was worse than no baseline: it filled the same
    community sizes from a domain-sorted list, which is the best case rather than the
    uninformed one, and duly scored higher than the real clustering. It is gone.
    """
    by_key = {r["key"]: r for r in rows}
    degree = degree or {}
    per_comm = collections.defaultdict(collections.Counter)
    for key, cid in sorted(comm.items()):
        per_comm[cid][spec["cat_to_domain"][by_key[key]["dom"]]] += 1

    def purity(counter: collections.Counter) -> int:
        # Sorted rather than most_common: a community split evenly between two declared
        # domains is a tie, and a tie broken by insertion order is broken by the hash seed.
        return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][1]

    pure = 0
    linked_pure = 0
    linked_total = 0
    spanning = 0
    automatic = 0
    for cid, counts in sorted(per_comm.items()):
        size = sum(counts.values())
        pure += purity(counts)
        if size == 1:
            automatic += 1
        else:
            linked_pure += purity(counts)
            linked_total += size
        if len(counts) > 1:
            spanning += 1

    # Normalised mutual information, symmetric, on the whole library. Zero if the detected
    # communities say nothing about the declared domains, one if either determines the other.
    n = len(comm) or 1
    dom_totals = collections.Counter()
    for counts in per_comm.values():
        dom_totals.update(counts)
    mutual = 0.0
    for counts in per_comm.values():
        csize = sum(counts.values())
        for dom, joint in counts.items():
            mutual += (joint / n) * math.log(
                (joint / n) / ((csize / n) * (dom_totals[dom] / n))
            )

    def entropy(counter):
        return -sum(
            (v / n) * math.log(v / n) for v in counter.values() if v
        )

    h_comm = entropy(
        collections.Counter({c: sum(v.values()) for c, v in per_comm.items()})
    )
    h_dom = entropy(dom_totals)
    nmi = 0.0 if h_comm <= 0 or h_dom <= 0 else mutual / math.sqrt(h_comm * h_dom)

    return {
        "pure": pure,
        "total": len(comm),
        "linked_pure": linked_pure,
        "linked_total": linked_total,
        "automatic": automatic,
        "nmi": round(nmi, 3),
        "spanning": spanning,
        "communities": len(per_comm),
    }


# ---------------------------------------------------------------------- labelling

# The advance width of each character, as a fraction of the font size, measured in a browser
# against the page's actual body face and pasted here.
#
# This started as one average number, 0.505 per character. An average is fine for a long name
# and badly wrong for a short one: measured against the real labels, the widest were
# under-estimated by 42%, and a skill name was placed against a community-name box a fifth
# narrower than the label actually drawn. Two names overlapped on the page's opening state.
#
# Raising the average to the worst case would have over-reserved every long name by 40% and
# dropped most of them. A table costs twenty lines and predicts every label on the page to
# within 0.01%, which was checked by comparing it with getComputedTextLength for all 508
# labels. Regenerate it the same way if the face changes.
CHAR_W = {
    ' ': 0.0, '&': 0.5749, '(': 0.4312, ')': 0.4312, '+': 0.7187, ',': 0.2875,
    '-': 0.4312, '.': 0.2875, '/': 0.4312, '0': 0.5749, '1': 0.4312, '2': 0.5749,
    '3': 0.5749, '4': 0.5749, '5': 0.5749, '6': 0.5749, '7': 0.5749, '8': 0.5749,
    '9': 0.5749, 'A': 0.7187, 'B': 0.7187, 'C': 0.7187, 'D': 0.7187, 'E': 0.5749,
    'F': 0.5749, 'G': 0.7187, 'H': 0.7187, 'I': 0.2875, 'J': 0.5749, 'K': 0.7187,
    'L': 0.5749, 'M': 0.8624, 'N': 0.7187, 'O': 0.7187, 'P': 0.5749, 'Q': 0.7187,
    'R': 0.5749, 'S': 0.5749, 'T': 0.5749, 'U': 0.7187, 'V': 0.7187, 'W': 1.0062,
    'X': 0.7187, 'Y': 0.7187, 'Z': 0.5749, 'a': 0.5749, 'b': 0.5749, 'c': 0.5749,
    'd': 0.5749, 'e': 0.5749, 'f': 0.4312, 'g': 0.5749, 'h': 0.5749, 'i': 0.2875,
    'j': 0.2875, 'k': 0.5749, 'l': 0.2875, 'm': 0.8624, 'n': 0.5749, 'o': 0.5749,
    'p': 0.5749, 'q': 0.5749, 'r': 0.4312, 's': 0.5749, 't': 0.2875, 'u': 0.5749,
    'v': 0.5749, 'w': 0.8624, 'x': 0.5749, 'y': 0.5749, 'z': 0.5749, '·': 0.2875,
}
# Anything outside the table: wider than any real character, so an unknown glyph reserves too
# much space rather than too little.
CHAR_W_FALLBACK = 0.62

LABEL_FONT = 9.5
COMMUNITY_FONT = 11.5
# Measured from getBBox in a browser, not derived from the font size: a 9.5px label
# occupies 12.4 user units vertically, 9.4 above the baseline and 2.9 below. Deriving it
# from the font size gave 10.4, and every collision that survived the first version of
# this placer overlapped by about the missing two units.
LABEL_H = 12.4


def label_box(
    name: str, x: float, y: float, anchor: str, font: float = LABEL_FONT
) -> tuple:
    """The rectangle a label occupies, so collisions can be tested before drawing.

    `font` matters: the community names are drawn larger than the skill names, and computing
    both at the smaller size reserved the community boxes a fifth too narrow.
    """
    w = font * sum(CHAR_W.get(c, CHAR_W_FALLBACK) for c in name)
    if anchor == "start":
        x0 = x
    elif anchor == "end":
        x0 = x - w
    else:
        x0 = x - w / 2
    h = LABEL_H * font / LABEL_FONT
    return (x0, y - h * 0.78, x0 + w, y + h * 0.22)


def _overlaps(a: tuple, b: tuple, gap: float = 1.4) -> bool:
    return (
        a[0] < b[2] + gap
        and b[0] < a[2] + gap
        and a[1] < b[3] + gap
        and b[1] < a[3] + gap
    )


def place_community_labels(
    order: list,
    labels: dict,
    members: dict,
    pos: dict,
    want: int,
    frame: tuple = (0.0, 0.0, FRAME[0], FRAME[1]),
) -> dict:
    """Place the community names so that none of them collide with each other.

    These were previously written at a fixed offset above each community and merely
    *reserved* against the skill names, which are placed afterwards. Reserved is not the
    same as checked: the boxes were never tested against one another, and once tightening the
    edge rules split the library into 31 communities instead of 19, two of the names
    overlapped. Largest community first, four candidate positions each, and a name with
    nowhere to go is not drawn rather than drawn on top of another one.
    """
    placed = {}
    boxes = []
    for cid in order:
        if len(placed) >= want:
            break
        mine = members[cid]
        label = labels[cid]
        cx = sum(pos[m][0] for m in mine) / len(mine)
        top = min(pos[m][1] for m in mine)
        bottom = max(pos[m][1] for m in mine)
        options = [
            (cx, top - 9.0),
            (cx, bottom + 17.0),
            (cx, top - 21.0),
            (cx, bottom + 29.0),
        ]
        for ox, oy in options:
            box = label_box(label, ox, oy, "middle", font=COMMUNITY_FONT)
            if box[0] < frame[0] or box[2] > frame[2]:
                continue
            if box[1] < frame[1] or box[3] > frame[3]:
                continue
            if any(_overlaps(box, other, gap=2.4) for other in boxes):
                continue
            placed[cid] = {"x": round(ox, 1), "y": round(oy, 1), "box": box}
            boxes.append(box)
            break
    return placed


def place_labels(
    ranked: list,
    names: dict,
    pos: dict,
    radius: dict,
    want: int,
    frame: tuple = (0.0, 0.0, FRAME[0], FRAME[1]),
    reserved: list = None,
) -> dict:
    """Choose which names to draw unasked, and where, so that none of them collide.

    Drawing the twenty-six most connected skills at a fixed offset from their own node
    produced an unreadable pile: in the densest community nine names landed on top of
    each other and the result was a grey smudge with no word in it. This is the same
    fault an earlier version of this page shipped and an independent review caught, so it
    is worth being explicit about the fix.

    Each candidate is offered four positions around its node, in order of preference, and
    is drawn only if one of them clears every label already placed and stays inside the
    frame. A name that cannot be placed is not drawn: it is still in the document, at zero
    opacity, and appears when something asks for it. Fewer names, all readable, beats
    more names none of which are.
    """
    placed = {}
    boxes = list(reserved or [])
    for key in ranked:
        if len(placed) >= want:
            break
        name = names[key]
        x, y = pos[key]
        r = radius.get(key, 3.0)
        options = [
            (x + r + 4, y + 3.2, "start"),
            (x - r - 4, y + 3.2, "end"),
            (x, y - r - 5.0, "middle"),
            (x, y + r + 10.4, "middle"),
        ]
        for ox, oy, anchor in options:
            box = label_box(name, ox, oy, anchor)
            if box[0] < frame[0] or box[2] > frame[2]:
                continue
            if box[1] < frame[1] or box[3] > frame[3]:
                continue
            if any(_overlaps(box, other) for other in boxes):
                continue
            placed[key] = {
                "x": round(ox, 1),
                "y": round(oy, 1),
                "anchor": anchor,
                "box": box,
            }
            boxes.append(box)
            break
    return placed
