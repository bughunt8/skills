#!/usr/bin/env python3
"""Read-only pinned Matt dependency validation and exact-path resolution.

Requires Python 3.10+ and PyYAML. Never invokes a skill or executes its body.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

import yaml

PIN = "24fe0ef7737efae15c87225755e9f6f5965e4888"
REPO = "https://github.com/mattpocock/skills"
ENGINEERING = (
    "ask-matt diagnosing-bugs grill-with-docs triage improve-codebase-architecture "
    "setup-matt-pocock-skills tdd to-spec to-tickets wayfinder implement implement-spec "
    "prototype research domain-modeling codebase-design code-review pr retro wizard"
).split()
PRODUCTIVITY = "grill-me grilling handoff teach to-questionnaire wait-what writing-for-agents".split()
NATIVE = {n: f"skills/{b}/{n}/SKILL.md"
          for b, names in (("engineering", ENGINEERING), ("productivity", PRODUCTIVITY))
          for n in names}
MODEL = set("diagnosing-bugs tdd prototype research domain-modeling codebase-design "
            "code-review pr wizard grilling writing-for-agents".split())
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


class Invalid(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key, value in node.value:
        k = loader.construct_object(key, deep=deep)
        if k in result:
            raise Invalid(f"duplicate YAML key: {k}")
        result[k] = loader.construct_object(value, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def json_pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise Invalid(f"duplicate JSON key: {k}")
        result[k] = v
    return result


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=json_pairs)


def checked_path(root, relative, must_exist=True):
    if not isinstance(relative, str) or "\\" in relative:
        raise Invalid(f"unsafe path: {relative!r}")
    p = PurePosixPath(relative)
    if p.is_absolute() or not p.parts or any(x in ("..", ".") for x in relative.split("/")):
        raise Invalid(f"unsafe path: {relative!r}")
    out = root
    for part in p.parts:
        out = out / part
        if out.is_symlink():
            raise Invalid(f"symlink path refused: {relative}")
    if must_exist and not out.is_file():
        raise Invalid(f"missing file/resource: {relative}")
    return out


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise Invalid(f"missing YAML frontmatter: {path}")
    try:
        stop = lines.index("---", 1)
    except ValueError as exc:
        raise Invalid(f"unterminated YAML frontmatter: {path}") from exc
    data = yaml.load("\n".join(lines[1:stop]), Loader=UniqueLoader)
    if not isinstance(data, dict):
        raise Invalid(f"frontmatter must be a mapping: {path}")
    return data


def disabled(fm):
    metadata = fm.get("metadata", {})
    if not isinstance(metadata, dict):
        raise Invalid("metadata must be a mapping")
    vals = [d["disable-model-invocation"] for d in (fm, metadata)
            if "disable-model-invocation" in d]
    if any(type(v) is not bool for v in vals):
        raise Invalid("disable-model-invocation must be a YAML boolean")
    if vals and len(set(vals)) != 1:
        raise Invalid("conflicting top-level/nested invocation metadata")
    return bool(vals and vals[0])


def codex(path):
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader)
    if not isinstance(data, dict) or not isinstance(data.get("interface"), dict):
        raise Invalid("Codex interface metadata must be a mapping")
    for field in ("display_name", "short_description"):
        if not isinstance(data["interface"].get(field), str) or not data["interface"][field]:
            raise Invalid(f"Codex interface missing {field}")
    policy = data.get("policy", {})
    if not isinstance(policy, dict):
        raise Invalid("Codex policy must be a mapping")
    if "allow_implicit_invocation" in policy and type(policy["allow_implicit_invocation"]) is not bool:
        raise Invalid("allow_implicit_invocation must be a YAML boolean")
    return data


def operative_targets(text):
    """Bounded parser for pinned source syntax, not a general prose interpreter."""
    result = set()
    pattern = r"skill tool\s+(?:twice,\s*for|with)\s+([\"`])([a-z][a-z0-9-]+)\1(?:\s+and\s+([\"`])([a-z][a-z0-9-]+)\3)?"
    for match in re.finditer(pattern, text, re.I):
        result.add(match[2])
        if match[4]:
            result.add(match[4])
    for match in re.finditer(r"\buse /([a-z][a-z0-9-]+)\b", text, re.I):
        result.add(match[1])
    return result


def cycles(graph, label):
    active, done = [], set()

    def visit(node):
        if node in active:
            raise Invalid(f"{label} cycle: {' -> '.join(active + [node])}")
        if node in done:
            return
        active.append(node)
        for target in graph.get(node, []):
            visit(target)
        active.pop()
        done.add(node)

    for node in graph:
        visit(node)


def read_registry(root):
    candidate = root / ".agents/skill-dependencies.json"
    path = checked_path(root if candidate.exists() else DEFAULT_ROOT,
                        ".agents/skill-dependencies.json")
    registry = load_json(path)
    return registry


def validate_registry(r):
    if r.get("schema_version") != 1 or r.get("upstream_commit") != PIN or r.get("upstream_repository") != REPO:
        raise Invalid("registry schema or upstream pin mismatch")
    legal = r["legal_resource"]
    if legal["source_path"] != "LICENSE" or legal["source_url"] != f"{REPO}/blob/{PIN}/LICENSE" or not re.fullmatch(r"[0-9a-f]{64}", legal["sha256"]):
        raise Invalid("license source/hash mismatch")
    entries = r.get("providers")
    if not isinstance(entries, list) or len(entries) != 27:
        raise Invalid("registry must contain exactly 27 native providers")
    by_name = {}
    for e in entries:
        name = e["name"]
        if name in by_name or name not in NATIVE:
            raise Invalid(f"duplicate or unexpected native provider: {name}")
        if e["path"] != NATIVE[name] or e["source_path"] != str(PurePosixPath(NATIVE[name]).parent):
            raise Invalid(f"wrong provider identity/path: {name}")
        if e["upstream_commit"] != PIN or e["source_url"] != f"{REPO}/blob/{PIN}/{e['path']}":
            raise Invalid(f"provider pin/source mismatch: {name}")
        expected_mode = "model_or_user" if name in MODEL else "user_only"
        if e["invocation"] != expected_mode:
            raise Invalid(f"invocation mode mismatch: {name}")
        files = e["files"]
        paths = [f["path"] for f in files]
        if len(set(paths)) != len(paths) or e["path"] not in paths or e["source_path"] + "/agents/openai.yaml" not in paths:
            raise Invalid(f"missing/duplicate registry resources: {name}")
        for f in files:
            if not f["path"].startswith(e["source_path"] + "/") or f["source_path"] != f["path"]:
                raise Invalid(f"wrong resource source path: {name}")
            if not re.fullmatch(r"[0-9a-f]{64}", f["sha256"]) or f["source_url"] != f"{REPO}/blob/{PIN}/{f['source_path']}":
                raise Invalid(f"invalid resource hash/source: {name}")
        if set(e["resources"]) != set(paths) - {e["path"], e["source_path"] + "/agents/openai.yaml"}:
            raise Invalid(f"resource inventory mismatch: {name}")
        by_name[name] = e
    if set(by_name) != set(NATIVE) or sum(len(e["files"]) for e in entries) != 79:
        raise Invalid("release file/provider closure mismatch")
    graph = {}
    for name, e in by_name.items():
        targets = []
        for edge in e["operative"]:
            target = edge["target"]
            if target not in by_name:
                raise Invalid(f"graph target missing: {name} -> {target}")
            if edge["provider_path"] != by_name[target]["path"]:
                raise Invalid(f"wrong graph provider: {name} -> {target}")
            if target not in MODEL:
                raise Invalid(f"model edge to user-only provider: {name} -> {target}")
            if edge["type"] not in ("operative_tool_call", "operative_slash_call"):
                raise Invalid(f"invalid operative edge type: {name}")
            if not edge.get("evidence_occurrences"):
                raise Invalid(f"missing edge evidence: {name} -> {target}")
            targets.append(target)
        if len(targets) != len(set(targets)):
            raise Invalid(f"duplicate graph edge: {name}")
        graph[name] = targets
        if not set(e["human_prerequisites"]) <= set(by_name):
            raise Invalid(f"human prerequisite missing: {name}")
    cycles(graph, "operative graph")
    aliases = r["aliases"]
    cycles({k: [v["target"]] for k, v in aliases.items()}, "alias")
    expected_aliases = {"grill-me-with-docs": ("grill-with-docs", NATIVE["grill-with-docs"]),
                        "setup-github-repository": ("github-repository-setup", "skills/engineering/github-repository-setup/SKILL.md")}
    if set(aliases) != set(expected_aliases):
        raise Invalid("alias identity mismatch")
    for alias, (target, path) in expected_aliases.items():
        if aliases[alias] != {"target": target, "provider_path": path, "invoker": "user", "expansion": "before_invocation"}:
            raise Invalid(f"alias identity/path or expansion mismatch: {alias}")
    auxiliary = r["auxiliary_providers"]
    expected_aux = {"github-repository-setup": "skills/engineering/github-repository-setup/SKILL.md",
                    "hybrid-research": "skills/research/research/skills/research/SKILL.md"}
    if {e["id"]: e["path"] for e in auxiliary} != expected_aux or len(auxiliary) != 2:
        raise Invalid("auxiliary provider identity/path mismatch")
    for e in auxiliary:
        expected = ("github-repository-setup", "user_only", "disable-model-invocation") if e["id"] == "github-repository-setup" else ("research", "model_or_user", None)
        if (e["name"], e["invocation"], e["invocation_metadata"]) != expected:
            raise Invalid(f"auxiliary invocation mismatch: {e['id']}")
        if not re.fullmatch(r"[0-9a-f]{64}", e["sha256"]):
            raise Invalid("invalid auxiliary body hash")
        if e["id"] == "github-repository-setup":
            pair = e["codex"]
            if pair["path"] != "skills/engineering/github-repository-setup/agents/openai.yaml" or not re.fullmatch(r"[0-9a-f]{64}", pair["sha256"]):
                raise Invalid("invalid required setup Codex metadata path/hash")
    scopes = r["caller_scopes"]
    if scopes != {"wayfinder": {"research": NATIVE["research"]},
                  "github-repository-setup": {"grilling": NATIVE["grilling"], "domain-modeling": NATIVE["domain-modeling"],
                                              "pr": NATIVE["pr"], "prototype": NATIVE["prototype"]}}:
        raise Invalid("caller scope identity/path mismatch")
    return by_name


def validate_provenance(root, e, required, legal_hash):
    directory = root / e["source_path"]
    if not required:
        return
    path = checked_path(root, e["source_path"] + "/PROVENANCE.md")
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^\| Upstream path \| `([^`]+)` \|$", text, re.M)
    permalink = f"{REPO}/tree/{PIN}/{e['source_path']}"
    if not match or match[1] != e["source_path"] or permalink not in text or f"{REPO}/commit/{PIN}" not in text:
        raise Invalid(f"provenance source path/pin mismatch: {e['name']}")
    for filename in ("LICENSE.upstream", "ATTRIBUTION.md", ".vendor-owned.json"):
        checked_path(root, e["source_path"] + "/" + filename)
    license_bytes = (directory / "LICENSE.upstream").read_bytes()
    prefix = (f"Vendored from {REPO} at commit {PIN}.\n"
              f"Original licence text follows, unmodified.\n{'-' * 76}\n\n").encode("utf-8")
    # The importer adds an attribution preface; hash the unmodified notice after it.
    if license_bytes.startswith(prefix):
        license_bytes = license_bytes[len(prefix):]
    if hashlib.sha256(license_bytes).hexdigest() != legal_hash:
        raise Invalid(f"upstream MIT notice/hash mismatch: {e['name']}")
    attribution = (directory / "ATTRIBUTION.md").read_text(encoding="utf-8")
    if REPO not in attribution or PIN not in attribution:
        raise Invalid(f"attribution pin/source mismatch: {e['name']}")
    ownership = load_json(directory / ".vendor-owned.json")
    if not isinstance(ownership, dict) or ownership.get("source") != "mattpocock-" + e["name"] or ownership.get("paths") != [""]:
        raise Invalid(f"invalid importer ownership record: {e['name']}")
    # Empty target denotes this one narrowly scoped root, not an unsafe file path.


def imported(root, entries):
    if any((root / e["source_path"] / marker).exists()
           for e in entries for marker in ("PROVENANCE.md", ".vendor-owned.json")):
        return True
    manifest = root / "skills/vendor.manifest.json"
    if manifest.exists():
        sources = load_json(checked_path(root, "skills/vendor.manifest.json")).get("sources", [])
        return any(s.get("repo", "").rstrip("/") == REPO for s in sources)
    return False


def catalog(root, requested):
    found = {}
    for base, dirs, files in os.walk(root / "skills", followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != ".git" and not (Path(base) / d).is_symlink())
        if "SKILL.md" not in files:
            continue
        relative = (Path(base) / "SKILL.md").relative_to(root).as_posix()
        path = checked_path(root, relative)
        # Parse YAML names, including quoted scalars with trailing comments.
        # The deliberate malformed fixture is not a provider. Fail closed if
        # an unreadable frontmatter visibly claims this requested identity.
        try:
            fm = frontmatter(path)
        except (Invalid, yaml.YAMLError) as exc:
            raw = path.read_text(encoding="utf-8")
            pattern = rf"^name:\s*[\"']?{re.escape(requested)}(?:[\"'\s#]|$)"
            if re.search(pattern, raw, re.M):
                raise Invalid(f"unreadable potential provider: {relative}: {exc}") from exc
            continue
        name = fm.get("name")
        if name != requested:
            continue
        found.setdefault(name, []).append(relative)
    return found


def check(root, r, require_provenance=False):
    by_name = validate_registry(r)
    errors = []
    require_provenance = require_provenance or imported(root, r["providers"])
    manifest = root / "skills/vendor.manifest.json"
    if require_provenance and manifest.exists():
        sources = load_json(checked_path(root, "skills/vendor.manifest.json")).get("sources", [])
        for name, e in by_name.items():
            matches = [s for s in sources if s.get("id") == "mattpocock-" + name]
            if len(matches) != 1:
                errors.append(f"import manifest source missing/duplicate: {name}")
                continue
            s = matches[0]
            expected_mapping = [{"from": e["source_path"], "to": "", "kind": "skill"}]
            if (s.get("repo", "").rstrip("/") != REPO or s.get("pinned_commit") != PIN
                    or s.get("expected_commit") != PIN or s.get("ref") != "v1.3.1"
                    or s.get("dest") != e["source_path"] or s.get("paths") != expected_mapping):
                errors.append(f"import manifest source path/pin mismatch: {name}")
    for name, e in by_name.items():
        try:
            for f in e["files"]:
                path = checked_path(root, f["path"])
                if hashlib.sha256(path.read_bytes()).hexdigest() != f["sha256"]:
                    raise Invalid(f"file hash mismatch: {f['path']}")
            fm = frontmatter(checked_path(root, e["path"]))
            if fm.get("name") != name or Path(e["path"]).parent.name != name:
                raise Invalid(f"wrong provider identity: {name}")
            is_disabled = disabled(fm)
            meta = codex(checked_path(root, e["source_path"] + "/agents/openai.yaml"))
            implicit = meta.get("policy", {}).get("allow_implicit_invocation", True)
            if is_disabled != (e["invocation"] == "user_only") or implicit == is_disabled:
                raise Invalid(f"invocation YAML/Codex pair mismatch: {name}")
            if name in MODEL and ("disable-model-invocation" in fm or "policy" in meta):
                raise Invalid(f"model defaults must be omitted: {name}")
            text = (root / e["path"]).read_text(encoding="utf-8")
            expected = {edge["target"] for edge in e["operative"]}
            if operative_targets(text) != expected:
                raise Invalid(f"graph/body mismatch: {name}")
            lines = text.splitlines()
            for edge in e["operative"]:
                for ev in edge["evidence_occurrences"]:
                    line = ev["line"]
                    if type(line) is not int or not 1 <= line <= len(lines) or lines[line - 1] != ev["text"]:
                        raise Invalid(f"graph evidence mismatch: {name}")
                    if edge["target"] not in operative_targets(ev["text"]):
                        raise Invalid(f"graph evidence target mismatch: {name}")
                    if ev["source_url"] != e["source_url"] + f"#L{line}":
                        raise Invalid(f"graph evidence source mismatch: {name}")
            validate_provenance(root, e, require_provenance, r["legal_resource"]["sha256"])
        except (Invalid, yaml.YAMLError, OSError, ValueError) as exc:
            errors.append(str(exc))
    for e in r["auxiliary_providers"]:
        if (root / e["path"]).exists():
            try:
                path = checked_path(root, e["path"])
                fm = frontmatter(path)
                if fm.get("name") != e["name"] or hashlib.sha256(path.read_bytes()).hexdigest() != e["sha256"]:
                    raise Invalid(f"wrong auxiliary provider/hash: {e['id']}")
                if disabled(fm) != (e["invocation"] == "user_only"):
                    raise Invalid(f"auxiliary invocation mismatch: {e['id']}")
                if e["invocation_metadata"]:
                    if fm.get("disable-model-invocation") is not True or "disable-model-invocation" in fm.get("metadata", {}):
                        raise Invalid("top-level human-only setup metadata required")
                    if not isinstance(fm.get("argument-hint"), str):
                        raise Invalid("top-level setup argument-hint required")
                    pair = e["codex"]
                    pair_path = checked_path(root, pair["path"])
                    if hashlib.sha256(pair_path.read_bytes()).hexdigest() != pair["sha256"]:
                        raise Invalid("setup Codex metadata hash mismatch")
                yaml_path = path.parent / "agents/openai.yaml"
                if yaml_path.exists():
                    meta = codex(checked_path(root, yaml_path.relative_to(root).as_posix()))
                    if meta.get("policy", {}).get("allow_implicit_invocation", True) == disabled(fm):
                        raise Invalid(f"auxiliary YAML/Codex pair mismatch: {e['id']}")
            except (Invalid, yaml.YAMLError, OSError, ValueError) as exc:
                errors.append(str(exc))
    plugin = root / ".claude-plugin/plugin.json"
    if plugin.exists():
        p = load_json(checked_path(root, ".claude-plugin/plugin.json"))
        if p.get("version") != "1.3.1" or sorted(p.get("skills", [])) != sorted("./" + e["source_path"] for e in r["providers"]):
            errors.append("release manifest closure mismatch")
    return errors


def resolve(root, r, name, invoker="user", caller=None):
    by_name = validate_registry(r)
    # Check everything before resolving: no successful routing through a broken bundle.
    errors = check(root, r)
    if errors:
        raise Invalid("dependency check failed: " + "; ".join(errors))
    if name.startswith("/"):
        name = name[1:]
    alias = r["aliases"].get(name)
    if alias:
        if invoker != "user":
            raise Invalid(f"model invocation refused: human-only alias {name}")
        if catalog(root, name).get(name):
            raise Invalid(f"alias cannot also be a wrapper/provider: {name}")
        name = alias["target"]
    choices = [e for e in r["providers"] + r["auxiliary_providers"] if e["name"] == name]
    if not choices:
        raise Invalid(f"unregistered provider: {name}")
    actual = catalog(root, name).get(name, [])
    if invoker == "model" and len(choices) == 1 and choices[0]["invocation"] == "user_only":
        raise Invalid(f"model invocation refused: user-only {name}")
    scope = alias["provider_path"] if alias else (
        r["caller_scopes"].get(caller, {}).get(name) if caller else None)
    # Registered research collision remains ambiguous even in a partial fixture.
    if len(choices) > 1 or len(actual) > 1:
        if not scope:
            if name == "research":
                raise Invalid(f"ambiguous {name}: caller scope required; use --caller wayfinder for Matt research")
            raise Invalid(f"ambiguous provider identity: {name}: explicit registered alias or caller scope required")
        choices = [e for e in choices if e["path"] == scope]
    if len(choices) != 1:
        raise Invalid(f"wrong provider scope: {name}")
    e = choices[0]
    path = checked_path(root, e["path"])
    if e["path"] not in actual:
        raise Invalid(f"wrong provider identity/path: {name}")
    if invoker == "model" and e["invocation"] == "user_only":
        raise Invalid(f"model invocation refused: user-only {name}")
    if invoker == "model" and caller:
        if caller not in by_name and caller not in ("github-repository-setup",):
            raise Invalid(f"unregistered caller: {caller}")
        caller_entry = by_name.get(caller) or next(x for x in r["auxiliary_providers"] if x["name"] == caller)
        checked_path(root, caller_entry["path"])
        targets = {edge["target"] for edge in by_name.get(caller, {}).get("operative", [])}
        targets.update(r["caller_scopes"].get(caller, {}))
        if name not in targets:
            # Wayfinder Notes may request additional exact, model-invoked providers.
            if caller != "wayfinder" or name == caller:
                raise Invalid(f"caller graph/scope does not authorize {caller} -> {name}")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--resolve", metavar="NAME")
    parser.add_argument("--invoker", choices=("user", "model"), default="user")
    parser.add_argument("--caller", metavar="NAME")
    parser.add_argument("--require-provenance", action="store_true",
                        help="require importer evidence even without detected import markers")
    args = parser.parse_args(argv)
    try:
        if args.root.is_symlink():
            raise Invalid("symlink root refused")
        root = args.root.resolve(strict=True)
        r = read_registry(root)
        if args.resolve:
            if args.require_provenance:
                errors = check(root, r, True)
                if errors:
                    raise Invalid("; ".join(errors))
            print(resolve(root, r, args.resolve, args.invoker, args.caller))
        else:
            errors = check(root, r, args.require_provenance)
            if errors:
                for error in errors:
                    print("ERROR: " + error, file=sys.stderr)
                return 1
            print("OK: 27 native providers, 79 pinned files, invocation pairs and operative graph validated")
            print("Static check only; runtime loader, authorization and external capabilities are not enforced.")
        return 0
    except (Invalid, yaml.YAMLError, OSError, ValueError, KeyError, TypeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
