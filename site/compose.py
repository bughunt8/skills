"""Compose Solutions from the skill library.

A Solution is a LEAD skill plus the subset of skills it leads. That is the whole
model: the library is 490 skills, and a Solution is the one skill you invoke that
knows how to drive a named handful of the others.

The point of this module is to answer "which combinations of these skills actually
form a Solution" without inventing any of them. Every Solution it emits carries a
provenance tier, and the tiers are ordered by how much the repository itself
asserts rather than how much this code inferred:

  curated   A human wrote solutions/<name>.md, naming the chain and the handoffs.
            Highest confidence. Nothing here is derived.

  declared  A bundle contains a skill named after the bundle, and that skill's own
            SKILL.md names its siblings in prose. The lead-to-member edge is a
            quotable fact from the lead's own text, not a guess. This is how
            agenthub, c-level-agents, commercial-skills and the rest describe
            themselves.

  composed  A category has no lead skill, so no Solution is asserted anywhere. A
            candidate chain is derived by ordering that category's skills along a
            delivery lifecycle and electing the most orchestration-shaped skill as
            lead. These are labelled as candidates on the page, because that is
            what they are.

On "every possible combination": the library has 490 skills, so the number of
subsets is 2**490, which is not a number anyone can enumerate or use. Asking for
every combination is really asking which combinations cohere. This module states
its coherence rules, applies them to all 490 skills, and reports what it found and
what it left out, so the claim is checkable rather than impressive.

Layout is computed here, in Python, rather than in the browser. A seeded force
simulation run at build time is deterministic, so the reproducibility gate can
catch drift; it prerenders into SVG so the graph exists without JavaScript; and it
means the browser spends its budget on interaction instead of physics.
"""

import math
import re
from pathlib import Path

# --------------------------------------------------------------- lifecycle stages
#
# Order matters: it is the spine a composed chain is sorted along, so a candidate
# Solution reads as a sequence of work rather than a bag of related skills.
STAGES = [
    ("route", ["route", "dispatch", "triage", "choose", "select", "which skill",
               "get started", "entry point", "orchestrat", "coordinat"]),
    ("research", ["research", "discover", "investigat", "benchmark", "competitive",
                  "market", "interview", "survey", "landscape", "evaluate"]),
    ("spec", ["spec", "requirement", "prd", "plan", "roadmap", "architect",
              "design doc", "adr", "decision", "scope", "brief"]),
    ("design", ["ui", "ux", "visual", "brand", "typograph", "layout", "wireframe",
                "mockup", "design system", "palette", "logo"]),
    ("build", ["implement", "build", "scaffold", "generate", "code", "write code",
               "refactor", "migrat", "develop", "author"]),
    ("verify", ["test", "review", "audit", "qa", "validat", "lint", "verify",
                "security", "adversarial", "check", "debug", "diagnos"]),
    ("ship", ["deploy", "release", "ship", "publish", "ci/cd", "pipeline",
              "launch", "rollout"]),
    ("operate", ["monitor", "observab", "incident", "on-call", "oncall", "sre",
                 "runbook", "postmortem", "capacity", "reliability", "slo"]),
    ("measure", ["analytic", "metric", "measure", "kpi", "dashboard", "report",
                 "forecast", "attribution", "experiment", "a/b"]),
    ("govern", ["complian", "iso", "gdpr", "risk", "policy", "legal", "governance",
                "regulat", "audit trail", "eu ai act", "privacy", "contract"]),
]

# Words that mark a skill as the thing you invoke to drive other skills.
LEAD_SIGNALS = [
    "orchestrat", "route", "dispatch", "coordinat", "end-to-end", "end to end",
    "pipeline", "workflow", "entry point", "get started", "delegat",
    "which skill", "sub-skill", "subskill", "suite of", "collection of",
    "master", "conductor", "driver",
]

MAX_CHAINS_PER_DOM = 6

ENTRY_NAMES = {"get-started", "init", "start", "main", "orchestrator", "router", "index"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower())


def stage_of(name: str, desc: str) -> str:
    """Classify a skill onto one lifecycle stage.

    First match wins in STAGES order, and the name is weighted over the
    description because a skill called `code-review` is a review skill even if its
    description talks about building. Unmatched skills get "build", the least
    surprising default for a library that is mostly about making things.
    """
    n, d = _norm(name), _norm(desc)
    for stage, keys in STAGES:
        if any(k in n for k in keys):
            return stage
    for stage, keys in STAGES:
        if any(k in d for k in keys):
            return stage
    return "build"


def lead_score(name: str, desc: str, sibling_names: list) -> int:
    """How much this skill looks like the lead for a set of others."""
    n, d = _norm(name), _norm(desc)
    score = sum(3 for k in LEAD_SIGNALS if k in d)
    score += sum(4 for k in LEAD_SIGNALS if k in n)
    if n in ENTRY_NAMES:
        score += 6
    if n.endswith("-skills") or n.endswith("-os") or n.endswith("-hub"):
        score += 5
    # Naming its siblings is the strongest signal there is: the skill is
    # documenting the set it drives.
    score += 2 * sum(1 for s in sibling_names if s != name and re.search(
        r"\b" + re.escape(s) + r"\b", d))
    return score


# ------------------------------------------------------------------- the bundles


def find_bundles(skills_root: Path) -> dict:
    """Map every bundle directory to the skill names directly inside its skills/.

    A "bundle" is any directory with a skills/ child holding two or more skills.
    That is the repository's own grouping, so it costs nothing to trust and it is
    the same shape the leads describe in prose.
    """
    out = {}
    for path in skills_root.rglob("skills"):
        if not path.is_dir() or path == skills_root:
            continue
        kids = sorted(
            d.name for d in path.iterdir()
            if d.is_dir() and (d / "SKILL.md").is_file()
        )
        if len(kids) >= 2:
            out[path.parent] = kids
    return out


def declared_solutions(skills_root: Path, by_key: dict) -> list:
    """Solutions the library asserts about itself.

    A bundle qualifies when it contains a skill that is plausibly its lead and
    that skill's SKILL.md names at least two siblings. The members are exactly the
    siblings it names — not every sibling present — because the claim being made
    is "this lead drives these", and only the named ones are evidence for it.
    """
    sols = []
    for root, kids in sorted(find_bundles(skills_root).items()):
        base = root.name
        rel = root.relative_to(skills_root).parts
        dom = rel[0] if rel else "core"
        candidates = [
            k for k in kids
            if k == base or k == base + "-skills" or k == base + "-agent"
            or k.replace("-skills", "") == base or k in ENTRY_NAMES
            or "orchestrator" in k
        ]
        if not candidates:
            continue

        best, best_named = None, []
        for cand in candidates:
            text = (root / "skills" / cand / "SKILL.md").read_text(
                encoding="utf-8", errors="replace")
            body = _norm(text)
            named = [k for k in kids
                     if k != cand and re.search(r"\b" + re.escape(k) + r"\b", body)]
            if len(named) > len(best_named):
                best, best_named = cand, named
        if not best or len(best_named) < 2:
            continue
        # Resolve inside this bundle's own category, so `init` under playwright-pro
        # is never confused with `init` under agenthub.
        if (dom, best) not in by_key:
            continue
        members = [m for m in best_named if (dom, m) in by_key]
        if len(members) < 2:
            continue
        sols.append({
            "name": best,
            "lead": best,
            "members": members,
            "tier": "declared",
            "dom": dom,
            "bundle": base,
            "problem": by_key[(dom, best)]["d"],
            "evidence": f"{best}/SKILL.md names {len(members)} of its siblings",
        })
    return sols


def composed_solutions(rows: list, claimed: set) -> list:
    """Candidate Solutions for categories that assert none.

    Only emitted when a category has at least four unclaimed skills spanning at
    least three lifecycle stages, so the result is a sequence of work rather than
    a pile of neighbours. One skill per stage keeps the chain readable, and the
    lead is elected by lead_score rather than picked by hand.

    These are the weakest tier and are labelled as candidates everywhere they
    appear. A composed Solution is a suggestion the graph makes; a declared one is
    a fact the repository states.
    """
    by_dom = {}
    for r in rows:
        if r["n"] in claimed:
            continue
        by_dom.setdefault(r["dom"], []).append(r)

    order = {s: i for i, (s, _) in enumerate(STAGES)}
    sols = []
    for dom, items in sorted(by_dom.items()):
        # Repeat within a category until the remainder can no longer form a
        # coherent chain. One pass per category would leave most of a 47-skill
        # category unreachable and quietly call the job done; a 47-skill category
        # genuinely contains several distinct pieces of work.
        pool = list(items)
        for _ in range(MAX_CHAINS_PER_DOM):
            if len(pool) < 4:
                break
            staged = {}
            for r in pool:
                staged.setdefault(stage_of(r["n"], r["d"]), []).append(r)
            if len(staged) < 3:
                break

            names = [r["n"] for r in pool]
            lead = max(pool, key=lambda r: (lead_score(r["n"], r["d"], names), -len(r["n"])))
            chain = []
            for st in sorted(staged, key=lambda s: order[s]):
                pick = sorted(
                    (r for r in staged[st] if r["n"] != lead["n"]),
                    key=lambda r: (-lead_score(r["n"], r["d"], names), r["n"]),
                )
                if pick:
                    chain.append(pick[0]["n"])
            chain = chain[:8]
            if len(chain) < 3:
                break
            sols.append({
                "name": lead["n"],
                "lead": lead["n"],
                "members": chain,
                "tier": "composed",
                "dom": dom,
                "problem": lead["d"],
                "evidence": f"{len(staged)} lifecycle stages present in {dom}",
            })
            spent = set(chain) | {lead["n"]}
            pool = [r for r in pool if r["n"] not in spent]
    return sols


def curated_solutions(repo_root: Path, by_name: dict, parse_frontmatter) -> list:
    """Hand-authored solutions/<name>.md, which outrank everything derived."""
    sol_dir = repo_root / "solutions"
    if not sol_dir.is_dir():
        return []
    out = []
    for p in sorted(sol_dir.glob("*.md")):
        fm = parse_frontmatter(p)
        if not fm.get("name") or not fm.get("steps"):
            continue
        members = [s["skill"] for s in fm["steps"] if s["skill"] in by_name]
        if not members:
            continue
        out.append({
            "name": fm["name"],
            "lead": fm["name"],
            "members": members,
            "tier": "curated",
            "dom": "solutions",
            "problem": fm.get("problem", ""),
            "summary": fm.get("summary", ""),
            "steps": fm["steps"],
            "evidence": f"solutions/{p.name}, composed by {fm.get('composed_by', 'a human')}",
        })
    return out


def build_solutions(repo_root: Path, rows: list, parse_frontmatter) -> tuple:
    """Return (solutions, stats). Strongest tier wins any contested lead."""
    by_name = {r["n"]: r for r in rows}
    by_key = {(r["dom"], r["n"]): r for r in rows}
    skills_root = repo_root / "skills"

    sols = curated_solutions(repo_root, by_name, parse_frontmatter)
    seen_leads = {s["lead"] for s in sols}

    for s in declared_solutions(skills_root, by_key):
        if s["lead"] not in seen_leads:
            sols.append(s)
            seen_leads.add(s["lead"])

    claimed = set(seen_leads)
    for s in sols:
        claimed.update(s["members"])

    for s in composed_solutions(rows, claimed):
        if s["lead"] not in seen_leads:
            sols.append(s)
            seen_leads.add(s["lead"])

    # A lead called `init`, `run` or `research` tells a reader nothing on its own,
    # and several of them exist. Qualify those with the bundle they lead, and only
    # those: a unique, descriptive name is left alone.
    name_counts = {}
    for r in rows:
        name_counts[r["n"]] = name_counts.get(r["n"], 0) + 1
    for s in sols:
        row = by_key.get((s["dom"], s["lead"]), {})
        # Prefer the bundle the lead actually leads; fall back to its category. A
        # qualifier that repeats the name it is qualifying ("research (research)")
        # is noise, so drop it in that case.
        qual = s.get("bundle") or row.get("bundle") or s["dom"]
        ambiguous = name_counts.get(s["lead"], 0) > 1 or s["lead"] in ENTRY_NAMES
        s["label"] = (f"{s['lead']} ({qual})"
                      if ambiguous and qual and qual != s["lead"] else s["lead"])

    rank = {"curated": 0, "declared": 1, "composed": 2}
    sols.sort(key=lambda s: (rank[s["tier"]], -len(s["members"]), s["name"]))

    reachable = set()
    for s in sols:
        reachable.add(s["lead"])
        reachable.update(s["members"])
    stats = {
        "skills": len(rows),
        "solutions": len(sols),
        "by_tier": {t: sum(1 for s in sols if s["tier"] == t)
                    for t in ("curated", "declared", "composed")},
        "in_a_solution": len(reachable),
        "unclaimed": len(rows) - len(reachable),
        "edges": sum(len(s["members"]) for s in sols),
    }
    return sols, stats


# ------------------------------------------------------------------------ layout


# The layout gets the whole frame.
#
# An earlier version reserved two rectangles for the intro copy and the detail
# panel, because the graph was a full-bleed background with the interface drawn on
# top of it. That could not be made correct: the SVG letterboxes inside its box, so
# the mapping from these coordinates to screen pixels changes with the window's
# aspect ratio, and two Solution nodes ended up underneath the panel where they
# could be seen but not clicked. The interface now occupies its own grid cells, so
# there is nothing to avoid and nothing to keep in sync.


def layout(sols: list, rows: list, width: float = 1400.0, height: float = 560.0) -> dict:
    """Place every Solution as its own legible cluster, then the long tail around them.

    This is composed, not simulated. A force simulation was the first attempt and
    it produced an even speckle of 490 dots: mathematically settled, and unreadable.
    Nothing in it said "these 54 things are the point and these 165 are context",
    because a force simulation optimises for spacing, not for meaning.

    So the geometry states the meaning directly. Each Solution is a disc whose
    radius is set by how many skills it leads. Discs are packed largest-first along
    a golden-angle spiral, which spaces them evenly without concentric banding, and
    a disc is only accepted once it clears every disc already placed and both
    interface keep-out zones. The unclaimed skills form a ring outside all of it,
    so "165 skills no Solution uses yet" is a visible fact rather than a footnote.

    Deterministic by construction: no randomness in any position, so the
    reproducibility gate compares like with like.
    """
    # The frame is 2.5:1, matching the box the graph is actually rendered into.
    # A 1000x700 frame was nearly square, so once the intro and the controls had
    # taken their share of a 900px-tall screen the graph was a 1164x445 letterbox
    # with the drawing squeezed into a 636px-wide column in the middle of it and
    # half the width unused.
    cx, cy = width / 2, height / 2

    # Members sit on a ring around their lead, and a large subset gets two rings
    # rather than one wide one.
    #
    # The size ceiling is arithmetic, not taste. The frame is 700,000 square units
    # and the two keep-out zones take 228,000 of them, leaving about 472,000 for 54
    # clusters. Circle packing tops out near 0.9 density and looks crowded well
    # before that, so at 65% each cluster can occupy pi*r^2 = 0.65*472000/54, which
    # puts r at about 42 units including its spacing margin. A single ring for a
    # 21-member Solution needed 64, so the packer could only fit everything by
    # relaxing its spacing until 63 pairs of nodes overlapped.
    def fan_rings(n: int) -> list:
        if n <= 8:
            return [(13.0 + n * 1.4, n)]
        inner = (n + 1) // 2
        return [(15.0, inner), (27.5, n - inner)]

    def fan_radius(n: int) -> float:
        return max(r for r, _ in fan_rings(n))

    ordered = sorted(sols, key=lambda s: -len(s["members"]))

    # A fixed, bounded set of candidate centres on a golden-angle spiral, all
    # inside the frame. Generating the candidates up front rather than walking
    # outward until something fits is what makes this terminate: the first version
    # walked the spiral until it left the frame and then looped forever, skipping
    # every out-of-frame point without ever exhausting its budget.
    ga = math.pi * (3 - math.sqrt(5))
    candidates = []
    for k in range(2600):
        rad = 18.0 + 4.4 * math.sqrt(k)
        ang = k * ga
        x = cx + math.cos(ang) * rad * 1.95
        y = cy + math.sin(ang) * rad * 0.80
        if 6 < x < width - 6 and 6 < y < height - 6:
            candidates.append((x, y))

    placed = []
    for s in ordered:
        fr = fan_radius(len(s["members"]))
        want = fr + 11.0
        spot = None
        # Try at full spacing, then relax. A cluster placed slightly tight is a
        # better outcome than a cluster dropped or thrown outside the frame.
        for slack in (1.0, 0.92, 0.84, 0.76, 0.68, 0.6):
            for (x, y) in candidates:
                if x - want < 4 or x + want > width - 4:
                    continue
                if y - want < 4 or y + want > height - 4:
                    continue
                if all(math.dist((x, y), (px, py)) >= (want + pr) * slack
                       for px, py, pr in placed):
                    spot = (x, y)
                    break
            if spot:
                break
        if spot is None:
            spot = candidates[min(len(placed), len(candidates) - 1)]
        placed.append((spot[0], spot[1], want))
        s["_pos"] = (spot[0], spot[1], fr)

    nodes, index = [], {}

    def add(name, kind, dom, r, x, y, sol=""):
        index[name] = len(nodes)
        nodes.append({"id": name, "kind": kind, "dom": dom, "r": r,
                      "x": round(x, 1), "y": round(y, 1), "sol": sol})

    by_name = {r["n"]: r for r in rows}
    for s in ordered:
        x, y, fr = s["_pos"]
        add(s["lead"], "lead", s["dom"], 9.5 if s["tier"] != "composed" else 7.5, x, y)
        n = len(s["members"])
        # Start each fan at a different angle so neighbouring clusters do not all
        # point their first member the same way, which would read as a pattern.
        # Rotate each fan by a per-Solution amount so neighbouring clusters do
        # not all point their first member the same way, which reads as a grid
        # artefact rather than as data. Derived from the name, not random, so it
        # is stable across builds.
        offset = (sum(ord(ch) for ch in s["lead"]) % 12) * math.tau / 12
        cursor = 0
        for ring_r, ring_n in fan_rings(n):
            for j in range(ring_n):
                m = s["members"][cursor]
                cursor += 1
                a = offset + math.tau * j / max(1, ring_n)
                if m in index:
                    continue
                add(m, "member", by_name.get(m, {}).get("dom", s["dom"]), 3.4,
                    x + math.cos(a) * ring_r, y + math.sin(a) * ring_r, s["lead"])

    # The long tail, on a ring just outside the clusters. Two interleaved radii so
    # 165 dots read as a band with depth rather than as a hard circle.
    #
    # Placed in the same stretched space the clusters were placed in, rather than by
    # multiplying an already-stretched distance a second time. Doing that put the
    # ring far outside the cluster field, and since the frame was then fitted to
    # every node including the ring, the 54 clusters were squeezed into the middle
    # 413 pixels of a 1164-pixel-wide graph.
    tail = [r for r in rows if r["n"] not in index]
    SX, SY = 1.95, 0.80
    outer = max(
        (math.hypot((x - cx) / SX, (y - cy) / SY) + r for x, y, r in placed),
        default=140.0,
    )
    for i, r in enumerate(tail):
        a = math.tau * i / max(1, len(tail)) + 0.22
        band = outer + 22.0 + (i % 3) * 9.0
        add(r["n"], "tail", r["dom"], 2.2,
            cx + math.cos(a) * band * SX, cy + math.sin(a) * band * SY)

    edges = []
    for s in sols:
        for m in s["members"]:
            if m in index and s["lead"] in index:
                edges.append((index[s["lead"]], index[m]))

    # Fit the frame to the CLUSTERS, not to every node.
    #
    # The Solutions are the subject, so they get the frame. The tail ring is
    # allowed to extend past the edges and be clipped, which is what makes it read
    # as a horizon rather than as a border drawn around the picture. Fitting to
    # every node instead handed a third of the width to 165 dots.
    pad = 16.0
    core = [n for n in nodes if n["kind"] != "tail"] or nodes
    xs = [n["x"] for n in core]
    ys = [n["y"] for n in core]
    spanx = (max(xs) - min(xs)) or 1.0
    spany = (max(ys) - min(ys)) or 1.0
    scale = min((width - 2 * pad) / spanx, (height - 2 * pad) / spany)
    ox = pad + ((width - 2 * pad) - spanx * scale) / 2 - min(xs) * scale
    oy = pad + ((height - 2 * pad) - spany * scale) / 2 - min(ys) * scale
    for n in nodes:
        n["x"] = round(n["x"] * scale + ox, 1)
        n["y"] = round(n["y"] * scale + oy, 1)
        n["r"] = round(n["r"] * max(0.7, min(1.0, scale)), 2)

    for s in sols:
        s.pop("_pos", None)

    return {"nodes": nodes, "edges": edges, "index": index,
            "leads": [s["lead"] for s in sols], "lead_set": set(s["lead"] for s in sols)}
