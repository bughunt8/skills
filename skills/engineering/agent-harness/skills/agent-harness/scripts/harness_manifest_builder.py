#!/usr/bin/env python3
"""Build a domain harness manifest: scan a domain folder's skills and emit the
machine-readable inventory (skills, tools, verification checks, agentic signals)
that goal_compiler.py and loop_controller.py consume.

Requires PyYAML. Deterministic: same tree in, same manifest out (modulo the
generated_at stamp, which --no-timestamp suppresses for diff-stable output).

Usage:
  python3 harness_manifest_builder.py --domain engineering --repo-root . --json
  python3 harness_manifest_builder.py --all --repo-root . --out-dir assets/harnesses --no-timestamp
  python3 harness_manifest_builder.py --sample
"""

import argparse
import datetime
import json
import os
import re
import sys
import shlex
import yaml
from pathlib import Path

from provider_bindings import (BindingError, MANIFEST_SCHEMA, TARGETS,
                               checkout_root, checked_path, find_skills,
                               frontmatter, live_binding)

SCHEMA = MANIFEST_SCHEMA

# Signal regexes: cheap, static evidence that a skill already carries agentic
# structure. Matched case-insensitively against the SKILL.md body.
SIGNALS = {
    "goal_intake": r"forcing[- ]question|before starting|intake|clarify(?:ing)? question",
    "refusal_gate": r"refus(?:e|al)|exit(?:s|ed)? (?:code )?[1-9]|hard rule|NO-GO",
    "verification": r"verif(?:y|ication|iable)|checklist|--sample|exit 0|definition of done",
    "loop_discipline": r"\bretry\b|\biterat(?:e|ion)|stop condition|max attempts|budget|until",
    "close_out": r"close[- ]?(?:the[- ])?loop|handoff|hand-off|state persist|done when|completion",
}

LOOP_DEFAULTS = {
    "max_attempts_per_task": 3,
    "max_loop_iterations": 12,
    "escalate_on": [
        "attempts_exhausted",
        "no_verification_available",
        "destructive_or_irreversible_action",
        "goal_drift_detected",
    ],
}


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def truncate_words(text, limit):
    """Cap at `limit` chars, cutting on a word boundary with an ellipsis marker."""
    if len(text) <= limit:
        return text
    cut = text[:limit - 2]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + " …"


def parse_frontmatter(text):
    return frontmatter(text)


def scan_skill(skill_dir, skill_md, repo_root):
    rel_dir = Path(skill_dir).relative_to(repo_root).as_posix()
    binding = live_binding(Path(repo_root), rel_dir)
    text = read_text(skill_md)
    meta = parse_frontmatter(text)
    body = text.lower()
    hashes = {f["path"]: f["sha256"] for f in binding["files"]}

    tools = []
    scripts_dir = os.path.join(skill_dir, "scripts")
    script_paths = []
    if os.path.isdir(scripts_dir):
        for fn in sorted(os.listdir(scripts_dir)):
            if fn.endswith(".py"):
                script_paths.append(os.path.join(scripts_dir, fn))
    # Root-level scripts (older layout).
    for fn in sorted(os.listdir(skill_dir)):
        if fn.endswith(".py"):
            script_paths.append(os.path.join(skill_dir, fn))

    for sp in script_paths:
        rel = Path(sp).relative_to(repo_root).as_posix()
        if (rel_dir == "skills/engineering/agent-harness/skills/agent-harness"
                and Path(sp).name == "provider_bindings.py"):
            continue  # Bound module resource, not an executable CLI tool.
        src = read_text(sp)
        tools.append({
            "script": rel,
            "sha256": hashes[rel],
            "wired": os.path.basename(sp) in text,
            "supports_sample": "--sample" in src,
            "verification": build_checks(rel, src),
        })

    signals = {k: bool(re.search(rx, body)) for k, rx in SIGNALS.items()}
    return {
        "name": meta["name"],
        "path": rel_dir,
        "invocation": binding["invocation"],
        "provider_binding": binding,
        "description": truncate_words(meta["description"], 600),
        "tools": tools,
        "agentic_signals": signals,
        "references": [f["path"] for f in binding["files"]
                       if f["path"].startswith(rel_dir + "/references/")],
    }


def build_checks(rel_script, src):
    checks = [{"cmd": "python3 %s --help" % shlex.quote(rel_script), "expect_exit": 0,
               "kind": "smoke"}]
    if "--sample" in src:
        checks.append({"cmd": "python3 %s --sample" % shlex.quote(rel_script),
                       "expect_exit": 0, "kind": "sample"})
    return checks


def build_manifest(domain_path, repo_root, timestamp=True):
    domain = Path(domain_path).relative_to(Path(repo_root) / "skills").as_posix()
    skills = [scan_skill(d, s, repo_root) for d, s in find_skills(domain_path)]
    manifest = {
        "schema": SCHEMA,
        "domain": domain,
        "skill_count": len(skills),
        "loop_defaults": LOOP_DEFAULTS,
        "skills": skills,
    }
    if timestamp:
        manifest["generated_at"] = (
            datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"))
    return manifest


SAMPLE_MANIFEST = {
    "schema": SCHEMA,
    "domain": "engineering",
    "skill_count": 1,
    "loop_defaults": LOOP_DEFAULTS,
    "skills": [{
        "name": "slo-architect",
        "path": "skills/engineering/slo-architect/skills/slo-architect",
        "invocation": "model_or_user",
        "provider_binding": {
            "schema": "agent-harness/provider.v1",
            "name": "slo-architect",
            "skill_path": "skills/engineering/slo-architect/skills/slo-architect",
            "invocation": "model_or_user",
            "files": [{
                "path": "skills/engineering/slo-architect/skills/slo-architect/SKILL.md",
                "sha256": "0" * 64, "role": "skill_body",
            }],
        },
        "description": "Design SLOs/SLIs and error budgets per the Google SRE Workbook...",
        "tools": [{
            "script": "skills/engineering/slo-architect/skills/slo-architect/scripts/error_budget_calculator.py",
            "sha256": "0" * 64,
            "wired": True,
            "supports_sample": True,
            "verification": [
                {"cmd": "python3 skills/engineering/slo-architect/skills/slo-architect/scripts/error_budget_calculator.py --help",
                 "expect_exit": 0, "kind": "smoke"},
                {"cmd": "python3 skills/engineering/slo-architect/skills/slo-architect/scripts/error_budget_calculator.py --sample",
                 "expect_exit": 0, "kind": "sample"},
            ],
        }],
        "agentic_signals": {
            "goal_intake": True, "refusal_gate": True, "verification": True,
            "loop_discipline": True, "close_out": True,
        },
        "references": ["skills/engineering/slo-architect/skills/slo-architect/references/error_budget.md"],
    }],
}


def main():
    ap = argparse.ArgumentParser(
        description="Scan a domain folder and emit its agent-harness manifest.")
    ap.add_argument("--domain", action="append", default=[],
                    help="Domain name under checkout-root/skills (repeatable).")
    ap.add_argument("--all", action="store_true",
                    help="Build the 18 existing committed domain targets.")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--out-dir", help="Write <domain>.json per domain here.")
    ap.add_argument("--json", action="store_true",
                    help="Print manifest(s) to stdout as JSON.")
    ap.add_argument("--no-timestamp", action="store_true",
                    help="Omit generated_at for diff-stable committed manifests.")
    ap.add_argument("--check", action="store_true",
                    help="Read-only comparison with committed assets; never writes.")
    ap.add_argument("--sample", action="store_true",
                    help="Print an example manifest and exit 0.")
    args = ap.parse_args()

    if args.sample:
        # Illustrative inventory only, not a dispatchable binding.
        SAMPLE_MANIFEST["example_only"] = True
        print(json.dumps(SAMPLE_MANIFEST, indent=2))
        return 0

    repo_root = checkout_root(args.repo_root)
    targets = list(args.domain)
    if args.all:
        targets.extend(TARGETS)
    if args.check and not targets:
        targets.extend(TARGETS)
    if not targets:
        ap.error("provide --domain, --all, or --sample")

    results = []
    for t in sorted(set(targets)):
        if t not in TARGETS:
            raise BindingError("unsupported domain name: %s" % t)
        dp = checked_path(repo_root, "skills/" + t, directory=True)
        manifest = build_manifest(dp, repo_root, timestamp=not (args.no_timestamp or args.check))
        results.append(manifest)
        if args.check:
            out_dir = Path(args.out_dir) if args.out_dir else (
                repo_root / "skills/engineering/agent-harness/skills/agent-harness/assets/harnesses")
            out = out_dir / (t + ".json")
            if out.is_symlink() or not out.is_file() or out.read_text(encoding="utf-8") != (
                    json.dumps(manifest, indent=2) + "\n"):
                raise BindingError("committed manifest drift: %s; regenerate with --all --no-timestamp" % out)
        elif args.out_dir:
            os.makedirs(args.out_dir, exist_ok=True)
            slug = t.rstrip("/").replace(os.sep, "-")
            out = os.path.join(args.out_dir, "%s.json" % slug)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, sort_keys=False)
                f.write("\n")
            print("wrote %s (%d skills)" % (out, manifest["skill_count"]),
                  file=sys.stderr)

    if args.check:
        print("checked %d manifests: no drift" % len(results))
    elif args.json or not args.out_dir:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (BindingError, OSError, ValueError, yaml.YAMLError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        sys.exit(7)
