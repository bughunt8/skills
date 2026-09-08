#!/usr/bin/env python3
"""Unit tests for the composition engine.

These exist because the browser tests could not catch the two worst defects this
engine has had. Those tests compared the rendered page against itself: they counted
54 lead nodes and 54 Solution cards, matched the name strings, and passed — while
the graph was drawing one node for two different skills and terminating an edge on
an unrelated skill that happened to share a name.

Counts and names cannot detect that. Identity can. So the assertions here are about
identity and topology, and they run against the engine directly rather than against
the DOM it produced.

Run: python3 tests/test_compose.py
"""

import contextlib
import importlib.util
import io
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))

import compose  # noqa: E402

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label}" + (f"\n        {detail}" if detail else ""))
        FAILURES.append(label)


def load_build():
    spec = importlib.util.spec_from_file_location("bp", SITE / "build.py")
    bp = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(bp)
    return bp


# --------------------------------------------------------------- classification


def test_classification():
    """The docstring's own example, and the compounds that used to break it.

    `code-review` returned "build" because `build` was tested before `verify` and
    `code` is a build word. `marketplace-builder` returned "research" because
    `market` is a substring of `marketplace`. Both are asserted here by name so a
    future reordering of STAGES cannot quietly undo them.
    """
    cases = {
        "code-review": "verify",            # the docstring's example
        "marketplace-builder": "build",     # market is not marketplace
        "api-design-reviewer": "verify",    # review beats design
        "saas-metrics-coach": "measure",    # a plural is the same word
        "deep-research": "research",
        "ci-cd-pipeline-builder": "ship",
        "gdpr-dsgvo-expert": "govern",
        "incident-commander": "operate",
    }
    for name, want in cases.items():
        got = compose.stage_of(name, "")
        check(f"stage_of({name}) == {want}", got == want, f"got {got}")

    # A description must never outrank the name: this is what "weighted" meant.
    check(
        "the name outranks the description",
        compose.stage_of("code-review", "helps you build and ship features") == "verify",
    )


# ------------------------------------------------------------------- identity


def test_identity(rows, sols, lay):
    """One skill, one node, and every edge lands where it was aimed."""
    keys = [r["key"] for r in rows]
    check("every skill key is unique", len(set(keys)) == len(keys))
    check(
        "every skill has exactly one graph node",
        all(r["key"] in lay["index"] for r in rows),
        f"{sum(1 for r in rows if r['key'] not in lay['index'])} missing",
    )
    ids = [n["id"] for n in lay["nodes"]]
    check("no two nodes share an id", len(set(ids)) == len(ids))

    # The topology assertion the DOM tests could not make: for every Solution, an
    # edge must exist between that Solution's lead identity and each member
    # identity. A name-keyed engine passes the count test and fails this one.
    wrong = [
        (s["lead"], m)
        for s in sols
        for m in s["members"]
        if (lay["index"][s["lead"]], lay["index"][m]) not in set(lay["edges"])
    ]
    check("every edge connects the intended identities", not wrong, str(wrong[:3]))


def test_namesakes(rows, sols, lay):
    """The six names this library reuses, asserted individually.

    Fixtures would not have caught this, because the defect only appears when two
    skills really do share a name. These are the real ones.
    """
    by_name = {}
    for r in rows:
        by_name.setdefault(r["n"], []).append(r)
    shared = {n: rs for n, rs in by_name.items() if len(rs) > 1}
    check("the library still contains namesakes to test", len(shared) >= 4,
          f"found {sorted(shared)}")

    for name, rs in sorted(shared.items()):
        nodes = [n for n in lay["nodes"] if n["id"] in {r["key"] for r in rs}]
        check(
            f"the {len(rs)} skills named {name} are {len(rs)} separate nodes",
            len(nodes) == len(rs),
            f"got {len(nodes)}",
        )

    # The specific mis-termination the review found: agenthub declares a member
    # called `init`, and so does playwright-pro. agenthub's edge must land on
    # agenthub's init.
    agenthub = next((s for s in sols if s["name"] == "agenthub"), None)
    if agenthub and any(m.endswith("~init") for m in agenthub["members"]):
        init_key = next(m for m in agenthub["members"] if m.endswith("~init"))
        check(
            "agenthub's init member is agenthub's own init",
            init_key == "engineering~agenthub~init",
            f"got {init_key}",
        )


# -------------------------------------------------------------------- curated


def test_curated(rows, sols, stats):
    """A curated lead is only counted as a skill when it is one."""
    by_key = {r["key"] for r in rows}
    curated = [s for s in sols if s["tier"] == "curated"]
    check("curated Solutions are present", len(curated) >= 1)
    for s in curated:
        claimed_skill = s.get("lead_is_skill")
        really = s["lead"] in by_key
        check(
            f"{s['name']} reports its lead honestly",
            bool(claimed_skill) == really,
            f"lead_is_skill={claimed_skill} but in library={really}",
        )

    # Coverage counts skills. Three curated leads are compositions, not skills, and
    # counting them inflated the number printed on the page.
    reachable = set()
    for s in sols:
        if s["lead"] in by_key:
            reachable.add(s["lead"])
        reachable.update(m for m in s["members"] if m in by_key)
    check(
        "coverage equals the number of distinct real skills reached",
        stats["in_a_solution"] == len(reachable),
        f'{stats["in_a_solution"]} vs {len(reachable)}',
    )
    check(
        "coverage never exceeds the library",
        stats["in_a_solution"] <= stats["skills"],
    )
    check(
        "coverage and unclaimed account for every skill",
        stats["in_a_solution"] + stats["unclaimed"] == stats["skills"],
    )


def test_curated_rejects_bad_input(rows):
    """A curated file naming a skill that does not exist must fail the build.

    It used to be accepted with the offending step deleted, which meant the page
    could not show the mistake and no gate could see it.
    """
    by_name = {}
    for r in rows:
        by_name.setdefault(r["n"], []).append(r)
    by_key = {r["key"]: r for r in rows}
    real = rows[0]["n"]

    class Boom(Exception):
        pass

    def fail(msg):
        raise Boom(msg)

    def fake_frontmatter(path):
        return {
            "name": "a-composition",
            "steps": [{"skill": real}, {"skill": "definitely-not-a-skill"}],
        }

    tmp = SITE / ".tmp-curated-test"
    (tmp / "solutions").mkdir(parents=True, exist_ok=True)
    (tmp / "solutions" / "probe.md").write_text("x", encoding="utf-8")
    try:
        try:
            compose.curated_solutions(tmp, by_name, by_key, fake_frontmatter, fail)
            check("an unresolvable curated step fails the build", False,
                  "it was accepted")
        except Boom as e:
            check("an unresolvable curated step fails the build",
                  "definitely-not-a-skill" in str(e), str(e))

        # And an ambiguous one, which is worse: it resolves, to the wrong skill.
        ambiguous = next(
            (n for n, rs in by_name.items() if len(rs) > 1), None
        )
        if ambiguous:
            def fm2(path):
                return {"name": "a-composition", "steps": [{"skill": ambiguous}]}
            try:
                compose.curated_solutions(tmp, by_name, by_key, fm2, fail)
                check("an ambiguous curated step fails the build", False,
                      f"{ambiguous} was resolved silently")
            except Boom as e:
                check("an ambiguous curated step fails the build",
                      "ambiguous" in str(e).lower(), str(e))
    finally:
        for p in sorted(tmp.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
        tmp.rmdir()


# ------------------------------------------------------------------ stability


def test_determinism(rows, sols):
    a = compose.layout(sols, rows)
    b = compose.layout(sols, rows)
    check(
        "the layout is identical when computed twice",
        [(n["id"], n["x"], n["y"]) for n in a["nodes"]]
        == [(n["id"], n["x"], n["y"]) for n in b["nodes"]],
    )


def test_tiers(sols):
    """A weaker tier must never take a lead a stronger one already holds."""
    seen = {}
    rank = {"curated": 0, "declared": 1, "composed": 2}
    dupes = []
    for s in sols:
        if s["lead"] in seen:
            dupes.append((s["lead"], seen[s["lead"]], s["tier"]))
        seen[s["lead"]] = s["tier"]
    check("no identity leads two Solutions", not dupes, str(dupes[:3]))
    check(
        "Solutions are ordered strongest tier first",
        [rank[s["tier"]] for s in sols] == sorted(rank[s["tier"]] for s in sols),
    )
    for s in sols:
        check(
            f"{s['label']} has at least two members",
            len(s["members"]) >= 2,
            f"{len(s['members'])}",
        ) if len(s["members"]) < 2 else None


def main():
    bp = load_build()
    rows = bp.collect(bp.fetch())
    sols, stats = compose.build_solutions(
        bp.REPO_ROOT, rows, bp._solution_frontmatter, bp.fail
    )
    lay = compose.layout(sols, rows)

    print(f"\n{len(rows)} skills, {len(sols)} Solutions, {len(lay['nodes'])} nodes\n")
    print("classification")
    test_classification()
    print("identity and topology")
    test_identity(rows, sols, lay)
    test_namesakes(rows, sols, lay)
    print("curated tier")
    test_curated(rows, sols, stats)
    test_curated_rejects_bad_input(rows)
    print("tiers and stability")
    test_tiers(sols)
    test_determinism(rows, sols)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} failed: {', '.join(FAILURES)}")
        return 1
    print("all composition checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
