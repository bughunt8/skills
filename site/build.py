#!/usr/bin/env python3
"""Build the skill-browser page from its source repositories.

Why this exists: the first version of this page built every card in
JavaScript. That produced a page with 858 characters of text for a crawler and
nothing at all with JS disabled, which is the wrong architecture for a public,
indexable page. Every card is now prerendered into index.html at build time and
JavaScript only attaches motion to markup that is already there.

    build.py --check   verify index.html matches the sources (used by CI)
    build.py --write   regenerate index.html and data.js
    build.py --refresh clone the upstreams fresh, then write

Standard library only, so CI needs nothing installed.

Exit codes
    0  generated output matches the sources (--check) or was written (--write)
    1  index.html is stale, or a source is missing
    2  usage or environment error
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import compose
import network

ROOT = Path(__file__).resolve().parent
# The repository that contains this site. Its own skills are read from here.
REPO_ROOT = ROOT.parent
INDEX = ROOT / "index.html"
DATA = ROOT / "data.js"
SOURCES = ROOT / "sources.json"

MARKERS = {
    "main": (
        "<!-- BEGIN GENERATED: main (build.py) -- do not edit by hand -->",
        "<!-- END GENERATED: main -->",
    ),
    "credits": (
        "<!-- BEGIN GENERATED: credits (build.py) -- do not edit by hand -->",
        "<!-- END GENERATED: credits -->",
    ),
}

# Human labels for directory names. A category with no entry falls back to its
# directory name, which is visible and therefore self-correcting.
LABELS = {
    "engineering": "Engineering",
    "c-level-advisor": "C-level advisory",
    "engineering-team": "Engineering team",
    "marketing-skill": "Marketing",
    "pstack": "Engineering rigor",
    "design": "Design",
    "creative-writing": "Creative writing",
    "productivity": "Productivity",
    "product-team": "Product",
    "ra-qm-team": "Regulatory and quality",
    "job-hunt": "Job search",
    "compliance-os": "Compliance",
    "project-management": "Project management",
    "commercial": "Commercial",
    "research": "Research",
    "business-operations": "Business operations",
    "business-growth": "Business growth",
    "markdown-html": "Markdown and HTML",
    "research-ops": "Research ops",
    "shuohao": "Short-drama production",
    "finance": "Finance",
    "loop-library": "Agent loops",
    "start-github-repo": "Repo scaffolding",
    "marketing": "Landing pages",
}

SKIP_NAMES = {"sample-skill"}  # a test fixture, not a skill


def fail(msg: str, code: int = 2):
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def load_sources() -> list:
    if not SOURCES.exists():
        fail(f"missing {SOURCES}")
    return json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]


def frontmatter(path: Path) -> "tuple[str, str]":
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---", text, re.S)
    name = desc = None
    if match:
        block = match.group(1)
        for key in ("name", "description"):
            m = re.search(rf"^{key}:[ \t]*(.*)$", block, re.M)
            if m:
                value = m.group(1).strip().strip("\"'")
                if key == "name":
                    name = value
                else:
                    desc = value
    return (name or path.parent.name), re.sub(r"\s+", " ", desc or "").strip()


def trim(text: str, limit: int = 170) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stop = cut.rfind(". ")
    return cut[: stop + 1] if stop > 90 else cut.rstrip() + "..."


def collect(checkouts: dict) -> list:
    rows = []
    # Every duplicate the build removes, so a collapse is visible in the log
    # rather than being a number that quietly does not add up.
    collapsed = []
    for src in load_sources():
        root = checkouts[src["id"]]
        if src.get("subpath"):
            root = root / src["subpath"]
        if not root.is_dir():
            fail(f"[{src['id']}] path not found: {root}")

        found = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            if "SKILL.md" in filenames:
                found.append(Path(dirpath) / "SKILL.md")
        # Shallowest path wins, so a repo that mirrors the same skill into two
        # directories contributes it once.
        found.sort(key=lambda p: (len(p.parts), str(p)))

        seen = {}
        for path in found:
            name, desc = frontmatter(path)
            if name in SKIP_NAMES:
                continue
            parts = Path(os.path.relpath(path.parent, root)).parts
            if src.get("flat_category"):
                category = src["flat_category"]
            else:
                category = parts[0] if parts and parts[0] != "." else "core"

            # The bundle a skill belongs to: the path between its category and
            # itself, with the conventional "skills" segment dropped. Used to tell
            # two same-named skills apart on the page.
            middle = [seg for seg in parts[1:-1] if seg != "skills"]
            bundle = "/".join(middle)

            # Dedupe on the CONTENT of SKILL.md, not on its name.
            #
            # Name-based dedupe cannot tell a mirror from a namesake, and it got
            # this wrong in both directions. Globally it dropped genuinely
            # different skills that shared a name across categories. Scoped to the
            # category it still collapsed engineering/agenthub/run with
            # engineering/autoresearch-agent/run, which are different skills whose
            # SKILL.md files differ, while the pairs it was designed to collapse
            # are byte-identical. Hashing the file collapses exactly the mirrors
            # and nothing else, which is verifiable rather than a guess.
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in seen:
                collapsed.append((src["repo"], category, name, str(path), seen[digest]))
                continue
            seen[digest] = str(path)

            rows.append(
                {
                    "n": name,
                    "d": trim(desc),
                    "dom": category,
                    "repo": src["repo"],
                    "lic": src["license"],
                    "url": src["url"],
                    "bundle": bundle,
                    # Identity, not display. Carried through composition, layout,
                    # every DOM node and every graph edge. Using the name here meant
                    # agenthub's `init` edge terminated on playwright-pro's `init`
                    # node, and the two distinct `run` skills were drawn as one.
                    "key": f"{category}~{bundle}~{name}",
                }
            )

    # Two distinct skills can legitimately share a name, for example the `run`
    # command of two different agent bundles. Qualify those on the page so a
    # reader can tell them apart, and leave every unique name clean.
    by_key = collections.Counter((r["dom"], r["n"]) for r in rows)
    for r in rows:
        r["qual"] = r["bundle"] if by_key[(r["dom"], r["n"])] > 1 and r["bundle"] else ""
    qualified = sum(1 for r in rows if r["qual"])
    if qualified:
        print(f"qualified {qualified} skill(s) that share a name within a category:")
        for r in rows:
            if r["qual"]:
                print(f"  {r['dom']}/{r['n']}  ->  shown as \"{r['n']} ({r['qual']})\"")

    # The identity must actually identify. If this ever fails, composition and the
    # graph would silently fuse two different skills, which is the defect this key
    # exists to prevent, so it fails the build rather than degrading quietly.
    seen_keys = {}
    for r in rows:
        if r["key"] in seen_keys:
            fail(
                f"identity collision: {r['key']!r} is used by two skills\n"
                f"  {seen_keys[r['key']]}\n  {r['repo']}/{r['dom']}/{r['n']}\n"
                "The (category, bundle, name) key must be unique."
            )
        seen_keys[r["key"]] = f"{r['repo']}/{r['dom']}/{r['n']}"

    if collapsed:
        print(f"collapsed {len(collapsed)} byte-identical duplicate(s):")
        for repo, category, name, dupe, kept in collapsed:
            print(f"  [{repo}] {category}/{name}")
            print(f"      kept    {kept}")
            print(f"      dropped {dupe}")
    return rows


def resolve_tip(url: str) -> str:
    """The commit the upstream default branch currently points at."""
    out = subprocess.run(
        ["git", "ls-remote", url + ".git", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    if not out:
        fail(f"could not resolve HEAD for {url}")
    return out[0]


def repin() -> None:
    """Move every external pin in sources.json to the current upstream tip.

    The host repository has no pin to move: it is read from the working tree.
    """
    cfg = json.loads(SOURCES.read_text(encoding="utf-8"))
    for src in cfg["sources"]:
        if src.get("local"):
            continue
        tip = resolve_tip(src["url"])
        if src.get("ref") != tip:
            print(f"  {src['repo']}: {src.get('ref', '<unpinned>')[:12]} -> {tip[:12]}")
        src["ref"] = tip
    SOURCES.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def fetch() -> dict:
    """Resolve every source to a directory. Returns {source id: path}.

    The host repository is used in place. External repositories are always cloned
    at their pinned commit rather than reusing a sibling working copy: a sibling
    checkout is whatever the last person left it at, and building from one is how
    the committed page came to disagree with its sources: CI cloned upstream HEAD,
    a laptop used a stale local clone, and the two produced different pages.
    """
    checkouts = {}
    tmp = Path(tempfile.mkdtemp(prefix="skill-src-"))
    for src in load_sources():
        if src.get("local"):
            # The host repository, read in place. No clone and no pin: the page
            # is built from the same tree it is committed to, so the counts on it
            # cannot lag the repository by a fortnight.
            checkouts[src["id"]] = REPO_ROOT
            continue
        ref = src.get("ref")
        if not ref:
            fail(
                f"[{src['id']}] has no pinned 'ref' in sources.json. "
                f"Run: python3 build.py --refresh --write"
            )
        dest = tmp / src["id"]
        subprocess.run(
            ["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
             src["url"] + ".git", str(dest)],
            check=True,
        )
        r = subprocess.run(
            ["git", "-C", str(dest), "checkout", "--quiet", ref],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            fail(
                f"[{src['id']}] pinned commit {ref[:12]} is not reachable in "
                f"{src['url']} ({r.stderr.strip()}). It may have been force-pushed; "
                f"re-pin with: python3 build.py --refresh --write"
            )
        checkouts[src["id"]] = dest
    return checkouts


# ------------------------------------------------------------------ rendering


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def _solution_frontmatter(path: Path) -> dict:
    """Parse a solutions/*.md frontmatter without PyYAML (stdlib only)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    out: dict = {}
    steps: list = []
    for line in parts[1].splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        if line[0] not in (" ", "-") and ":" in line:
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip().strip('"').strip("'")
            continue
        m = re.match(r"^\s*-\s+skill:\s*(.+)$", line)
        if m:
            steps.append({"skill": m.group(1).strip().strip('"').strip("'")})
            continue
        h = re.match(r"^\s+handoff:\s*(.+)$", line)
        if h and steps:
            steps[-1]["handoff"] = h.group(1).strip()
            continue
        w = re.match(r"^\s+why:\s*(.+)$", line)
        if w and steps:
            steps[-1]["why"] = w.group(1).strip()
    if steps:
        out["steps"] = steps
    return out


def collect_solutions() -> list:
    """Read solutions/*.md; each is a curated master skill chaining real skills."""
    sol_dir = REPO_ROOT / "solutions"
    if not sol_dir.is_dir():
        return []
    out = []
    for p in sorted(sol_dir.glob("*.md")):
        fm = _solution_frontmatter(p)
        if fm.get("name") and fm.get("steps"):
            out.append(fm)
    return out


def slug(key: str) -> str:
    """A DOM-safe id from an identity key, with collisions ruled out at build time.

    Keys look like `engineering~agenthub~init`. The id has to work in a fragment
    link and a CSS selector, and it must stay one-to-one with the key it came from,
    or two Solutions would share an anchor.
    """
    return "s-" + re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")


def hue_class(name: str) -> str:
    """Deterministic community colour class for a category.

    The colours live in styles.css as .h0 to .h11, not in a style attribute,
    because the production Content-Security-Policy is style-src 'self': an inline
    style attribute is refused by the browser, and a <style> block would be too.
    Hashing the category name means a new category picks up a colour without
    anyone editing CSS, and the same category keeps its colour between builds.
    """
    h = 0
    for ch in name:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return f"h{h % 12}"


# How many Solutions the pinned opening travels through. The graph holds every
# Solution and all of them are reachable by search or click, but scroll-stepping
# through 54 of them would be exactly the endless scrolling this page is trying to
# stop being. Eight is enough to teach the interaction and show the range.
FEATURED = 8

# Twelve hues is as many as anyone can hold apart at once. The communities beyond that
# are drawn in grey and named in the panel rather than given a colour that means nothing.
NAMED_COMMUNITIES = 12

# Names are cheap; colours are not. Tightening the edge rules split the library into 31
# communities rather than 19, and nineteen unnamed grey clusters is a worse page than
# twelve coloured ones plus six more that at least say what they are.
LABELLED_COMMUNITIES = 18

# Names drawn without being asked for. The rest arrive on hover, on selection, or
# through search: 490 names at this scale is a grey wash, not a labelling.
HUB_LABELS = 26

# Modularity resolution. Higher splits the library into more, smaller subjects; at 1.0
# the largest community is 50 skills and the smallest with real structure is 5, which is
# the range where the labels the members generate are still recognisable.
COMMUNITY_RESOLUTION = 1.0

# The graph's coordinate system, in one place. The layout used 1400x620 while the <svg>
# declared a viewBox of 1400x560, so twenty-nine skills were positioned in a band the
# browser clips away: highlighted, labelled, counted in the panel, and invisible. Both the
# viewBox attribute and the layout now come from here.
FRAME = network.FRAME


def _domain_of(nodes: dict, node_id: str) -> str:
    cur = node_id
    while nodes[cur]["parent"] is not None:
        cur = nodes[cur]["parent"]
    return cur


def render_network(net: dict, graph: dict, comm: dict, rows: list, sols: list) -> tuple:
    """Draw the library as a knowledge graph: communities, hubs, evidence, frontier.

    This is the fourth opening this page has had, and the first that draws something
    nobody decided in advance. A spiral packing of all 540 nodes was an even speckle. A
    four-column dendrogram of the taxonomy was tidy and inert — it drew the filing
    system, and a filing system is not a finding. Both showed a structure that had
    already been written down somewhere.

    Here the colours are communities found by modularity maximisation over evidence
    taken from the files, the big nodes are big because everything runs through them,
    and where a community cuts across the declared domains that disagreement is on
    screen rather than smoothed away.

    Every node is still a link to the skill's own card, so this is a table of contents
    before any script runs.
    """
    pos = net["pos"]
    degree = graph["degree"]
    kinds = graph["kinds"]
    by_key = {r["key"]: r for r in rows}
    order = net["communities"]

    # Twelve distinct hues, then a neutral. Nineteen communities have real structure and
    # twelve is as many colours as anyone can hold apart; the smaller ones are drawn in
    # grey and named in the panel instead of being given a colour that means nothing.
    hue_of = {}
    for i, cid in enumerate(order):
        hue_of[cid] = f"h{i}" if i < NAMED_COMMUNITIES else "hx"

    def hue(key):
        return hue_of.get(comm[key], "hx")

    sol_of = collections.defaultdict(list)
    lead_of = {}
    for s in sols:
        if s["lead"] in by_key:
            lead_of[s["lead"]] = s
        for m in s["members"]:
            sol_of[m].append(s["lead"])

    max_deg = max(degree.values()) if degree else 1

    def radius(key):
        # Area, not radius, in proportion to degree, so the hubs read as bigger without
        # a 23-connection node being eleven times the width of a 2-connection one.
        d = degree.get(key, 0)
        return round(2.1 + 6.4 * math.sqrt(d / max_deg), 2)

    parts = []
    # One group holds everything the camera moves, so framing a community is a single
    # transform rather than 490 rewritten coordinates. Labels ride inside it and divide
    # their font size by the same factor, which is what the first camera got wrong:
    # SVG text is measured in user units, so zooming in made every label grow until they
    # collided.
    parts.append('        <g id="vp" class="g-vp">')

    # ------------------------------------------------------------------- the edges
    #
    # Drawn before the nodes, because SVG paints in document order and an edge crossing
    # a node should pass behind it. Curved rather than straight: 1,868 straight lines
    # between 490 points is a moiré, and a slight arc lets two edges between the same
    # pair of clusters stay distinguishable.
    parts.append('        <g class="g-edges" aria-hidden="true">')
    edge_rows = []
    for i, ((a, b), w) in enumerate(sorted(graph["weights"].items())):
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        mx = (x1 + x2) / 2 + (y2 - y1) * 0.11
        my = (y1 + y2) / 2 - (x2 - x1) * 0.11
        kind = kinds[(a, b)]
        parts.append(
            f'          <path class="g-edge g-edge--{kind} {hue(a)}" '
            f'data-a="{esc(a)}" data-b="{esc(b)}" data-i="{i}" '
            f'd="M{x1},{y1} Q{round(mx, 1)},{round(my, 1)} {x2},{y2}"/>'
        )
        edge_rows.append((a, b, round(w, 2), kind, graph["why"].get((a, b), [])[:2]))
    parts.append("        </g>")

    # ------------------------------------------------------------------- the nodes
    parts.append('        <g class="g-nodes">')
    # Smallest first, so a hub is never buried under the leaves it connects.
    for key in sorted(pos, key=lambda k: (degree.get(k, 0), k)):
        row = by_key[key]
        x, y = pos[key]
        r = radius(key)
        cid = comm[key]
        classes = f"g-node {hue(key)}"
        if key in lead_of:
            classes += " is-lead"
        # The frontier: no edges at all, so nothing in the library connects this skill to
        # anything. This was keyed on Solution membership before, which drew 158 skills as
        # the frontier while 129 of them had edges, and left five genuine isolates out of
        # it — a visible claim that was simply false.
        if degree.get(key, 0) == 0:
            classes += " is-loose"
        attrs = [
            f'class="{classes}"',
            f'href="#skill-{slug(key)}"',
            f'data-key="{esc(key)}"',
            f'data-name="{esc(row["n"])}"',
            f'data-comm="{cid}"',
            f'data-deg="{degree.get(key, 0)}"',
            f'data-dom="{esc(row["dom"])}"',
            f'data-x="{x}"',
            f'data-y="{y}"',
        ]
        if sol_of.get(key):
            attrs.append(f'data-sol="{esc(" ".join(sol_of[key]))}"')
        if key in lead_of:
            attrs.append(f'data-leads="{esc(lead_of[key]["lead"])}"')
        aria = f'{row["n"]}, {degree.get(key, 0)} connections'
        attrs.append(f'aria-label="{esc(aria)}"')
        parts.append(f'          <a {" ".join(attrs)}>')
        # A hit target far larger than the dot: the smallest node is 4.2 units across in
        # a 1400-unit frame, which is under four rendered pixels.
        parts.append(
            f'            <circle class="g-hit" cx="{x}" cy="{y}" '
            f'r="{round(min(network.MIN_GAP / 2 - 0.6, max(6.4, r + 4.5)), 1)}"/>'
        )
        parts.append(f'            <circle class="g-dot" cx="{x}" cy="{y}" r="{r}"/>')
        parts.append("          </a>")
    parts.append("        </g>")

    # ------------------------------------------------------------------ the labels
    #
    # Two kinds, both in their own layer so they paint above every node and every edge.
    # Community names sit above their members; individual names are only drawn for the
    # hubs, because 490 of them at this scale is a grey wash.
    parts.append('        <g class="g-labels" aria-hidden="true">')
    labels_by_cid = {
        cid: network.label_community(net["members"][cid], by_key, graph) for cid in order
    }
    community_spots = network.place_community_labels(
        order,
        labels_by_cid,
        net["members"],
        pos,
        LABELLED_COMMUNITIES,
        frame=(0.0, 0.0, network.FRAME[0], network.FRAME[1]),
    )
    community_meta = []
    for i, cid in enumerate(order):
        members = net["members"][cid]
        xs = [pos[m][0] for m in members]
        ys = [pos[m][1] for m in members]
        cx = round(sum(xs) / len(xs), 1)
        top = round(min(ys) - 9.0, 1)
        label = labels_by_cid[cid]
        spot = community_spots.get(cid)
        hub = max(members, key=lambda k: (degree.get(k, 0), k))
        community_meta.append(
            {
                "id": cid,
                "label": label,
                "size": len(members),
                "hub": by_key[hub]["n"],
                "x": cx,
                "y": top,
            }
        )
        if spot is not None:
            parts.append(
                f'          <text class="g-clabel {hue_of[cid]}" data-comm="{cid}" '
                f'x="{spot["x"]}" y="{spot["y"]}" text-anchor="middle">'
                f'{esc(label)}</text>'
            )

    # A name for every skill, not only for the hubs. The hubs' names are visible from
    # the start; the other 464 are drawn with zero opacity and revealed when something
    # asks for them — a selection, a community, a traced path, a search hit.
    #
    # Emitting only the 26 hubs meant that opening a community whose own strongest
    # member was not one of the library's 26 strongest named nothing at all.
    ranked = sorted(pos, key=lambda k: (-degree.get(k, 0), k))
    # The community names are already on the page and must not be written over, so they
    # are reserved before any skill name is offered a position.
    reserved = [spot["box"] for spot in community_spots.values()]
    hubs = network.place_labels(
        ranked,
        {k: by_key[k]["n"] for k in ranked},
        pos,
        {k: radius(k) for k in ranked},
        HUB_LABELS,
        frame=(0.0, 0.0, network.FRAME[0], network.FRAME[1]),
        reserved=reserved,
    )
    for key in ranked:
        spot = hubs.get(key)
        if spot is None:
            # Present but invisible until something asks for it. Every skill has a name
            # in the document; only the ones that fit are drawn without being asked.
            x, y = pos[key]
            parts.append(
                f'          <text class="g-nlabel g-nlabel--extra {hue(key)}" '
                f'data-key="{esc(key)}" x="{round(x + radius(key) + 4, 1)}" '
                f'y="{round(y + 3.2, 1)}" text-anchor="start">'
                f'{esc(by_key[key]["n"])}</text>'
            )
        else:
            parts.append(
                f'          <text class="g-nlabel {hue(key)}" data-key="{esc(key)}" '
                f'x="{spot["x"]}" y="{spot["y"]}" '
                f'text-anchor="{spot["anchor"]}">{esc(by_key[key]["n"])}</text>'
            )
    parts.append("        </g>")

    parts.append("        </g>")
    return "\n".join(parts), edge_rows, community_meta, hue_of


def render(rows: list) -> "tuple[dict, str]":
    counts = collections.Counter(r["dom"] for r in rows)
    # Sorted by size then by name: two categories with the same count must not swap
    # places between builds, or the page is not reproducible from source.
    order = [c for c, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    total = len(rows)

    by = collections.defaultdict(list)
    for r in rows:
        by[r["dom"]].append(r)
    for k in by:
        by[k].sort(key=lambda r: r["n"])

    sols, stats = compose.build_solutions(REPO_ROOT, rows, _solution_frontmatter, fail)
    spec = network.load_domains(ROOT)
    graph = network.build_graph(rows, sols)
    comm = network.communities(graph, sorted(r["key"] for r in rows), COMMUNITY_RESOLUTION)
    net = network.layout(
        graph, comm, {r["key"]: r for r in rows}, width=FRAME[0], height=FRAME[1]
    )
    agree = network.agreement(comm, rows, spec)
    # How many of the drawn relationships the repository states outright, rather than this
    # page having inferred them from names. Counted once and used everywhere it is claimed:
    # in the intro, on the filter button, and in the audit that fails the build if the
    # markup states a number the build does not own.
    graph_svg, edge_rows, community_meta, hue_of = render_network(
        net, graph, comm, rows, sols
    )
    n_stated = sum(1 for e in edge_rows if e[3] == "extracted")
    # Spoken to anyone who cannot see the graph, so it has to describe what is drawn and
    # be regenerated from the same numbers. It read "the library as a four-layer tree" for
    # a build after the tree was gone.
    graph_label = (
        f"The library as a graph: {len(rows)} skills, "
        f"{len(edge_rows):,} relationships, and {len(net['communities'])} communities "
        f"detected from what the skills reference rather than from how they are filed. "
        f"Each node is a link to that skill's own entry. The same information is listed "
        f"as text under Solutions and The library below."
    )
    # The scroll traversal walks the largest communities, which is also the order the
    # chapter markers use.
    featured = [c["id"] for c in community_meta[:FEATURED]]
    by_lead = {s["lead"]: s for s in sols}
    key_row = {r["key"]: r for r in rows}
    claimed_keys = {m for x in sols for m in x["members"]} | set(by_lead)

    # Anchors are derived from identity, so two Solutions cannot share one.
    slugs = {}
    for s in sols:
        sl = slug(s["lead"])
        if sl in slugs:
            fail(f"anchor collision: {sl!r} from {s['lead']!r} and {slugs[sl]!r}")
        slugs[sl] = s["lead"]

    out = []

    # ------------------------------------------------------------------- rail
    out.append('    <nav class="rail" id="rail" aria-label="Categories">')
    for cat in order:
        out.append(
            f'      <a href="#cat-{esc(cat)}">{esc(LABELS.get(cat, cat))}'
            f"<span>{counts[cat]}</span></a>"
        )
    out.append("    </nav>")

    # ------------------------------------------------------- the opening stage
    #
    # The graph is the first thing on the page, not a diagram buried under it. It
    # is also the navigation: every Solution is a node you can reach by scrolling
    # past it, searching for it, or clicking it.
    out.append('    <header class="stage" id="top">')
    out.append('      <div class="stage__tools">')
    out.append('        <label class="vh" for="gsearch">Search the graph</label>')
    out.append(
        f'        <input class="stage__search" id="gsearch" type="search" '
        f'placeholder="Search {total} skills" autocomplete="off" spellcheck="false">'
    )
    # Controls that act on the graph rather than on the Solutions list. The three
    # provenance chips that used to sit here filtered Solution nodes, and the graph no
    # longer draws Solutions as nodes: every node is a skill. Tier is still on every
    # Solution card below, where it is read rather than filtered.
    out.append(
        '        <div class="stage__chips" id="gchips" role="group" '
        'aria-label="Graph controls">'
    )
    out.append(
        f'          <button class="chip" type="button" id="gstated" aria-pressed="false" '
        f'title="hide the relationships this page inferred">stated only '
        f'<span>{n_stated}</span></button>'
    )
    out.append(
        '          <button class="chip" type="button" id="gpath" aria-pressed="false" '
        'title="pick two skills and see the shortest route between them">'
        'trace a path</button>'
    )
    out.append('          <button class="chip chip--reset" type="button" id="greset">Reset</button>')
    out.append("        </div>")
    out.append("      </div>")

    # The panel is prerendered with the first Solution, so it is never an empty
    # box waiting for a hover that never comes on a touch screen.
    out.append('      <div class="stage__canvas">')
    out.append(
        # role="group", not role="img". An img role makes the whole subtree
        # presentational, which is wrong here: the graph contains 54 controls. axe
        # flagged the aria-label on every lead as a prohibited attribute for
        # exactly this reason.
        f'        <svg class="stage__svg" id="gsvg" '
        f'viewBox="0 0 {FRAME[0]:.0f} {FRAME[1]:.0f}" '
        f'role="group" aria-label="{esc(graph_label)}">'
    )
    out.append(graph_svg)
    out.append("        </svg>")
    out.append("      </div>")

    out.append('      <div class="stage__intro">')
    out.append('        <p class="eyebrow">Agent skill library</p>')
    # The number is the truth from the tree, rendered at full value. It does not
    # animate up from zero: the resting state of a headline should not be a false
    # statement, and "0 skills" was the first thing every visitor read.
    # Short enough to hold one line at the width the intro actually gets. The
    # longer phrasing wrapped to two lines, and every line the text takes is a line
    # the graph loses: the stage is exactly one screen tall.
    out.append(
        f'        <h1><b>{len(sols)}</b> Solutions from <b>{total}</b> skills</h1>'
    )
    out.append(
        f'        <p class="stage__sub">Not a filing system: {len(net["communities"])} '
        f'communities found from {len(edge_rows):,} relationships — {n_stated} the '
        f'repository states outright, the rest inferred from names sharing a subject. '
        f'Open a community, trace a path, or search.</p>'
    )
    out.append('        <p class="cue" id="cue"><span></span>Scroll</p>')
    out.append("      </div>")

    # tabindex="0" because the panel is a scrollable region: a hub with 23 connections
    # overflows it, and axe is right to flag a scrollable region that cannot be focused —
    # without this a keyboard user cannot read the bottom of the largest node's entry.
    out.append(
        '      <aside class="stage__panel" id="panel" aria-live="polite" '
        'tabindex="0" aria-label="Selected node">'
    )
    # Opens on the largest community rather than on one skill: the first statement the
    # page makes should be the shape it found, not one item inside it.
    first = community_meta[0]
    out.append('        <p class="panel__tier" id="paneltier">community</p>')
    out.append(
        f'        <h2 class="panel__name" id="panelname">{esc(first["label"])}</h2>'
    )
    out.append(
        f'        <p class="panel__desc" id="paneldesc">'
        f'{first["size"]} skills grouped by what their names and their Solutions say '
        f'they have in common, not by where they are filed. Its most connected member '
        f'is {esc(first["hub"])}.</p>'
    )
    out.append('        <ol class="panel__chain" id="panelchain">')
    for key in net["members"][first["id"]][:10]:
        out.append(f'          <li>{esc(key_row[key]["n"])}</li>')
    out.append("        </ol>")
    out.append(
        f'        <p class="panel__ev" id="panelev">'
        f'{first["size"]} skills · most connected: {esc(first["hub"])}</p>'
    )
    out.append("      </aside>")

    # One scroll beat per featured Solution. app.js turns these into the traversal;
    # without JavaScript they are a plain list of links into the Solutions section.
    out.append('      <ol class="stage__beats" id="beats">')
    meta_by_id = {c["id"]: c for c in community_meta}
    for cid in featured:
        c = meta_by_id[cid]
        out.append(
            f'        <li class="beat" data-comm="{cid}">'
            f'<a href="#solutions">{esc(c["label"])}</a></li>'
        )
    out.append("      </ol>")
    out.append("    </header>")

    # --------------------------------------------------------------- solutions
    out.append('    <section class="sols" id="solutions" aria-labelledby="solh">')
    out.append('      <h2 id="solh">Every Solution the library can form</h2>')
    out.append(
        f'      <p class="sols__lede">{len(sols)} Solutions cover '
        f'{stats["in_a_solution"]} of the {total} skills. '
        f'{stats["by_tier"]["curated"]} are written by hand, '
        f'{stats["by_tier"]["declared"]} are asserted by the lead skill itself, and '
        f'{stats["by_tier"]["composed"]} are candidates derived from the tree. '
        f'{stats["unclaimed"]} skills belong to no Solution yet.</p>'
    )
    out.append('      <div class="sols__grid">')
    for s in sols:
        out.append(
            f'        <article class="sol" id="{esc(slug(s["lead"]))}" '
            f'data-tier="{esc(s["tier"])}" data-sol="{esc(s["lead"])}">'
        )
        out.append('          <header class="sol__head">')
        out.append(f'            <h3>{esc(s.get("label", s["name"]))}</h3>')
        out.append(f'            <span class="sol__tier">{esc(s["tier"])}</span>')
        out.append("          </header>")
        if s.get("problem"):
            out.append(f'          <p class="sol__problem">{esc(s["problem"])}</p>')
        out.append('          <ol class="sol__chain">')
        for m in s["members"]:
            row = key_row.get(m)
            title = f'{row["repo"]} · {row["lic"]}' if row else ""
            out.append(
                f'            <li><span class="sol__step" data-id="{esc(m)}" '
                f'title="{esc(title)}">{esc(row["n"] if row else m)}</span></li>'
            )
        out.append("          </ol>")
        out.append(f'          <p class="sol__ev">{esc(s.get("evidence", ""))}</p>')
        out.append("        </article>")
    out.append("      </div>")
    out.append("    </section>")

    # ----------------------------------------------------------------- library
    #
    # Every skill, in one compact pass. This replaced 24 pinned chapters that
    # scrubbed a filmstrip sideways: the effect was good once and then it was
    # 71,000 pixels of scrolling between a reader and the skill they wanted.
    out.append('    <main class="lib" id="library">')
    out.append('      <h2>The library</h2>')
    out.append(
        f'      <p class="lib__lede">All {total} skills, grouped by category. '
        "Each keeps the licence it was published under and names the repository "
        "it came from.</p>"
    )
    n = 0
    for cat in order:
        label = LABELS.get(cat, cat)
        # Every category starts closed. Leaving the largest one open added 5,000
        # pixels to the page before the reader had asked for anything, and on a
        # phone it was 13,000. Each row states its own count, so the section reads
        # as a browser rather than as an empty list, and app.js opens whichever
        # category a search or a rail link lands in.
        out.append(
            f'      <details class="lib__cat" id="cat-{esc(cat)}" '
            f'data-count="{counts[cat]}">'
        )
        out.append(
            f'        <summary class="lib__catname {hue_class(cat)}">'
            f'{esc(label)}<span>{counts[cat]}</span></summary>'
        )
        out.append('        <div class="lib__grid">')
        for s in by[cat]:
            n += 1
            desc = s["d"] or "No description declared in this skill's frontmatter."
            qual = f'<span class="qual">{esc(s["qual"])}</span>' if s.get("qual") else ""
            in_sol = s["key"] in claimed_keys
            out.append(
                f'          <article class="card{" card--used" if in_sol else ""}" '
                f'id="skill-{slug(s["key"])}" '
                f'data-id="{esc(s["key"])}" data-name="{esc(s["n"])}">'
            )
            out.append(
                f'            <div class="card__top"><span class="card__no">{n:03d}</span>'
                f'<span class="card__cmd">/{esc(s["n"])}</span></div>'
            )
            # The space before the qualifier matters: .qual is display:block so it
            # collapses visually, but without it the heading reads "runagenthub" to
            # a screen reader and to anything else consuming textContent.
            out.append(f'            <h4>{esc(s["n"])} {qual}</h4>')
            out.append(f"            <p>{esc(desc)}</p>")
            out.append(
                f'            <footer><a href="{esc(s["url"])}" rel="noopener">'
                f'{esc(s["repo"])}</a><span class="lic">{esc(s["lic"])}</span></footer>'
            )
            out.append("          </article>")
        out.append("        </div>")
        out.append("      </details>")
    out.append("    </main>")

    # credits, generated so the per-repo counts cannot drift from the tree
    per_repo = collections.Counter(r["repo"] for r in rows)
    lic_of = {r["repo"]: r["lic"] for r in rows}
    url_of = {r["repo"]: r["url"] for r in rows}
    cred = ['      <div class="credits" id="credits">']
    for repo, cnt in sorted(per_repo.items(), key=lambda kv: (-kv[1], kv[0])):
        cred.append(
            f'        <div><strong><a href="{esc(url_of[repo])}" rel="noopener">{esc(repo)}</a>'
            f'</strong><span class="lic">{esc(lic_of[repo])}</span>'
            f'<span class="n">{cnt} skills</span></div>'
        )
    cred.append("      </div>")

    # Index the nodes once, in the order the graph uses, so edges can be integers.
    node_index_order = sorted(net["pos"])
    node_index = {k: i for i, k in enumerate(node_index_order)}

    data = (
        "window.SKILLDATA="
        + json.dumps(
            {
                "total": total,
                "categories": len(order),
                "solutions": len(sols),
                "featured": featured,
                "tiers": stats["by_tier"],
                "covered": stats["in_a_solution"],
                "unclaimed": stats["unclaimed"],
                # The graph itself, so the browser can answer questions the DOM cannot:
                # which nodes neighbour this one, and how do these two connect.
                #
                # Keys are indices into "nodes" rather than repeated strings — the same
                # 1,868 edges written as pairs of identity keys came to 96 KB, and as
                # pairs of integers they come to 21 KB.
                "nodes": [k for k in node_index_order],
                "edges": [
                    [node_index[a], node_index[b], w, 0 if kind == "extracted" else 1]
                    for (a, b, w, kind, _why) in edge_rows
                ],
                "why": [why for (_a, _b, _w, _k, why) in edge_rows],
                "comms": [
                    {
                        "id": c["id"],
                        "label": c["label"],
                        "size": c["size"],
                        "hub": c["hub"],
                    }
                    for c in community_meta
                ],
                "agreement": agree,
                # The same character-width table the build places labels with, so the
                # browser reveals names using identical arithmetic instead of measuring.
                # Measuring was subtly wrong: the camera sets the zoom factor that the
                # labels' font size divides by, and reading getComputedTextLength in the
                # same tick could return a width from the layout before that recalculation
                # landed. One pair of names overlapped at 1280 wide and not at 1440.
                "charw": network.CHAR_W,
                "charwFallback": network.CHAR_W_FALLBACK,
                "labelFont": network.LABEL_FONT,
                "labelHeight": network.LABEL_H,
                "communityFont": network.COMMUNITY_FONT,
                "domains": spec["titles"],
                "catDomain": spec["cat_to_domain"],
            },
            separators=(",", ":"),
        )
        + ";\n"
    )
    return (
        {"main": "\n".join(out), "credits": "\n".join(cred)},
        data,
        len(sols),
        n_stated,
    )


# Every phrasing in the hand-written part of the page that states a count. Each
# must be regenerated on build, because a number nobody recalculates is a claim
# nobody checked.
CLAIMS = [
    (re.compile(r"\b(\d+) agent skills across (\d+) categories"), "{t} agent skills across {c} categories"),
    (re.compile(r"\b(\d+) AI agent skills across (\d+) categories"), "{t} AI agent skills across {c} categories"),
    (re.compile(r"\btravel through (\d+) categories"), "travel through {c} categories"),
    # Keeps the opening tag via the backreference, so the template only owns the
    # claim itself and not the markup around it.
    (re.compile(r'(<div class="hud__count" id="hudcount">)[^<]*'),
     r"\g<1>{t} skills / {s} Solutions"),
    # The evidence filter names how many relationships the repository states outright.
    # It is a measurement of the graph, so the build owns it: hand-typing 357 into the
    # markup is exactly the drift the rest of this list exists to stop.
    (re.compile(r'(id="gstated"[^>]*>stated only <span>)\d+'), r"\g<1>{e}"),
]

# Any surviving number attached to these nouns outside the generated region is a
# claim the build does not own, and is therefore drift waiting to happen.
AUDIT = re.compile(r"\b(\d+)\s+(?:AI\s+)?(?:agent\s+)?(?:skills|categories)\b")


def splice(
    page: str, blocks: dict, total: int, cats: int, sols: int, stated: int
) -> str:
    for key, (begin, end) in MARKERS.items():
        if page.count(begin) != 1 or page.count(end) != 1:
            fail(
                f"index.html has {page.count(begin)} BEGIN and {page.count(end)} END "
                f"markers for '{key}'; exactly one of each is required"
            )
        head = page.split(begin)[0]
        tail = page.split(end, 1)[1]
        page = head + begin + "\n" + blocks[key] + "\n    " + end + tail

    for pattern, template in CLAIMS:
        page = pattern.sub(
            template.format(t=total, c=cats, s=sols, e=stated), page
        )
    return page


def audit_svg(html: str) -> None:
    """The graph must be well-formed XML, not merely lint-clean HTML.

    html-validate does not parse SVG foreign content strictly, and accepted 54
    elements opened as <a> and closed as </g> without a word. The graph is the
    page's primary interface; if its markup is malformed, what a browser recovers
    is a guess.
    """
    import xml.etree.ElementTree as ET

    start = html.find("<svg")
    if start < 0:
        fail("the page contains no graph")
    end = html.find("</svg>", start)
    if end < 0:
        fail("the graph's <svg> element is never closed")
    try:
        ET.fromstring(html[start:end + 6])
    except ET.ParseError as e:
        fail(f"the graph is not well-formed XML: {e}")


def audit_claims(page: str, total: int, cats: int) -> list:
    """Find count claims in the hand-written region that the build does not own."""
    begin, end = MARKERS["main"]
    cbegin, cend = MARKERS["credits"]
    # Blank out both generated regions; their numbers are generated by definition.
    stripped = re.sub(
        re.escape(begin) + r".*?" + re.escape(end), "", page, flags=re.S
    )
    stripped = re.sub(
        re.escape(cbegin) + r".*?" + re.escape(cend), "", stripped, flags=re.S
    )
    bad = []
    for m in AUDIT.finditer(stripped):
        n = int(m.group(1))
        if n not in (total, cats):
            line = stripped[: m.start()].count("\n") + 1
            bad.append(f"line {line}: \"{m.group(0)}\" (data says {total} skills, {cats} categories)")
    return bad


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="Build the skill-browser page.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    ap.add_argument(
        "--refresh",
        action="store_true",
        help="move each pin in sources.json to the current upstream tip first",
    )
    args = ap.parse_args(argv)

    if not shutil.which("git"):
        fail("git is required")

    if args.refresh:
        if args.check:
            fail("--refresh changes the pins, so it cannot be combined with --check")
        print("re-pinning sources to their current upstream tips:")
        repin()

    rows = collect(fetch())
    if not rows:
        fail("no skills collected; check sources.json", 1)
    blocks, data, nsols, nstated = render(rows)
    counts = collections.Counter(r["dom"] for r in rows)

    current = INDEX.read_text(encoding="utf-8")
    updated = splice(current, blocks, len(rows), len(counts), nsols, nstated)

    audit_svg(updated)
    drift = audit_claims(updated, len(rows), len(counts))
    if drift:
        print(
            "error: index.html states counts the build does not own:\n  "
            + "\n  ".join(drift)
            + "\n\nAdd the phrasing to CLAIMS in build.py so it is regenerated, "
            "rather than editing the number by hand.",
            file=sys.stderr,
        )
        return 1

    if args.check:
        stale = []
        if current != updated:
            stale.append("index.html")
        if not DATA.exists() or DATA.read_text(encoding="utf-8") != data:
            stale.append("data.js")
        if stale:
            print(
                f"error: {', '.join(stale)} out of date against the sources. "
                f"Run: python3 build.py --write",
                file=sys.stderr,
            )
            return 1
        print(f"up to date: {len(rows)} skills across {len(counts)} categories")
        return 0

    INDEX.write_text(updated, encoding="utf-8")
    DATA.write_text(data, encoding="utf-8")
    print(f"wrote index.html and data.js: {len(rows)} skills across {len(counts)} categories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
