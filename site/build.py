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
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import compose

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


def render_graph(sols: list, rows: list, lay: dict) -> "tuple[str, list]":
    """Prerender the whole graph as inline SVG from the precomputed layout.

    Prerendered rather than drawn by JavaScript on load, for the same reason the
    cards are prerendered: the graph is the opening image of the page, and a page
    whose opening image only exists once a script has run is a page that is blank
    for anyone the script fails for. app.js adds traversal, focus and search on top
    of markup that is already correct and already visible.
    """
    nodes, edges, index = lay["nodes"], lay["edges"], lay["index"]
    by_name = {r["n"]: r for r in rows}
    # A skill can be led by more than one Solution, so ownership is a list, not a
    # value. code-review serves both idea-to-shipped-code and hard-to-find-bug;
    # when this held a single lead, focusing the second Solution lit only the
    # members no other Solution had already claimed.
    sol_of = {}
    for s in sols:
        for m in s["members"]:
            sol_of.setdefault(m, []).append(s["lead"])

    parts = []

    # Edges first so nodes always sit on top of them.
    parts.append('        <g class="g-edges" aria-hidden="true">')
    for a, b in edges:
        na, nb = nodes[a], nodes[b]
        lead_node = na if na["kind"] == "lead" else nb
        lead = lead_node["id"]
        # A skill can serve more than one Solution: code-review is used by both
        # idea-to-shipped-code and hard-to-find-bug, and agenthub shares run and
        # status with autoresearch-agent. The skill is drawn once, so those edges
        # cross the frame. Dashed, so a long line reads as a shared skill rather
        # than as a rendering fault.
        span = ((na["x"] - nb["x"]) ** 2 + (na["y"] - nb["y"]) ** 2) ** 0.5
        cross = " g-edge--cross" if span > 90 else ""
        parts.append(
            f'          <line class="g-edge{cross} {hue_class(lead_node["dom"])}" '
            f'data-sol="{esc(lead)}" '
            f'x1="{na["x"]}" y1="{na["y"]}" x2="{nb["x"]}" y2="{nb["y"]}"/>'
        )
    parts.append("        </g>")

    # The long tail: every skill no Solution claims. Drawn as a quiet outer band
    # rather than hidden, because "165 skills that no Solution uses" is a fact
    # about the library worth showing, and it is where the next Solution comes
    # from.
    parts.append('        <g class="g-tail" aria-hidden="true">')
    for n in nodes:
        if n["kind"] != "tail":
            continue
        parts.append(
            f'          <circle class="g-node g-node--tail {hue_class(n["dom"])}" '
            f'data-id="{esc(n["id"])}" data-dom="{esc(n["dom"])}" '
            f'cx="{n["x"]}" cy="{n["y"]}" r="{n["r"]}"/>'
        )
    parts.append("        </g>")

    parts.append('        <g class="g-members" aria-hidden="true">')
    for n in nodes:
        if n["kind"] != "member":
            continue
        parts.append(
            f'          <circle class="g-node g-node--member {hue_class(n["dom"])}" '
            f'data-id="{esc(n["id"])}" data-dom="{esc(n["dom"])}" '
            f'data-sol="{esc(" ".join(sol_of.get(n["id"], [])))}" '
            f'cx="{n["x"]}" cy="{n["y"]}" r="{n["r"]}"/>'
        )
    parts.append("        </g>")

    # Leads carry a real accessible name each, so the graph is a list of Solutions
    # to a screen reader instead of 487 unlabelled circles.
    label_of = {s["lead"]: s.get("label", s["lead"]) for s in sols}
    tier_of = {s["lead"]: s["tier"] for s in sols}
    # Only the featured leads carry a label at rest. Fifty-four labels at once was
    # unreadable overlapping text, and a graph you cannot read is a texture.
    featured_set = {s["lead"] for s in sols[:FEATURED]}
    parts.append('        <g class="g-leads">')
    for n in nodes:
        if n["kind"] != "lead":
            continue
        label = label_of.get(n["id"], n["id"])
        named = " is-named" if n["id"] in featured_set else ""
        parts.append(
            f'          <g class="g-lead {hue_class(n["dom"])}{named}" '
            f'data-id="{esc(n["id"])}" '
            f'data-tier="{esc(tier_of.get(n["id"], ""))}" data-dom="{esc(n["dom"])}" '
            f'tabindex="0" aria-label="{esc(label)}">'
        )
        # An invisible, larger hit target, because the lead circle is under 10
        # units across and asking a pointer to land on that would make the graph
        # decorative rather than usable.
        #
        # Sized at r+7, not r+11. The closest two leads sit 41 units apart, so an
        # r+11 target spanned 41 units and overlapped its neighbour's: clicking
        # agenthub lit agenthub but the pointer then entered self-improving-agent's
        # target, and the panel described a different Solution to the one shown.
        parts.append(
            f'            <circle class="g-hit" cx="{n["x"]}" cy="{n["y"]}" '
            f'r="{round(n["r"] + 7, 1)}"/>'
        )
        parts.append(
            f'            <circle class="g-node g-node--lead" cx="{n["x"]}" '
            f'cy="{n["y"]}" r="{n["r"]}"/>'
        )
        parts.append("          </g>")
    parts.append("        </g>")

    # Labels are a layer of their own, drawn after every node.
    #
    # They used to live inside each lead's group, which meant a lead placed later
    # in the document painted its circle over an earlier lead's label: the
    # `landing-page-that-sells` label was sliced in half by a neighbouring node.
    # SVG has no z-index, so the only way to guarantee text sits above all geometry
    # is to emit it last.
    parts.append('        <g class="g-labels" aria-hidden="true">')
    for n in nodes:
        if n["kind"] != "lead":
            continue
        label = label_of.get(n["id"], n["id"])
        named = " is-named" if n["id"] in featured_set else ""
        parts.append(
            f'          <text class="g-label{named}" data-id="{esc(n["id"])}" '
            f'x="{n["x"]}" y="{round(n["y"] + n["r"] + 12, 1)}" '
            f'text-anchor="middle">{esc(label)}</text>'
        )
    parts.append("        </g>")

    featured = [s["lead"] for s in sols[:FEATURED]]
    return "\n".join(parts), featured


def render(rows: list) -> "tuple[dict, str]":
    counts = collections.Counter(r["dom"] for r in rows)
    order = [c for c, _ in counts.most_common()]
    total = len(rows)

    by = collections.defaultdict(list)
    for r in rows:
        by[r["dom"]].append(r)
    for k in by:
        by[k].sort(key=lambda r: r["n"])

    sols, stats = compose.build_solutions(REPO_ROOT, rows, _solution_frontmatter)
    lay = compose.layout(sols, rows)
    graph_svg, featured = render_graph(sols, rows, lay)
    by_lead = {s["lead"]: s for s in sols}
    name_row = {r["n"]: r for r in rows}

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
    out.append('      <div class="stage__canvas">')
    out.append(
        '        <svg class="stage__svg" id="gsvg" viewBox="0 0 1400 560" '
        'role="img" aria-label="Every Solution in the library and the skills each '
        'one leads. The same information is listed as text under Solutions below.">'
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
        '        <p class="stage__sub">A Solution is one lead skill that drives a named '
        "subset of the rest. Scroll to travel between them, search, or click any "
        "node.</p>"
    )
    out.append('        <p class="cue" id="cue"><span></span>Scroll</p>')
    out.append("      </div>")

    # Graphify-shaped controls: search the graph, filter by how much the library
    # actually asserts about each Solution, and get back out.
    out.append('      <div class="stage__tools">')
    out.append('        <label class="vh" for="gsearch">Search the graph</label>')
    out.append(
        f'        <input class="stage__search" id="gsearch" type="search" '
        f'placeholder="Search {total} skills" autocomplete="off" spellcheck="false">'
    )
    out.append('        <div class="stage__chips" id="gchips" role="group" aria-label="Filter by provenance">')
    for tier, blurb in (
        ("curated", "written by hand"),
        ("declared", "the lead names its own members"),
        ("composed", "derived candidate"),
    ):
        n = stats["by_tier"][tier]
        out.append(
            f'          <button class="chip" type="button" data-tier="{tier}" '
            f'aria-pressed="false" title="{esc(blurb)}">{tier} <span>{n}</span></button>'
        )
    out.append('          <button class="chip chip--reset" type="button" id="greset">Reset</button>')
    out.append("        </div>")
    out.append("      </div>")

    # The panel is prerendered with the first Solution, so it is never an empty
    # box waiting for a hover that never comes on a touch screen.
    first = sols[0]
    out.append('      <aside class="stage__panel" id="panel" aria-live="polite">')
    out.append(f'        <p class="panel__tier" id="paneltier">{esc(first["tier"])}</p>')
    out.append(f'        <h2 class="panel__name" id="panelname">{esc(first.get("label", first["lead"]))}</h2>')
    out.append(f'        <p class="panel__desc" id="paneldesc">{esc(first.get("problem", ""))}</p>')
    out.append('        <ol class="panel__chain" id="panelchain">')
    for m in first["members"]:
        out.append(f'          <li>{esc(m)}</li>')
    out.append("        </ol>")
    out.append(f'        <p class="panel__ev" id="panelev">{esc(first.get("evidence", ""))}</p>')
    out.append("      </aside>")

    # One scroll beat per featured Solution. app.js turns these into the traversal;
    # without JavaScript they are a plain list of links into the Solutions section.
    out.append('      <ol class="stage__beats" id="beats">')
    for lead in featured:
        s = by_lead[lead]
        out.append(
            f'        <li class="beat" data-sol="{esc(lead)}">'
            f'<a href="#sol-{esc(lead)}">{esc(s.get("label", lead))}</a></li>'
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
            f'        <article class="sol" id="sol-{esc(s["lead"])}" '
            f'data-tier="{esc(s["tier"])}" data-sol="{esc(s["lead"])}">'
        )
        out.append('          <header class="sol__head">')
        out.append(f'            <h3>{esc(s.get("label", s["lead"]))}</h3>')
        out.append(f'            <span class="sol__tier">{esc(s["tier"])}</span>')
        out.append("          </header>")
        if s.get("problem"):
            out.append(f'          <p class="sol__problem">{esc(s["problem"])}</p>')
        out.append(f'          <ol class="sol__chain">')
        for m in s["members"]:
            row = name_row.get(m)
            title = f'{row["repo"]} · {row["lic"]}' if row else ""
            out.append(
                f'            <li><span class="sol__step" title="{esc(title)}">{esc(m)}</span></li>'
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
            in_sol = s["n"] in {m for x in sols for m in x["members"]} or s["n"] in by_lead
            out.append(
                f'          <article class="card{" card--used" if in_sol else ""}" '
                f'data-id="{esc(s["n"])}">'
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
    for repo, cnt in per_repo.most_common():
        cred.append(
            f'        <div><strong><a href="{esc(url_of[repo])}" rel="noopener">{esc(repo)}</a>'
            f'</strong><span class="lic">{esc(lic_of[repo])}</span>'
            f'<span class="n">{cnt} skills</span></div>'
        )
    cred.append("      </div>")

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
            },
            separators=(",", ":"),
        )
        + ";\n"
    )
    return {"main": "\n".join(out), "credits": "\n".join(cred)}, data, len(sols)


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
]

# Any surviving number attached to these nouns outside the generated region is a
# claim the build does not own, and is therefore drift waiting to happen.
AUDIT = re.compile(r"\b(\d+)\s+(?:AI\s+)?(?:agent\s+)?(?:skills|categories)\b")


def splice(page: str, blocks: dict, total: int, cats: int, sols: int) -> str:
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
        page = pattern.sub(template.format(t=total, c=cats, s=sols), page)
    return page


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
    blocks, data, nsols = render(rows)
    counts = collections.Counter(r["dom"] for r in rows)

    current = INDEX.read_text(encoding="utf-8")
    updated = splice(current, blocks, len(rows), len(counts), nsols)

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
