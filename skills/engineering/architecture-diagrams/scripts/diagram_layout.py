"""Deterministic layout for diagram documents.

Turns a validated IR document into positioned geometry the renderer can emit as
SVG. Pure standard library, and deterministic: the same input always produces
byte-identical output, which is what makes the golden tests in `tests/` and the
`--check` mode of the renderer meaningful.

Two layouts live here.

`layout_graph` handles architecture, workflow, dataflow and lifecycle. It is a
layered (Sugiyama-style) layout, cut down to the parts that matter at the scale a
hand-authored diagram reaches:

  1. break cycles, so a lifecycle state machine with a retry loop still ranks
  2. rank by longest path, so an edge always points forward
  3. order within each rank by barycentre to reduce crossings
  4. keep group members adjacent, so a group boundary is a tight box rather than
     a rectangle swallowing half the diagram
  5. assign coordinates and route edges

`layout_sequence` handles sequence diagrams as participants over lifelines.

Text is measured by approximation. There are no font metrics in the standard
library, so glyph width is estimated as a fraction of the font size. The
estimate is deliberately generous: a slightly roomy box is invisible, whereas a
tight one clips its own label.
"""

from __future__ import annotations

# ---------------------------------------------------------------- geometry
NODE_W = 208
NODE_PAD_X = 16
NODE_MIN_H = 60
LINE_H = 19
NOTE_LINE_H = 16
RANK_GAP = 104
NODE_GAP = 26
MARGIN = 56

GROUP_PAD = 24
GROUP_HEADER = 30

LANE_W = 200
LANE_BOX_W = 168
LANE_BOX_H = 56
MSG_GAP = 68
SEQ_SELF_GAP = 82
SEQ_TOP = 40
SEQ_FIRST_MSG = 74

LABEL_FS = 14
NOTE_FS = 12
# Average glyph width as a fraction of font size for the UI stack in theme.css.
GLYPH = 0.58


def text_width(text, font_size=LABEL_FS):
    return len(text) * font_size * GLYPH


def _hard_break(word, max_px, font_size):
    """Split a token that cannot fit on one line at any width.

    Necessary rather than nice to have. Refusing to split meant a long
    identifier, a URI, or any CJK string (which has no spaces to wrap at)
    rendered as a single line far wider than the node: a 1,000-character label
    measured 9,153px inside a 208px box, overflowing by ~4,470px on each side and
    being clipped at the fit and print boundaries.
    """
    if text_width(word, font_size) <= max_px:
        return [word]
    per_char = max(1, int(max_px // (font_size * GLYPH)))
    return [word[i : i + per_char] for i in range(0, len(word), per_char)] or [word]


def wrap(text, max_px, font_size=LABEL_FS):
    """Greedy word wrap to a pixel budget, hard-breaking tokens that cannot fit."""
    words = str(text).split()
    if not words:
        return [""]
    lines, cur = [], ""
    for word in words:
        for piece in _hard_break(word, max_px, font_size):
            candidate = (cur + " " + piece) if cur else piece
            if text_width(candidate, font_size) <= max_px:
                cur = candidate
            else:
                if cur:
                    lines.append(cur)
                cur = piece
    if cur:
        lines.append(cur)
    return lines or [""]


ACTOR_HEAD = 34


def _node_box(node):
    inner = NODE_W - 2 * NODE_PAD_X
    label_lines = wrap(node["label"], inner, LABEL_FS)
    note_lines = wrap(node["note"], inner, NOTE_FS) if node.get("note") else []
    tech = node.get("tech")
    height = 22 + len(label_lines) * LINE_H
    if note_lines:
        height += 6 + len(note_lines) * NOTE_LINE_H
    if tech:
        height += 18
    height += 18
    # The actor shape draws a head above its body, so the body must start lower
    # or the head sits on top of the label.
    if node.get("shape") == "actor":
        height += ACTOR_HEAD
    return label_lines, note_lines, max(NODE_MIN_H, height)


# ------------------------------------------------------------- graph layout
def _back_edges(node_ids, edges):
    """Identify edges that close a cycle, by DFS colouring.

    Ranking needs a DAG. Rather than refusing cyclic input, the back edges are
    set aside for ranking and drawn differently, so a retry loop or a state
    machine reads as a loop instead of failing to lay out.
    """
    adj = {n: [] for n in node_ids}
    for i, e in enumerate(edges):
        adj[e["from"]].append((e["to"], i))

    WHITE, GREY, BLACK = 0, 1, 2
    colour = {n: WHITE for n in node_ids}
    back = set()

    for root in node_ids:
        if colour[root] != WHITE:
            continue
        # Explicit stack: a deep chain should not blow the interpreter's.
        stack = [(root, iter(adj[root]))]
        colour[root] = GREY
        while stack:
            node, it = stack[-1]
            advanced = False
            for target, idx in it:
                if colour[target] == GREY:
                    back.add(idx)
                elif colour[target] == WHITE:
                    colour[target] = GREY
                    stack.append((target, iter(adj[target])))
                    advanced = True
                    break
            if not advanced:
                colour[node] = BLACK
                stack.pop()
    return back


def _ranks(node_ids, edges, back):
    """Longest-path ranking over the acyclic subgraph."""
    preds = {n: [] for n in node_ids}
    succs = {n: [] for n in node_ids}
    for i, e in enumerate(edges):
        if i in back:
            continue
        preds[e["to"]].append(e["from"])
        succs[e["from"]].append(e["to"])

    rank = {n: 0 for n in node_ids}
    indeg = {n: len(preds[n]) for n in node_ids}
    queue = [n for n in node_ids if indeg[n] == 0]
    seen = 0
    while queue:
        node = queue.pop(0)
        seen += 1
        for target in succs[node]:
            rank[target] = max(rank[target], rank[node] + 1)
            indeg[target] -= 1
            if indeg[target] == 0:
                queue.append(target)
    return rank, preds, succs


def _order(by_rank, preds, succs, group_of):
    """Reduce crossings by barycentre, then pull group members together.

    Group cohesion is applied last and wins ties, because a group drawn as a
    tight boundary communicates more than a marginally lower crossing count.
    """
    pos = {}
    for nodes in by_rank.values():
        for i, n in enumerate(nodes):
            pos[n] = i

    for _ in range(4):
        for direction in ("down", "up"):
            keys = sorted(by_rank) if direction == "down" else sorted(by_rank, reverse=True)
            for r in keys:
                neighbours = preds if direction == "down" else succs
                def bary(n):
                    linked = [pos[m] for m in neighbours[n] if m in pos]
                    return sum(linked) / len(linked) if linked else pos[n]
                by_rank[r].sort(key=lambda n: (group_of.get(n, -1), bary(n)))
                for i, n in enumerate(by_rank[r]):
                    pos[n] = i
    return by_rank


def layout_graph(doc):
    orientation = doc.get("orientation", "LR")
    nodes = doc["nodes"]
    edges = list(doc.get("edges", []))
    node_ids = [n["id"] for n in nodes]
    by_id = {n["id"]: n for n in nodes}

    group_of = {}
    for gi, group in enumerate(doc.get("groups", [])):
        for member in group["nodes"]:
            group_of[member] = gi

    back = _back_edges(node_ids, edges)
    rank, preds, succs = _ranks(node_ids, edges, back)

    by_rank = {}
    for n in node_ids:
        by_rank.setdefault(rank[n], []).append(n)
    by_rank = _order(by_rank, preds, succs, group_of)

    # Boxes
    boxes = {}
    for n in node_ids:
        label_lines, note_lines, h = _node_box(by_id[n])
        boxes[n] = {"label_lines": label_lines, "note_lines": note_lines, "w": NODE_W, "h": h}

    # ---------------------------------------------------------------- bands
    # Groups are laid out as swimlanes rather than as bounding boxes drawn over
    # a free layout. Free layout lets a group span several ranks while another
    # group occupies the same vertical space, and the two boundary rectangles
    # then overlap and become unreadable. Confining each group to its own band
    # of the cross axis makes overlap structurally impossible: a group's box can
    # only ever extend horizontally, along the ranks it actually occupies.
    groups_in = doc.get("groups", [])
    band_of = {}
    bands = []
    if groups_in:
        # Order the bands by where their members first appear in the flow, so
        # reading top to bottom roughly follows the direction of travel.
        order_key = {}
        for gi, group in enumerate(groups_in):
            order_key[gi] = min(rank[m] for m in group["nodes"])
        for gi in sorted(order_key, key=lambda g: (order_key[g], g)):
            bands.append(("group", gi))
        ungrouped = [n for n in node_ids if n not in group_of]
        if ungrouped:
            bands.append(("loose", None))
        for bi, (btype, gi) in enumerate(bands):
            members = groups_in[gi]["nodes"] if btype == "group" else ungrouped
            for m in members:
                band_of[m] = bi
    else:
        bands = [("loose", None)]
        for n in node_ids:
            band_of[n] = 0

    # Per (band, rank) stacks, ordered by the crossing-reduced order.
    stacks = {}
    for r in sorted(by_rank):
        for n in by_rank[r]:
            stacks.setdefault((band_of[n], r), []).append(n)

    # The cross-axis size of a box is its height under LR and its width under TB.
    # Using the height in both directions made every TB rank advance by ~86px
    # while the boxes are 208px wide, so neighbours overlapped by 122px.
    def cross(node_id):
        return boxes[node_id]["w"] if orientation == "TB" else boxes[node_id]["h"]

    # Each band is as deep as its fullest rank, plus a header when it is a group.
    band_height = {}
    for bi in range(len(bands)):
        tallest = 0
        for r in sorted(by_rank):
            members = stacks.get((bi, r), [])
            if members:
                extent = sum(cross(m) for m in members) + NODE_GAP * (len(members) - 1)
                tallest = max(tallest, extent)
        header = GROUP_HEADER if bands[bi][0] == "group" else 0
        band_height[bi] = tallest + header + (2 * GROUP_PAD if header else 0)

    band_top = {}
    cursor = MARGIN
    for bi in range(len(bands)):
        band_top[bi] = cursor
        cursor += band_height[bi] + (NODE_GAP + GROUP_PAD if bands[bi][0] == "group" else NODE_GAP)

    placed = {}
    for (bi, r), members in stacks.items():
        header = GROUP_HEADER + GROUP_PAD if bands[bi][0] == "group" else 0
        inner_h = band_height[bi] - header - (GROUP_PAD if bands[bi][0] == "group" else 0)
        extent = sum(cross(m) for m in members) + NODE_GAP * (len(members) - 1)
        along = band_top[bi] + header + (inner_h - extent) / 2
        for m in members:
            # Rank spacing must clear the box's own extent along the rank axis,
            # which is the height under TB and the fixed width under LR.
            rank_step = (
                (max(boxes[k]["h"] for k in node_ids) + RANK_GAP)
                if orientation == "TB"
                else (NODE_W + RANK_GAP)
            )
            across = MARGIN + r * rank_step
            placed[m] = (across, along) if orientation == "LR" else (along, across)
            along += cross(m) + NODE_GAP

    out_nodes = []
    for n in node_ids:
        node = by_id[n]
        x, y = placed[n]
        box = boxes[n]
        out_nodes.append(
            {
                "id": n,
                "x": round(x, 2),
                "y": round(y, 2),
                "w": box["w"],
                "h": box["h"],
                "label_lines": box["label_lines"],
                "note_lines": box["note_lines"],
                "tech": node.get("tech"),
                "shape": node.get("shape", "box"),
                "accent": node.get("accent"),
                "rank": rank[n],
                "group": group_of.get(n),
            }
        )
    pos = {n["id"]: n for n in out_nodes}

    # Group boxes, confined to their band.
    out_groups = []
    for gi, group in enumerate(groups_in):
        members = [pos[m] for m in group["nodes"]]
        x0 = min(m["x"] for m in members) - GROUP_PAD
        y0 = min(m["y"] for m in members) - GROUP_PAD - GROUP_HEADER
        x1 = max(m["x"] + m["w"] for m in members) + GROUP_PAD
        y1 = max(m["y"] + m["h"] for m in members) + GROUP_PAD
        out_groups.append(
            {
                "label": group["label"],
                "x": round(x0, 2),
                "y": round(y0, 2),
                "w": round(x1 - x0, 2),
                "h": round(y1 - y0, 2),
                "index": gi,
            }
        )

    # ---------------------------------------------------------------- edges
    # Back edges are routed through a reserved strip clear of every node rather
    # than bowed just above their own endpoints. Bowing locally puts the edge and
    # its label on top of whatever happens to sit above it, which is how the
    # "status callback" label ended up hidden behind a node.
    content_min = min(n["y"] for n in out_nodes) if orientation == "LR" else min(
        n["x"] for n in out_nodes
    )
    back_list = [i for i in range(len(edges)) if i in back]
    strip = {idx: content_min - 40 - 24 * k for k, idx in enumerate(back_list)}

    # Edges sharing a pair of endpoints would otherwise trace the same curve and
    # stack their labels in the same place, so they are fanned apart.
    pair_count = {}
    for edge in edges:
        key = (edge["from"], edge["to"])
        pair_count[key] = pair_count.get(key, 0) + 1
    pair_seen = {}

    out_edges = []
    for i, edge in enumerate(edges):
        a, b = pos[edge["from"]], pos[edge["to"]]
        is_back = i in back
        key = (edge["from"], edge["to"])
        k = pair_seen.get(key, 0)
        pair_seen[key] = k + 1
        # Centre the fan on the direct route: one edge is undeflected.
        fan = 0.0
        if pair_count[key] > 1:
            fan = (k - (pair_count[key] - 1) / 2) * 34.0
        path, lx, ly = _edge_path(a, b, orientation, is_back, strip.get(i), fan)
        out_edges.append(
            {
                "from": edge["from"],
                "to": edge["to"],
                "path": path,
                "label": edge.get("label"),
                "lx": round(lx, 2),
                "ly": round(ly, 2),
                "style": edge.get("style", "dashed" if is_back else "solid"),
                "back": is_back,
                "accent": edge.get("accent"),
            }
        )

    xs = [n["x"] for n in out_nodes] + [g["x"] for g in out_groups]
    ys = [n["y"] for n in out_nodes] + [g["y"] for g in out_groups]
    x2 = [n["x"] + n["w"] for n in out_nodes] + [g["x"] + g["w"] for g in out_groups]
    y2 = [n["y"] + n["h"] for n in out_nodes] + [g["y"] + g["h"] for g in out_groups]
    if strip:
        lo = min(strip.values()) - 18
        (ys if orientation == "LR" else xs).append(lo)

    pad = 28
    return {
        "kind": doc["kind"],
        "orientation": orientation,
        "nodes": out_nodes,
        "edges": out_edges,
        "groups": out_groups,
        "min_x": round(min(xs) - pad, 2),
        "min_y": round(min(ys) - pad, 2),
        "width": round(max(x2) - min(xs) + 2 * pad, 2),
        "height": round(max(y2) - min(ys) + 2 * pad, 2),
    }


def _edge_path(a, b, orientation, is_back, strip=None, fan=0.0):
    """Cubic bezier between two boxes.

    Back edges travel through a reserved strip that no node occupies. The legs
    from each endpoint up to that strip are straight cubics and are NOT routed
    around intervening boxes, so on a dense graph a back edge can still cross an
    unrelated node. This is a known limitation, stated in SKILL.md rather than
    papered over.
    """
    if a is b:
        # A self-loop needs a visible loop, not a zero-length curve.
        x, y = a["x"] + a["w"] / 2, a["y"]
        return (
            f"M {x - 24:.1f} {y:.1f} C {x - 40:.1f} {y - 56:.1f} "
            f"{x + 40:.1f} {y - 56:.1f} {x + 24:.1f} {y:.1f}",
            x,
            y - 44,
        )
    if orientation == "LR":
        sx, sy = a["x"] + a["w"], a["y"] + a["h"] / 2
        tx, ty = b["x"], b["y"] + b["h"] / 2
        if is_back:
            # Runs right-to-left: leave and enter on the same side, travel above.
            sx, tx = a["x"], b["x"] + b["w"]
            bow = strip if strip is not None else min(a["y"], b["y"]) - 46
            path = f"M {sx:.1f} {sy:.1f} C {sx - 60:.1f} {bow:.1f} {tx + 60:.1f} {bow:.1f} {tx:.1f} {ty:.1f}"
            return path, (sx + tx) / 2, bow - 6
        dx = max(40.0, (tx - sx) * 0.5)
        path = (
            f"M {sx:.1f} {sy:.1f} C {sx + dx:.1f} {sy + fan:.1f} "
            f"{tx - dx:.1f} {ty + fan:.1f} {tx:.1f} {ty:.1f}"
        )
        return path, (sx + tx) / 2, (sy + ty) / 2 - 8 + fan * 0.75
    sx, sy = a["x"] + a["w"] / 2, a["y"] + a["h"]
    tx, ty = b["x"] + b["w"] / 2, b["y"]
    if is_back:
        sx, sy = a["x"] + a["w"] / 2, a["y"]
        ty = b["y"] + b["h"]
        bow = strip if strip is not None else min(a["x"], b["x"]) - 46
        path = f"M {sx:.1f} {sy:.1f} C {bow:.1f} {sy - 60:.1f} {bow:.1f} {ty + 60:.1f} {tx:.1f} {ty:.1f}"
        return path, bow + 4, (sy + ty) / 2
    dy = max(40.0, (ty - sy) * 0.5)
    path = (
        f"M {sx:.1f} {sy:.1f} C {sx + fan:.1f} {sy + dy:.1f} "
        f"{tx + fan:.1f} {ty - dy:.1f} {tx:.1f} {ty:.1f}"
    )
    return path, (sx + tx) / 2 + 8 + fan * 0.75, (sy + ty) / 2


# ---------------------------------------------------------- sequence layout
def layout_sequence(doc):
    parts = doc["participants"]
    messages = doc["messages"]

    # Lane boxes are sized from their content and then equalised, so every
    # lifeline starts at the same y. Sizing them to a fixed constant is what put
    # the actor participant's label outside its own box: the actor shape draws a
    # head above its body, which a fixed height does not account for.
    measured = []
    for part in parts:
        label_lines = wrap(part["label"], LANE_BOX_W - 24, LABEL_FS)
        # The note is part of the documented contract, so it must be measured
        # here or it will be rendered outside the box it belongs to.
        note_lines = wrap(part["note"], LANE_BOX_W - 24, NOTE_FS) if part.get("note") else []
        h = 22 + len(label_lines) * LINE_H + 18
        if note_lines:
            h += 6 + len(note_lines) * NOTE_LINE_H
        if part.get("shape") == "actor":
            h += ACTOR_HEAD
        measured.append((part, label_lines, note_lines, max(LANE_BOX_H, h)))
    box_h = max(h for _, _, _, h in measured)

    lanes = []
    for i, (part, label_lines, note_lines, _) in enumerate(measured):
        x = MARGIN + i * LANE_W
        lanes.append(
            {
                "id": part["id"],
                "label_lines": label_lines,
                "x": round(x, 2),
                "cx": round(x + LANE_BOX_W / 2, 2),
                "w": LANE_BOX_W,
                "h": box_h,
                "shape": part.get("shape", "box"),
                "note": part.get("note"),
                "note_lines": note_lines,
            }
        )
    cx = {lane["id"]: lane["cx"] for lane in lanes}

    out = []
    y = SEQ_TOP + box_h + SEQ_FIRST_MSG
    for i, msg in enumerate(messages):
        a, b = cx[msg["from"]], cx[msg["to"]]
        self_call = msg["from"] == msg["to"]
        out.append(
            {
                "index": i + 1,
                "from": msg["from"],
                "to": msg["to"],
                "x1": a,
                "x2": b,
                "y": round(y, 2),
                "self": self_call,
                "label": msg.get("label"),
                "style": msg.get("style", "solid"),
                "note": msg.get("note"),
                "accent": msg.get("accent"),
            }
        )
        # A self-call occupies a loop, not a line, so it needs its own vertical
        # budget or the next message's label lands on top of the loop's.
        y += SEQ_SELF_GAP if self_call else MSG_GAP
        if msg.get("note"):
            y += 30

    bottom = y + 30
    return {
        "kind": "sequence",
        "orientation": "TB",
        "lanes": lanes,
        "messages": out,
        "lifeline_top": SEQ_TOP + box_h,
        "lifeline_bottom": round(bottom, 2),
        "min_x": 0,
        "min_y": 0,
        "width": round(MARGIN * 2 + max(1, len(parts)) * LANE_W, 2),
        "height": round(bottom + MARGIN, 2),
    }


def layout(doc):
    return layout_sequence(doc) if doc["kind"] == "sequence" else layout_graph(doc)
