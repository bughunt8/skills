#!/usr/bin/env python3
"""Render assets/manifest.json into a target repository directory.

Standard library only. Deterministic: same answers plus same templates produce byte-identical output.

Placeholder syntax is {{NAME}}, and only names listed in the manifest's `placeholders` array are
substituted. That is deliberate — it leaves GitHub Actions expressions such as ${{ github.sha }}
untouched.

Usage
-----
  scaffold.py --target ./my-repo --answers answers.json
  scaffold.py --target ./my-repo --answers answers.json --dry-run
  scaffold.py --target ./my-repo --answers answers.json --only docs
  scaffold.py --print-answers-template
  scaffold.py --self-test

Exit codes
----------
  0  success
  1  refused to overwrite an existing file (use --force), or a template was missing
  2  invalid arguments or answers
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
TEMPLATES = ASSETS / "templates"
MANIFEST = ASSETS / "manifest.json"

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


# --------------------------------------------------------------------------- answers


def load_manifest(path: pathlib.Path = MANIFEST) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def answers_template(manifest: dict) -> dict:
    out = {}
    for key, spec in manifest["answers_schema"].items():
        out[key] = spec.get("default", "" if spec.get("required") else None)
    return out


def resolve(manifest: dict, answers: dict) -> dict:
    """Fill defaults, validate enums, and compute derived values."""
    schema = manifest["answers_schema"]
    resolved = {}
    problems = []

    for key, spec in schema.items():
        value = answers.get(key, spec.get("default"))
        if value in (None, "") and spec.get("required"):
            problems.append(f"missing required answer: {key} ({spec['prompt']})")
        if "enum" in spec and value not in (None, "") and value not in spec["enum"]:
            problems.append(f"{key}={value!r} is not one of {spec['enum']}")
        resolved[key] = value

    for key in answers:
        if key not in schema:
            problems.append(f"unknown answer key: {key}")

    if problems:
        raise ValueError("; ".join(problems))

    profile_name = resolved["profile"]
    profile = manifest["profiles"][profile_name]

    ctx = {
        "PROJECT_NAME": resolved["project_name"],
        "DESCRIPTION": resolved["description"],
        "OWNER": resolved["owner"],
        "LICENSE_ID": resolved["license"],
        "COPYRIGHT_HOLDER": resolved["copyright_holder"],
        "YEAR": str(datetime.date.today().year),
        "COC_CONTACT": resolved["coc_contact"],
        "DEFAULT_BRANCH": resolved["default_branch"],
        "NODE_VERSION": str(resolved["node_version"]),
        "PACKAGE_MANAGER": resolved["package_manager"],
        "PROFILE_LABEL": profile["label"],
        "RELEASE_TOOLING": resolved["release_tooling"],
    }
    for name, pattern in manifest["derived"].items():
        ctx[name] = pattern.format(**ctx)

    missing = [p for p in manifest["placeholders"] if p not in ctx]
    if missing:
        raise ValueError(f"manifest declares placeholders with no value: {missing}")

    return {"answers": resolved, "profile": profile, "profile_name": profile_name, "context": ctx}


# --------------------------------------------------------------------------- conditions


def evaluate(condition: str | None, state: dict) -> bool:
    """Evaluate a manifest `when` clause.

    Supported forms, deliberately tiny so behaviour is obvious:
      profile.<flag>          profile flag is truthy
      <answer>                answer is truthy
      not <expr>              negation of either of the above
      <answer> == <value>     string equality
      <answer> != <value>     string inequality
    """
    if not condition:
        return True

    expr = condition.strip()
    if expr.startswith("not "):
        return not evaluate(expr[4:], state)

    for op in ("==", "!="):
        if op in expr:
            left, right = (part.strip() for part in expr.split(op, 1))
            actual = str(lookup(left, state))
            return (actual == right) if op == "==" else (actual != right)

    return bool(lookup(expr, state))


def lookup(name: str, state: dict):
    if name.startswith("profile."):
        return state["profile"].get(name.split(".", 1)[1], False)
    return state["answers"].get(name, False)


# --------------------------------------------------------------------------- rendering


def render(text: str, context: dict) -> str:
    """Substitute only the known placeholder names, leaving everything else alone."""
    return PLACEHOLDER_RE.sub(lambda m: context.get(m.group(1), m.group(0)), text)


def plan(manifest: dict, state: dict, only: str | None) -> list[dict]:
    selected = []
    for entry in manifest["files"]:
        if only and entry["group"] != only:
            continue
        if not evaluate(entry.get("when"), state):
            continue
        selected.append(entry)
    order = {g["id"]: g["order"] for g in manifest["groups"]}
    selected.sort(key=lambda e: (order.get(e["group"], 99), e["dest"]))
    return selected


def write_all(entries, state, target: pathlib.Path, force: bool) -> tuple[list[str], list[str]]:
    written, refused = [], []
    for entry in entries:
        src = TEMPLATES / entry["template"]
        if not src.exists():
            raise FileNotFoundError(f"template missing: {entry['template']}")
        dest = target / entry["dest"]
        if dest.exists() and not force:
            refused.append(entry["dest"])
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write so an interrupted run cannot leave a half-rendered file.
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False,
                                        dir=dest.parent) as tmp:
            tmp.write(render(src.read_text(encoding="utf-8"), state["context"]))
            tmp_path = pathlib.Path(tmp.name)
        tmp_path.replace(dest)
        if entry.get("mode"):
            os.chmod(dest, int(entry["mode"], 8))
        written.append(entry["dest"])
    return written, refused


# --------------------------------------------------------------------------- reporting


def report(manifest, state, entries, written, refused, dry_run, fmt) -> dict:
    secrets = [s for s in manifest["required_secrets"] if evaluate(s.get("when"), state)]
    payload = {
        "profile": state["profile_name"],
        "planned": [e["dest"] for e in entries],
        "written": written,
        "refused": refused,
        "dry_run": dry_run,
        "required_secrets": secrets,
        "manual_settings": manifest["manual_settings"],
    }
    if fmt == "json":
        print(json.dumps(payload, indent=2))
        return payload

    verb = "Would write" if dry_run else "Wrote"
    print(f"Profile: {state['profile_name']} ({state['profile']['label']})")
    print(f"\n{verb} {len(entries) if dry_run else len(written)} file(s):\n")
    by_group: dict[str, list[str]] = {}
    for entry in entries:
        by_group.setdefault(entry["group"], []).append(entry["dest"])
    labels = {g["id"]: g["label"] for g in manifest["groups"]}
    for gid, dests in by_group.items():
        print(f"  {labels.get(gid, gid)}")
        for d in dests:
            print(f"    {d}")
        print()
    if refused:
        print("Refused to overwrite (re-run with --force after reviewing the diff):")
        for d in refused:
            print(f"    {d}")
        print()
    if secrets:
        print("Required secrets — set these outside version control, never in a file:")
        for s in secrets:
            print(f"    {s['name']:24} {s['purpose']}  [{s['scope']}]")
        print()
    print("Manual repository settings still to apply:")
    for item in manifest["manual_settings"]:
        print(f"    - {item}")
    return payload


# --------------------------------------------------------------------------- self-test


SAMPLE = {
    "project_name": "acme-edge",
    "description": "Edge API for the Acme platform.",
    "profile": "worker-service",
    "license": "MIT",
    "visibility": "private",
    "package_manager": "pnpm",
    "coc_contact": "conduct@example.com",
    "release_tooling": "changesets",
    "owner": "acme",
    "copyright_holder": "Acme Ltd",
    "default_branch": "main",
    "node_version": "22",
}


def self_test() -> int:
    manifest = load_manifest()
    state = resolve(manifest, dict(SAMPLE))
    failures = []

    if state["context"]["REPO"] != "acme/acme-edge":
        failures.append("derived REPO is wrong")
    if state["context"]["TEST_COMMAND"] != "pnpm test":
        failures.append("derived TEST_COMMAND is wrong")

    # Actions expressions must survive rendering untouched.
    sample = "group: ci-${{ github.workflow }} for {{PROJECT_NAME}}"
    out = render(sample, state["context"])
    if "${{ github.workflow }}" not in out or "acme-edge" not in out:
        failures.append("render() damaged a GitHub Actions expression")

    if not evaluate("profile.cloudflare", state):
        failures.append("profile.cloudflare should be true for worker-service")
    if evaluate("profile.package", state):
        failures.append("profile.package should be false for worker-service")
    if not evaluate("release_tooling == changesets", state):
        failures.append("equality condition failed")
    if evaluate("not profile.cloudflare", state):
        failures.append("negation failed")

    entries = plan(manifest, state, None)
    missing = [e["template"] for e in entries if not (TEMPLATES / e["template"]).exists()]
    if missing:
        failures.append(f"templates referenced by the manifest but not bundled: {missing}")

    dests = [e["dest"] for e in entries]
    dupes = {d for d in dests if dests.count(d) > 1}
    if dupes:
        failures.append(f"two templates target the same destination: {sorted(dupes)}")

    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        written, refused = write_all(entries, state, tmp, force=False)
        if refused:
            failures.append(f"unexpected refusals on a clean target: {refused}")
        leftovers = []
        for rel in written:
            text = (tmp / rel).read_text(encoding="utf-8")
            for name in PLACEHOLDER_RE.findall(text):
                if name in manifest["placeholders"]:
                    leftovers.append(f"{rel}:{name}")
        if leftovers:
            failures.append(f"unsubstituted placeholders remain: {leftovers[:5]}")
        if (tmp / "scripts/test").exists() and not os.access(tmp / "scripts/test", os.X_OK):
            failures.append("scripts/test was not made executable")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    for f in failures:
        print(f"FAIL: {f}")
    print(f"\nself-test: {len(entries)} files planned, {len(failures)} failure(s)")
    return 1 if failures else 0


# --------------------------------------------------------------------------- main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scaffold a repository from the bundled manifest.")
    ap.add_argument("--target", type=pathlib.Path, help="destination directory")
    ap.add_argument("--answers", type=pathlib.Path, help="JSON file of answers")
    ap.add_argument("--only", help="restrict to one manifest group (e.g. docs)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ap.add_argument("--output", choices=("text", "json"), default="text")
    ap.add_argument("--print-answers-template", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    manifest = load_manifest()

    if args.self_test:
        return self_test()

    if args.print_answers_template:
        print(json.dumps(answers_template(manifest), indent=2))
        return 0

    if not args.target or not args.answers:
        ap.error("--target and --answers are required unless using --print-answers-template "
                 "or --self-test")

    try:
        state = resolve(manifest, json.loads(args.answers.read_text(encoding="utf-8")))
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.only and args.only not in {g["id"] for g in manifest["groups"]}:
        print(f"error: unknown group {args.only!r}", file=sys.stderr)
        return 2

    entries = plan(manifest, state, args.only)

    written, refused = ([], [])
    if not args.dry_run:
        try:
            written, refused = write_all(entries, state, args.target, args.force)
        except FileNotFoundError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    report(manifest, state, entries, written, refused, args.dry_run, args.output)
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
