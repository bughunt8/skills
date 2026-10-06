#!/usr/bin/env python3
"""pm_goal_router.py — deterministic lane classifier for the project-management domain.

Scores a PM goal/inquiry against the 8 sub-skill lanes using keyword signals
(same two-signal threshold discipline as the research-ops / commercial / markdown-html
orchestrators). Emits a routing decision an agent can branch on mechanically.

Exit codes:
  0  confident route emitted (route_to set)
  2  ambiguous — ask ONE clarifying question naming the top two lanes
  3  no signal — do not guess; ask the user to restate the goal
Stdlib only. Deterministic: same text in, same route out.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import sys

SIGNALS = {
    "HEALTH": {
        "skill": "senior-pm",
        "path": "project-management/skills/senior-pm",
        "keywords": [
            "project health", "portfolio", "risk register", "risk analysis", "emv",
            "monte carlo", "executive report", "status report", "milestone", "budget",
            "resource capacity", "capacity plan", "raid", "stakeholder satisfaction",
            "program", "watermelon",
        ],
    },
    "SPRINT": {
        "skill": "scrum-master",
        "path": "project-management/skills/scrum-master",
        "keywords": [
            "sprint", "velocity", "retro", "retrospective", "ceremony", "standup",
            "scrum", "burndown", "forecast", "story points", "action item",
            "team health", "flow metrics", "cycle time", "throughput", "wip",
        ],
    },
    "JIRA": {
        "skill": "jira-expert",
        "path": "project-management/skills/jira-expert",
        "keywords": [
            "jql", "jira workflow", "jira board", "automation rule", "issue type",
            "jira filter", "jira report", "jira config", "workflow transition",
            "kanban board", "epic link",
        ],
    },
    "CONFLUENCE": {
        "skill": "confluence-expert",
        "path": "project-management/skills/confluence-expert",
        "keywords": [
            "confluence", "space", "knowledge base", "page tree", "documentation audit",
            "wiki", "page hierarchy", "content governance", "macro",
        ],
    },
    "ADMIN": {
        "skill": "atlassian-admin",
        "path": "project-management/skills/atlassian-admin",
        "keywords": [
            "permission", "sso", "saml", "provisioning", "deactivate user", "group",
            "admin", "security policy", "access control", "marketplace app", "audit log",
        ],
    },
    "TEMPLATES": {
        "skill": "atlassian-templates",
        "path": "project-management/skills/atlassian-templates",
        "keywords": [
            "template", "blueprint", "scaffold", "standardized page", "reusable layout",
            "storage format",
        ],
    },
    "MEETINGS": {
        "skill": "meeting-analyzer",
        "path": "project-management/skills/meeting-analyzer",
        "keywords": [
            "meeting", "transcript", "talk time", "speaking", "filler words",
            "interruption", "facilitation", "1:1", "one-on-one",
        ],
    },
    "COMMS": {
        "skill": "team-communications",
        "path": "project-management/skills/team-communications",
        "keywords": [
            "status update", "3p", "newsletter", "faq", "announcement",
            "stakeholder update", "incident report", "comms", "broadcast",
        ],
    },
}

SAMPLE_GOAL = (
    "our sprints feel off — velocity keeps swinging and the retro action items "
    "never get done"
)


def score(text: str) -> dict:
    low = text.lower()
    scores = {}
    hits = {}
    for lane, spec in SIGNALS.items():
        matched = [kw for kw in spec["keywords"] if kw in low]
        scores[lane] = len(matched)
        hits[lane] = matched
    return {"scores": scores, "hits": hits}


def decide(scores: dict) -> dict:
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    (top_lane, top), (second_lane, second) = ranked[0], ranked[1]
    if top == 0:
        return {"decision": "NO_SIGNAL", "exit": 3}
    if top >= 2 and (second == 0 or top >= 2 * second):
        return {"decision": "ROUTE", "lane": top_lane, "exit": 0}
    candidates = [top_lane] + ([second_lane] if second > 0 else [])
    return {"decision": "ASK", "candidates": candidates, "exit": 2}


def qualify_provider(repo_root, relative, expected_name):
    """Use this router's own checkout; never execute the selected Skill/command."""
    root = Path(repo_root).resolve(strict=True)
    installed = Path(__file__).resolve()
    trusted_root = installed.parents[5]
    expected_router = trusted_root / "skills/project-management/skills/pm-skills/scripts/pm_goal_router.py"
    if installed != expected_router or root != trusted_root:
        raise ValueError("--repo-root must match this router's own trusted checkout")
    module = root / "scripts/check_skill_dependencies.py"
    component = root
    for part in ("scripts", "check_skill_dependencies.py"):
        component = component / part
        if component.is_symlink():
            raise ValueError("trusted checkout dependency checker path is a symlink")
    if not module.is_file():
        raise ValueError("trusted checkout dependency checker is missing")
    spec = importlib.util.spec_from_file_location("_pm_dependency_metadata", module)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    provider = checker.checked_path(root, relative)
    try:
        fm = checker.frontmatter(provider)
    except checker.yaml.YAMLError as exc:
        raise ValueError("PM provider has malformed YAML metadata") from exc
    if fm.get("name") != expected_name:
        raise ValueError("PM provider identity does not match the selected lane")
    if checker.disabled(fm):
        raise ValueError("PM lane is user-only; independent human invocation required")
    client = provider.parent / "agents/openai.yaml"
    if client.parent.is_symlink():
        raise ValueError("PM provider client metadata parent is a symlink")
    if client.exists() or client.is_symlink():
        try:
            metadata = checker.codex(checker.checked_path(root, client.relative_to(root).as_posix()))
        except checker.yaml.YAMLError as exc:
            raise ValueError("PM provider has malformed client metadata") from exc
        if metadata.get("policy", {}).get("allow_implicit_invocation", True) is not True:
            raise ValueError("PM provider client policy blocks implicit model dispatch")
    legacy_path = checker.checked_path(root, "scripts/check_legacy_bindings.py")
    legacy_spec = importlib.util.spec_from_file_location("_pm_declared_binding", legacy_path)
    legacy = importlib.util.module_from_spec(legacy_spec)
    legacy_spec.loader.exec_module(legacy)
    registry = legacy.read_registry(root)
    errors = legacy.validate_pm(root, registry)
    if errors:
        raise ValueError("PM declaration is missing or stale: " + "; ".join(errors))
    return provider


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic lane router for project-management goals."
    )
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--text", help="Goal / inquiry text to classify.")
    src.add_argument("--input", help="Read goal text from a file ('-' for stdin).")
    ap.add_argument("--output", choices=["json", "human"], default="json")
    ap.add_argument("--sample", action="store_true",
                    help="Classify a built-in sample goal and exit.")
    ap.add_argument("--repo-root",
                    help="Trusted skills checkout root; verify exact live provider metadata.")
    args = ap.parse_args()

    if args.sample:
        text = SAMPLE_GOAL
    elif args.text:
        text = args.text
    elif args.input:
        text = (sys.stdin.read() if args.input == "-"
                else open(args.input, encoding="utf-8").read())
    else:
        ap.error("one of --text, --input, or --sample is required")

    result = score(text)
    verdict = decide(result["scores"])
    out = {
        "goal": text.strip()[:300],
        "scores": {k: v for k, v in result["scores"].items() if v},
        "decision": verdict["decision"],
    }
    if verdict["decision"] == "ROUTE":
        lane = verdict["lane"]
        out["route_to"] = SIGNALS[lane]["skill"]
        out["skill_path"] = "skills/" + SIGNALS[lane]["path"]
        out["provider_path"] = out["skill_path"] + "/SKILL.md"
        out["binding_verified"] = False
        out["execution_allowed"] = False
        out["matched_signals"] = result["hits"][lane]
        if args.repo_root:
            try:
                provider = qualify_provider(args.repo_root, out["provider_path"], out["route_to"])
                out["qualified_provider_path"] = str(provider)
                out["binding_verified"] = True
                # Qualified metadata is not authorization to perform operations.
                out["instruction"] = "Use the exact provider in approved scope; binding does not grant mutation authority."
            except (OSError, ValueError, ImportError, TypeError, KeyError) as exc:
                out["decision"] = "BLOCKED_PROVIDER"
                out["error"] = str(exc)
                verdict["exit"] = 4
    elif verdict["decision"] == "ASK":
        out["candidates"] = [
            {"lane": lane, "skill": SIGNALS[lane]["skill"], "score": result["scores"][lane]}
            for lane in verdict["candidates"]
        ]
        out["instruction"] = ("Ask ONE clarifying question naming both candidate lanes, "
                              "with a recommended answer. Never guess silently.")
    else:
        out["instruction"] = ("No lane signal. Ask the user to restate the goal with the "
                              "deliverable named. Do not route on fuzz.")

    if args.output == "json":
        print(json.dumps(out, indent=2))
    else:
        print(f"Decision: {out['decision']}")
        if "route_to" in out:
            print(f"Route to: {out['route_to']} ({out['skill_path']})")
            print(f"Signals:  {', '.join(out['matched_signals'])}")
        elif "candidates" in out:
            names = " vs ".join(c["skill"] for c in out["candidates"])
            print(f"Ambiguous: {names} — ask one clarifying question.")
        else:
            print("No signal — ask the user to restate the goal.")
    return verdict["exit"]


if __name__ == "__main__":
    sys.exit(main())
