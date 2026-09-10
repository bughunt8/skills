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


# The order stages are TESTED in, which is not the order they happen in.
#
# These are two different questions and conflating them was a bug. Scanning in
# lifecycle order meant `build` was tested before `verify`, so `code-review`
# matched the token `code` and was classified as a build skill — the exact case the
# docstring claimed to handle. Generic stages are now tested last, and `build` last
# of all, so a specific signal always wins.
PRECEDENCE = ["route", "govern", "operate", "measure", "verify", "ship",
              "design", "spec", "research", "build"]


def _tokens(s: str) -> list:
    return [tok for tok in re.split(r"[^a-z0-9]+", _norm(s)) if tok]


class LayoutTooTight(Exception):
    """Raised when the frame cannot hold the Solutions without overlapping them."""


def stage_of(name: str, desc: str) -> str:
    """Classify a skill onto one lifecycle stage.

    Three passes, most reliable evidence first: an exact token of the name, then a
    substring of a name token, then the description. Exact tokens matter because
    substring matching on names is how `marketplace-builder` became a research
    skill: `market` is a substring of `marketplace` but not a word in it.

    Unmatched skills get "build", the least surprising default for a library that
    is mostly about making things.
    """
    keys_by_stage = dict(STAGES)
    name_tokens = _tokens(name)
    desc_text = _norm(desc)

    # A trailing plural is the same word: `saas-metrics-coach` is a measure skill,
    # and the keyword is "metric".
    exact = set(name_tokens) | {tok[:-1] for tok in name_tokens if tok.endswith("s")}
    for stage in PRECEDENCE:
        if any(k in exact for k in keys_by_stage[stage]):
            return stage
    # Substring matching, restricted twice.
    #
    # Only keywords of four characters or more, because short ones are noise inside
    # a word: "ui" is a substring of "builder", which classified
    # `marketplace-builder` as a design skill.
    #
    # And only against the last token, because these names are English compounds and
    # English compounds are head-final: the head of `marketplace-builder` is
    # "builder", so it is a build skill, even though "market" appears in it and
    # market research is a real stage. Matching any token made it a research skill.
    head = name_tokens[-1] if name_tokens else ""
    for stage in PRECEDENCE:
        if any(len(k) >= 4 and k in head for k in keys_by_stage[stage]):
            return stage
    for stage in PRECEDENCE:
        if any(k in desc_text for k in keys_by_stage[stage]):
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


def _declares(text: str, name: str) -> bool:
    """Does this SKILL.md actually reference `name` as a skill?

    A bare word in prose is not a declaration. The previous test was
    `\bname\b` anywhere in the Markdown, which let ordinary English stand in as
    evidence of orchestration: a bundle with siblings called `fix`, `run`, `report`
    or `review` qualified because its lead used those words in sentences. The tier
    is supposed to mean "the repository says so", so the reference has to look like
    a reference: a code span, a path, a bold or linked name, a bullet, or a heading.
    """
    n = re.escape(name)
    forms = [
        rf"`[^`\n]*\b{n}\b[^`\n]*`",       # `run`, `skills/run`, `/run --now`
        rf"\bskills/{n}\b",                  # skills/run
        rf"\b{n}/SKILL\.md\b",              # run/SKILL.md
        rf"/{n}\b",                          # /run as an invocation
        rf"\*\*[^*\n]*\b{n}\b[^*\n]*\*\*",  # **run**
        rf"\[[^\]\n]*\b{n}\b[^\]\n]*\]",    # [run](...)
        rf"^\s*(?:[-*+]|\d+\.)\s+\**{n}\b",   # - run
        rf"^#{{1,6}}\s+\**{n}\b",           # ## run
    ]
    return any(re.search(f, text, re.M | re.I) for f in forms)


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
        # The bundle a member skill will carry, computed exactly as the collector
        # does: the path between the category and the skill, with the conventional
        # "skills" segment dropped. For a bundle that IS the category directory,
        # such as skills/commercial, that is empty; for skills/engineering/agenthub
        # it is "agenthub". Getting this wrong silently halved the declared tier,
        # because every member key missed by one segment and resolved to nothing.
        member_bundle = "/".join(seg for seg in rel[1:] if seg != "skills")
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
            named = [k for k in kids if k != cand and _declares(text, k)]
            if len(named) > len(best_named):
                best, best_named = cand, named
        if not best or len(best_named) < 2:
            continue
        # Resolve by identity within this bundle. `init` under playwright-pro and
        # `init` under agenthub are different skills, and a name cannot tell them
        # apart.
        lead_key = f"{dom}~{member_bundle}~{best}"
        if lead_key not in by_key:
            continue
        member_keys = [f"{dom}~{member_bundle}~{m}" for m in best_named]
        member_keys = [k for k in member_keys if k in by_key]
        if len(member_keys) < 2:
            continue
        sols.append({
            "name": best,
            "lead": lead_key,
            "lead_is_skill": True,
            "members": member_keys,
            "tier": "declared",
            "dom": dom,
            "bundle": base,
            "problem": by_key[lead_key]["d"],
            "evidence": (
                f"{best}/SKILL.md references {len(member_keys)} of its siblings "
                f"as skills"
            ),
        })
    return sols


def composed_solutions(rows: list, claimed: set) -> list:
    """Candidate Solutions built from the skills no stronger tier has claimed.

    Not "categories that assert no lead", which is what this docstring used to say
    and what the code never did. A 105-skill category can hold a declared Solution
    and still contain several unrelated pieces of work; refusing to look at the
    other 98 skills because one bundle inside it documents itself would be an
    accident of shape, not a judgement. What the tier actually means is: these
    skills belong to no curated or declared Solution, and this is a plausible
    ordering of some of them.

    Only emitted when at least four unclaimed skills in a category span at least
    three lifecycle stages, so the result is a sequence of work rather than a pile
    of neighbours. One skill per stage keeps the chain readable, and the lead is
    elected by lead_score rather than picked by hand.

    This is the weakest tier and is labelled as a candidate everywhere it appears.
    A composed Solution is a suggestion; a declared one is a fact the repository
    states about itself.
    """
    by_dom = {}
    for r in rows:
        if r["key"] in claimed:
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
            # Lexical tie-break on the key, so an election between two equally
            # orchestration-shaped skills is stable across builds rather than
            # depending on collection order.
            lead = max(
                pool,
                key=lambda r: (lead_score(r["n"], r["d"], names), -len(r["n"]), r["key"]),
            )
            chain = []
            for st in sorted(staged, key=lambda s: order[s]):
                pick = sorted(
                    (r for r in staged[st] if r["key"] != lead["key"]),
                    key=lambda r: (-lead_score(r["n"], r["d"], names), r["key"]),
                )
                if pick:
                    chain.append(pick[0]["key"])
            chain = chain[:8]
            if len(chain) < 3:
                break
            sols.append({
                "name": lead["n"],
                "lead": lead["key"],
                "lead_is_skill": True,
                "members": chain,
                "tier": "composed",
                "dom": dom,
                "bundle": lead["bundle"],
                "problem": lead["d"],
                "evidence": f"{len(staged)} lifecycle stages present in {dom}",
            })
            spent = set(chain) | {lead["key"]}
            pool = [r for r in pool if r["key"] not in spent]
    return sols


def curated_solutions(repo_root: Path, by_name: dict, by_key: dict,
                      parse_frontmatter, fail) -> list:
    """Hand-authored solutions/<name>.md, which outrank everything derived.

    Two things this refuses to do quietly, both of which it used to do:

    It no longer drops a step it cannot resolve. A curated file naming a skill that
    does not exist, or naming one ambiguously, was accepted with the bad step
    silently deleted, so the page could not show the mistake and no test could
    catch it. That is now a build failure with the file and the step named.

    And it no longer claims the Solution's own name is a skill. All three curated
    Solutions are compositions, not skills: there is no `idea-to-shipped-code`
    SKILL.md. Counting those three names as covered skills inflated the coverage
    figure printed on the page by three.
    """
    sol_dir = repo_root / "solutions"
    if not sol_dir.is_dir():
        return []
    out = []
    for path in sorted(sol_dir.glob("*.md")):
        fm = parse_frontmatter(path)
        if not fm.get("name") or not fm.get("steps"):
            continue

        member_keys = []
        for step in fm["steps"]:
            nm = step.get("skill", "")
            matches = by_name.get(nm, [])
            if not matches:
                fail(
                    f"solutions/{path.name} step {nm!r} is not a skill in the "
                    f"library. Fix the name, or add the skill."
                )
            if len(matches) > 1:
                where = ", ".join(sorted(r["key"] for r in matches))
                fail(
                    f"solutions/{path.name} step {nm!r} is ambiguous: {where}. "
                    f"Qualify it, because a name does not identify a skill here."
                )
            member_keys.append(matches[0]["key"])

        # Is the Solution's own name also a skill? For these three it is not.
        own = by_name.get(fm["name"], [])
        lead_is_skill = len(own) == 1
        lead_key = own[0]["key"] if lead_is_skill else f"solution~~{fm['name']}"

        out.append({
            "name": fm["name"],
            "lead": lead_key,
            "lead_is_skill": lead_is_skill,
            "members": member_keys,
            "tier": "curated",
            "dom": "solutions",
            "bundle": "",
            "problem": fm.get("problem", ""),
            "summary": fm.get("summary", ""),
            "evidence": (
                f"solutions/{path.name}, composed by "
                f"{fm.get('composed_by', 'a human')}"
            ),
        })
    return out


def build_solutions(repo_root: Path, rows: list, parse_frontmatter, fail) -> tuple:
    """Return (solutions, stats). Strongest tier wins any contested lead.

    Everything here is keyed on identity rather than on a display name. Six names
    in this library belong to more than one skill, and two of those pairs sit in
    the same category, so a name-keyed model fused them: the graph drew one `run`
    node for two different skills, and agenthub's `init` edge terminated on
    playwright-pro's `init`.
    """
    by_key = {r["key"]: r for r in rows}
    by_name: dict = {}
    for r in rows:
        by_name.setdefault(r["n"], []).append(r)
    skills_root = repo_root / "skills"

    sols = curated_solutions(repo_root, by_name, by_key, parse_frontmatter, fail)
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

    rank = {"curated": 0, "declared": 1, "composed": 2}
    sols.sort(key=lambda s: (rank[s["tier"]], -len(s["members"]), s["name"]))

    # A lead called `init`, `run` or `research` tells a reader nothing on its own,
    # and several of them exist. Qualify a label only when its name is genuinely
    # ambiguous in the library, and never with a qualifier that repeats the name.
    for s in sols:
        qual = s.get("bundle") or s["dom"]
        ambiguous = len(by_name.get(s["name"], [])) > 1 or s["name"] in ENTRY_NAMES
        s["label"] = (
            f"{s['name']} ({qual})"
            if ambiguous and qual and qual != s["name"]
            else s["name"]
        )

    # Coverage counts skills, so it counts only identities that are skills. The
    # three curated leads are compositions rather than skills and are excluded.
    reachable = set()
    for s in sols:
        if s["lead"] in by_key:
            reachable.add(s["lead"])
        reachable.update(m for m in s["members"] if m in by_key)

    stats = {
        "skills": len(rows),
        "solutions": len(sols),
        "by_tier": {t: sum(1 for s in sols if s["tier"] == t)
                    for t in ("curated", "declared", "composed")},
        "in_a_solution": len(reachable),
        "unclaimed": len(rows) - len(reachable),
        "edges": sum(len(s["members"]) for s in sols),
        "leads_that_are_skills": sum(1 for s in sols if s.get("lead_is_skill")),
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


def _fan_rings_for(n: int) -> list:
    """Ring radii and counts for a cluster of n members. Module level so the frame
    can be sized before the clusters are placed."""
    if n <= 8:
        return [(13.0 + n * 1.4, n)]
    inner = (n + 1) // 2
    return [(15.0, inner), (27.5, n - inner)]


def _fan_radius_for(n: int) -> float:
    return max(r for r, _ in _fan_rings_for(n))


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
    #
    # The frame grows with the work it has to hold, keeping the aspect ratio so the
    # rendered box still fits it. 1400x560 comfortably holds the Solutions this
    # library currently produces; a library with three times as many would not fit,
    # and the previous behaviour was to place the extras on top of each other
    # without saying so. Area scales with the total room the clusters need, so the
    # packing stays about as dense at any size.
    need = sum((_fan_radius_for(len(s["members"])) + 11.0) ** 2 for s in sols)
    baseline = 51 * (35.0 ** 2)
    if need > baseline:
        grow = math.sqrt(need / baseline)
        width, height = width * grow, height * grow
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
    fan_rings = _fan_rings_for
    fan_radius = _fan_radius_for

    ordered = sorted(sols, key=lambda s: -len(s["members"]))

    # A fixed, bounded set of candidate centres on a golden-angle spiral, all
    # inside the frame. Generating the candidates up front rather than walking
    # outward until something fits is what makes this terminate: the first version
    # walked the spiral until it left the frame and then looped forever, skipping
    # every out-of-frame point without ever exhausting its budget.
    ga = math.pi * (3 - math.sqrt(5))
    candidates = []
    budget = max(2600, int(2600 * (width * height) / (1400.0 * 560.0)))
    for k in range(budget):
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
            # No silent fallback. This used to take candidates[len(placed)]
            # regardless of collisions, so a library that outgrew the frame produced
            # leads drawn on top of each other — at 150 Solutions, one exact
            # duplicate position; at 300, eight — and nothing said so. Overlapping
            # leads are not a cosmetic problem here: the graph is the navigation, and
            # two leads at one point means one of them cannot be clicked.
            #
            # Growing the frame is the correct response to a growing library, and it
            # is the caller's decision, so this reports rather than guesses.
            raise LayoutTooTight(
                f"no non-overlapping position for {s['name']!r} "
                f"({len(s['members'])} members, needs {want:.0f} units of room) "
                f"after placing {len(placed)} of {len(ordered)} Solutions in a "
                f"{width:.0f}x{height:.0f} frame. Increase the frame in layout()."
            )
        placed.append((spot[0], spot[1], want))
        s["_pos"] = (spot[0], spot[1], fr)

    nodes, index = [], {}

    def add(key, kind, dom, r, x, y, sol="", label=""):
        index[key] = len(nodes)
        nodes.append({"id": key, "label": label, "kind": kind, "dom": dom, "r": r,
                      "x": round(x, 1), "y": round(y, 1), "sol": sol})

    by_key = {r["key"]: r for r in rows}
    for s in ordered:
        x, y, fr = s["_pos"]
        add(s["lead"], "lead", s["dom"], 9.5 if s["tier"] != "composed" else 7.5,
            x, y, label=s.get("label", s["name"]))
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
                row = by_key.get(m, {})
                add(m, "member", row.get("dom", s["dom"]), 3.4,
                    x + math.cos(a) * ring_r, y + math.sin(a) * ring_r, s["lead"],
                    label=row.get("n", m))

    # The long tail, on a ring just outside the clusters. Two interleaved radii so
    # 165 dots read as a band with depth rather than as a hard circle.
    #
    # Placed in the same stretched space the clusters were placed in, rather than by
    # multiplying an already-stretched distance a second time. Doing that put the
    # ring far outside the cluster field, and since the frame was then fitted to
    # every node including the ring, the 54 clusters were squeezed into the middle
    # 413 pixels of a 1164-pixel-wide graph.
    tail = [r for r in rows if r["key"] not in index]
    SX, SY = 1.95, 0.80
    outer = max(
        (math.hypot((x - cx) / SX, (y - cy) / SY) + r for x, y, r in placed),
        default=140.0,
    )
    for i, r in enumerate(tail):
        a = math.tau * i / max(1, len(tail)) + 0.22
        band = outer + 22.0 + (i % 3) * 9.0
        add(r["key"], "tail", r["dom"], 2.2,
            cx + math.cos(a) * band * SX, cy + math.sin(a) * band * SY,
            label=r["n"])

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
            "leads": [s["lead"] for s in sols],
            "lead_set": set(s["lead"] for s in sols)}
