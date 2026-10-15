#!/usr/bin/env python3
"""Bounded, read-only verification of the central registry's legacy_bindings.

Python 3.10+ and PyYAML. This is a verifier, not a Skill/Agent loader. It never
imports or executes a command, router, provider body, shell example or MCP tool.
build_records returns proposed data only; a human must review it before the
parent writes the SAME .agents/skill-dependencies.json. Hash registration does
not establish independent human execution, host registration or runtime closure.

Supported declaration syntax: inline Markdown links and full/collapsed reference
links, outside fenced code. Map links must resolve to files beneath skills/.
Unknown/directory/external targets in those declarations fail closed. HTML
anchors, autolinks and backticked text are not dispatch declarations and are
not parsed; consumer hashes detect edits but do not prove prose semantics.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import sys
from urllib.parse import unquote, urlsplit

import yaml

REGISTRY_PATH = ".agents/skill-dependencies.json"
CONSUMERS = {
    name: f"skills/engineering-team/skills/{name}/SKILL.md"
    for name in ("senior-backend", "senior-frontend", "senior-fullstack")
}
GRILLING = "skills/productivity/grilling/SKILL.md"
DOMAIN = "skills/engineering/domain-modeling/SKILL.md"
PM = {
    "command": "/cs:pm",
    "arguments": "sprint retrospective action items",
    "command_path": "skills/project-management/commands/cs-pm.md",
    "provider_path": "skills/project-management/skills/scrum-master/SKILL.md",
    "router_path": "skills/project-management/skills/pm-skills/scripts/pm_goal_router.py",
    "canonical_name": "scrum-master",
    "namespace": "project-management",
    "invocation": "user",
    "independent_human_command_required": True,
    "executed": False,
}
BLOCKED = {
    "cs-backend-engineer": "agent_definition",
    "cs-frontend-engineer": "agent_definition",
    "cs-fullstack-engineer": "agent_definition",
    "cs-grill-master": "agent_definition",
    "cs-grillmaster": "agent_definition",
    "cs-cto-advisor": "agent_definition",
    "cs-content-creator": "agent_definition",
    "cs-apple-hig": "agent_definition",
    "ra-qm-team": "domain",
    "forcing_question_patterns.md": "document",
    "/cs:backend-review": "command",
    "/cs:frontend-review": "command",
    "/cs:fullstack-review": "command",
}
HUMAN_WRAPPERS = {"grill-me", "grill-with-docs"}


class Invalid(ValueError):
    """Malformed, missing, stale or unauthorized binding."""


class UniqueLoader(yaml.SafeLoader):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if not isinstance(key, str) or key in result:
            raise Invalid(f"duplicate/non-string mapping key: {key!r}")
        result[key] = value
    return result


def _yaml_mapping(loader, node, deep=False):
    return _pairs((loader.construct_object(k, deep=deep),
                   loader.construct_object(v, deep=deep)) for k, v in node.value)


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                             _yaml_mapping)


def _yaml(text):
    try:
        return yaml.load(text, Loader=UniqueLoader)
    except (yaml.YAMLError, TypeError, RecursionError) as exc:
        raise Invalid(f"invalid YAML: {exc}") from exc


def _root(root):
    root = Path(root).absolute()
    if not root.is_dir() or root.is_symlink():
        raise Invalid(f"invalid repository root: {root}")
    return root


def checked_path(root, relative, *, skills=True):
    """Only canonical repo-relative paths; refuse every symlink component."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise Invalid(f"unsafe path: {relative!r}")
    parts = relative.split("/")
    if (relative.startswith("/") or any(p in ("", ".", "..") for p in parts)
            or any(":" in p or "\x00" in p for p in parts)
            or str(PurePosixPath(relative)) != relative
            or (skills and parts[0] != "skills")):
        raise Invalid(f"unsafe/non-skills canonical path: {relative!r}")
    out = root
    for part in parts:
        out = out / part
        if out.is_symlink():
            raise Invalid(f"symlink path refused: {relative}")
    if not out.is_file():
        raise Invalid(f"missing file/resource: {relative}")
    return out


def _text(root, path):
    return checked_path(root, path).read_text(encoding="utf-8")


def _file(root, path):
    return {"path": path, "sha256": hashlib.sha256(
        checked_path(root, path).read_bytes()).hexdigest()}


def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise Invalid("missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise Invalid("unterminated YAML frontmatter") from exc
    fm = _yaml("\n".join(lines[1:end]))
    if not isinstance(fm, dict):
        raise Invalid("frontmatter must be a mapping")
    return fm


def _identity(fm, path):
    name = fm.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        raise Invalid(f"missing/invalid frontmatter identity: {path}")
    expected = (PurePosixPath(path).parent.name if path.endswith("/SKILL.md")
                else PurePosixPath(path).stem)
    if name != expected:
        raise Invalid(f"wrong frontmatter identity: {path}: {name!r} != {expected!r}")
    return name


def _disabled(fm):
    md = fm.get("metadata", {})
    if not isinstance(md, dict):
        raise Invalid("metadata must be a mapping")
    values = [d["disable-model-invocation"] for d in (fm, md)
              if "disable-model-invocation" in d]
    if any(type(v) is not bool for v in values):
        raise Invalid("disable-model-invocation must be a YAML boolean")
    if len(set(values)) > 1:
        raise Invalid("conflicting top-level/nested invocation flags")
    return bool(values and values[0])


def _provider(root, path):
    if path.endswith("/SKILL.md"):
        if "/agents/" in path or "/commands/" in path:
            raise Invalid(f"agent/command directory cannot supply a Skill loader target: {path}")
        kind = "skill"
    elif "/agents/" in path and path.endswith(".md"):
        kind = "agent_definition"
    else:
        return {"kind": "document", "path": path, "invocation": "passive",
                "files": [_file(root, path)]}
    fm = frontmatter(_text(root, path))
    name = _identity(fm, path)
    disabled = _disabled(fm)
    files = [_file(root, path)]
    codex_path = str(PurePosixPath(path).parent / "agents/openai.yaml")
    # Presence is checked without following a symlink, including dangling ones.
    possible = root / codex_path
    if possible.parent.is_symlink():
        raise Invalid(f"symlink client metadata directory refused: {possible.parent}")
    codex_present = possible.exists() or possible.is_symlink()
    if kind == "skill" and codex_present:
        codex = _yaml(_text(root, codex_path))
        if not isinstance(codex, dict):
            raise Invalid(f"malformed Codex metadata: {codex_path}")
        interface, policy = codex.get("interface"), codex.get("policy", {})
        if not isinstance(interface, dict) or not isinstance(policy, dict):
            raise Invalid(f"malformed Codex interface/policy: {codex_path}")
        for field in ("display_name", "short_description"):
            if not isinstance(interface.get(field), str) or not interface[field]:
                raise Invalid(f"missing Codex interface.{field}: {codex_path}")
        implicit = policy.get("allow_implicit_invocation", True)
        if type(implicit) is not bool:
            raise Invalid(f"Codex invocation policy must be boolean: {codex_path}")
        if implicit == disabled:
            raise Invalid(f"Codex/frontmatter invocation disagreement: {path}")
        files.append(_file(root, codex_path))
    mode = ("host_registration_required" if kind == "agent_definition"
            else "user_only" if disabled else "model_or_user")
    return {"kind": kind, "path": path, "canonical_name": name,
            "namespace": PurePosixPath(path).parts[1], "invocation": mode,
            "deprecated": fm.get("metadata", {}).get("status") == "deprecated",
            "files": files}


def _link_path(root, source, href):
    """Normalize Markdown's legitimate ../ links, not registry paths."""
    if not isinstance(href, str) or href != href.strip() or "\\" in href:
        raise Invalid(f"unsafe Markdown target in {source}: {href!r}")
    decoded = unquote(href)
    # Encoded traversal/absolute paths are not a supported declaration syntax.
    if decoded != href:
        raise Invalid(f"encoded Markdown target refused in {source}: {href}")
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or parsed.query or href.startswith("/"):
        raise Invalid(f"non-filesystem Markdown target in {source}: {href}")
    if not parsed.path:
        if parsed.fragment:
            return None
        raise Invalid(f"empty Markdown target in {source}")
    parts = list(PurePosixPath(source).parent.parts)
    for part in parsed.path.split("/"):
        if part in ("", "."):
            raise Invalid(f"noncanonical Markdown target in {source}: {href}")
        if part == "..":
            if len(parts) <= 1:
                raise Invalid(f"Markdown path escapes skills/: {href}")
            parts.pop()
        else:
            parts.append(part)
            # Do not normalize away a symlink followed by '..'.
            if (root.joinpath(*parts)).is_symlink():
                raise Invalid(f"symlink Markdown target in {source}: {href}")
    result = "/".join(parts)
    checked_path(root, result)
    return result


def _links(root, source):
    """Return each link occurrence with a deterministic evidence ID.

    Refuse remaining bracket-style declarations instead of silently overlooking
    malformed supported syntax. Images, HTML and backticked paths are not
    provider declarations.
    """
    lines = _text(root, source).splitlines()
    visible, fence = [], None
    for no, line in enumerate(lines, 1):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token[0]
            elif fence == token[0]:
                fence = None
            continue
        if fence is None:
            visible.append((no, line))
    if fence is not None:
        raise Invalid(f"unterminated Markdown fence: {source}")
    definitions = {}
    for no, line in visible:
        m = re.fullmatch(r"\s*\[([^\]]+)\]:\s*(\S+)\s*", line)
        if m:
            key = m[1].casefold()
            if key in definitions:
                raise Invalid(f"duplicate Markdown reference ID: {source}:{key}")
            definitions[key] = m[2]
    result = []
    pattern = re.compile(r"(?<!!)\[([^\]\n]+)\]\(([^()\s]+)\)"
                         r"|(?<!!)\[([^\]\n]+)\]\[([^\]\n]*)\]")
    for no, line in visible:
        if re.fullmatch(r"\s*\[[^\]]+\]:\s*\S+\s*", line):
            continue
        for index, m in enumerate(pattern.finditer(line), 1):
            label = m[1] or m[3]
            if m[1] is not None:
                href = m[2]
            else:
                key = (m[4] or label).casefold()
                if key not in definitions:
                    raise Invalid(f"undeclared Markdown reference: {source}:{key}")
                href = definitions[key]
            path = _link_path(root, source, href)
            if path:
                result.append({"line": no, "ordinal": index, "label": label,
                               "href": href, "path": path, "instruction": line})
        rest = pattern.sub("", line)
        if re.search(r"(?<!!)\[[^\]]+\]\s*[\[(]", rest):
            raise Invalid(f"unsupported Markdown link syntax: {source}:{no}")
    return result


def _action(provider, evidence):
    if provider["kind"] == "document":
        return "passive_read"
    if provider["kind"] == "agent_definition":
        return "host_registered_agent_handoff"
    if provider["deprecated"]:
        return "manual_selection"
    # The boundary paragraph declares these two operative links, then contrasts
    # passive glossary reads and human wrappers in the same paragraph. Do not
    # classify its actual model links from those unrelated negative examples.
    if provider["path"] in (GRILLING, DOMAIN):
        return ("declared_model_route" if provider["invocation"] == "model_or_user"
                else "independent_human_handoff")
    instruction = evidence["instruction"].lower()
    if ("passive" in instruction or "not an automatic rebind" in instruction
            or "selection guidance" in instruction):
        return "manual_selection"
    if provider["invocation"] == "user_only":
        return "independent_human_handoff"
    return "declared_model_route"


def _blocked(text, caller):
    result = []
    for name, kind in sorted(BLOCKED.items()):
        # Do not mistake a filename's suffix for a different declaration.
        if re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w.-])", text):
            # Absence must be explicit in the map; a bare promise is unsafe.
            paragraphs = [p for p in text.split("\n\n") if name in p]
            if not any(re.search(r"\b(blocked|absent|no single)\b", p, re.I)
                       for p in paragraphs):
                raise Invalid(f"missing explicit blocked/manual boundary: {caller}:{name}")
            result.append({"id": caller + ":blocked:" + name, "declared_name": name,
                           "kind": kind, "status": "blocked_manual_selection",
                           "provider_path": None, "alias": False})
    own = "cs-" + caller.removeprefix("senior-") + "-engineer"
    for required in (own, "cs-grill-master"):
        if required not in {r["declared_name"] for r in result}:
            raise Invalid(f"missing historical blocked declaration: {caller}:{required}")
    return result


def _pm_record(root):
    record = dict(PM)
    cmd = _text(root, PM["command_path"])
    frontmatter(cmd)
    if (not re.search(r"^# /cs:pm(?:\s|$)", cmd, re.M) or "$ARGUMENTS" not in cmd
            or "project-management/skills/pm-skills/scripts/pm_goal_router.py" not in cmd
            or "pm-skills" not in cmd):
        raise Invalid("PM command declaration/arguments/router mismatch")
    invocations = []
    # Inspect the literal command's argv shape, not arbitrary surrounding prose.
    # shlex only tokenizes this declaration; no shell process is created.
    for block in re.findall(r"^```(?:bash|sh)\s*\n(.*?)^```\s*$", cmd, re.M | re.S):
        for line in block.splitlines():
            if "pm_goal_router.py" not in line or line.lstrip().startswith("#"):
                continue
            try:
                argv = shlex.split(line)
            except ValueError as exc:
                raise Invalid(f"malformed PM command argv: {exc}") from exc
            if len(argv) < 2 or argv[:2] != ["python3", PM["router_path"]]:
                raise Invalid("PM command must invoke the exact canonical router path")
            options = argv[2:]
            if len(options) % 2:
                raise Invalid("PM command option/value shape mismatch")
            pairs = list(zip(options[::2], options[1::2]))
            values = _pairs(pairs)
            if (set(values) - {"--repo-root", "--text", "--output"}
                    or values.get("--text") != "$ARGUMENTS"
                    or values.get("--output") != "json"
                    or ("--repo-root" in values and values["--repo-root"] != ".")):
                raise Invalid("PM command must pass one inquiry argv and the canonical root")
            invocations.append(argv)
    if len(invocations) != 1:
        raise Invalid("PM command must declare exactly one canonical router invocation")
    provider = _provider(root, PM["provider_path"])
    if (provider["kind"], provider["canonical_name"], provider["namespace"]) != (
            "skill", "scrum-master", "project-management"):
        raise Invalid("PM provider identity/namespace mismatch")
    source = _text(root, PM["router_path"])
    try:
        tree = ast.parse(source)
        candidates = [
            n.value for n in tree.body
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "SIGNALS" for t in n.targets)
        ]
        if len(candidates) != 1:
            raise Invalid("PM router must declare one literal SIGNALS mapping")
        signals = ast.literal_eval(candidates[0])
    except (SyntaxError, ValueError, TypeError, RecursionError) as exc:
        raise Invalid(f"PM router literal metadata invalid: {exc}") from exc
    if not isinstance(signals, dict) or not isinstance(signals.get("SPRINT"), dict):
        raise Invalid("PM router missing SPRINT metadata")
    sprint = signals["SPRINT"]
    if sprint.get("skill") != "scrum-master" or sprint.get("path") not in (
            "project-management/skills/scrum-master",
            "skills/project-management/skills/scrum-master"):
        raise Invalid("PM router SPRINT target/namespace mismatch")
    scores = {}
    for lane, spec in signals.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("keywords"), list):
            raise Invalid("PM router keyword metadata malformed")
        keywords = spec["keywords"]
        if not keywords or any(not isinstance(k, str) or not k for k in keywords):
            raise Invalid("PM router keywords must be nonempty strings")
        if len(set(keywords)) != len(keywords):
            raise Invalid("PM router duplicate keywords")
        scores[lane] = sum(k in PM["arguments"] for k in keywords)
    second = max((s for lane, s in scores.items() if lane != "SPRINT"), default=0)
    if scores["SPRINT"] < 2 or scores["SPRINT"] < 2 * second:
        raise Invalid("PM router literal signals do not uniquely support retrospective")
    # This is metadata inspection, deliberately not proof of the Python decision
    # function, command execution, MCP availability or an actual retrospective.
    record["verification"] = "literal_metadata_only_not_execution"
    record["files"] = [_file(root, PM[k]) for k in
                       ("command_path", "provider_path", "router_path")]
    record["provider_invocation"] = provider["invocation"]
    return record


def build_records(root):
    """Generate proposed legacy_bindings data from updated docs, without writes."""
    root = _root(root)
    records = []
    for caller, skill in CONSUMERS.items():
        info = _provider(root, skill)
        if info["canonical_name"] != caller:
            raise Invalid(f"wrong consumer identity: {caller}")
        base = str(PurePosixPath(skill).parent)
        map_path = base + "/references/composition_map.md"
        mandatory = {skill, map_path, base + "/references/workflow.md",
                     base + "/references/forcing_questions.md"}
        mandatory.update(f["path"] for f in info["files"])
        # Inventory all local linked instruction documents. Do not recursively
        # scan provider trees or interpret their executable shell examples.
        todo, seen = list(sorted(mandatory)), set()
        while todo:
            path = todo.pop()
            if path in seen:
                continue
            seen.add(path)
            if not path.endswith(".md"):
                continue
            for link in _links(root, path):
                target = link["path"]
                if target.startswith(base + "/") and target.endswith(".md"):
                    if target not in seen:
                        todo.append(target)
        docs = _text(root, map_path)
        routes = []
        for evidence in _links(root, map_path):
            path = evidence["path"]
            if any(name in evidence["label"] for name in BLOCKED):
                raise Invalid(f"phantom alias/blocked label linked to a provider: {caller}")
            provider = _provider(root, path)
            action = _action(provider, evidence)
            if (provider.get("canonical_name") in HUMAN_WRAPPERS
                    and action == "declared_model_route"):
                raise Invalid("human grill wrapper is never a model target")
            route = {
                "id": f"{caller}:L{evidence['line']}:N{evidence['ordinal']}",
                "provider": provider, "action": action, "evidence": evidence,
                "host_registration_required": provider["kind"] == "agent_definition",
                "runtime_closure_claimed": False,
            }
            if path == DOMAIN:
                if "approval" not in evidence["instruction"].lower():
                    raise Invalid(f"domain-modeling lacks independent approval boundary: {caller}")
                route["condition"] = "separate_approved_modeling_task"
            elif path == GRILLING:
                route["condition"] = "preflight_shared_understanding_required"
            elif provider.get("canonical_name") == "seo-audit":
                route["condition"] = "optional_installed_authorized_and_Q5_SEO_dependent"
            else:
                route["condition"] = "follow_exact_map_instruction_and_host_authorization"
            routes.append(route)
        actual_paths = {r["provider"]["path"] for r in routes}
        if not {GRILLING, DOMAIN} <= actual_paths:
            raise Invalid(f"missing declared grilling/domain-modeling route: {caller}")
        for required in (GRILLING, DOMAIN):
            if not any(r["provider"]["path"] == required
                       and r["action"] == "declared_model_route" for r in routes):
                raise Invalid(f"required native model route became user-only: {required}")
        records.append({
            "id": caller, "skill_path": skill, "map_path": map_path,
            "files": [_file(root, p) for p in sorted(seen)],
            "routes": routes, "blocked": _blocked(docs, caller),
            "historical_registration": "body_hash_not_independent_human_proof",
            "runtime_closure_claimed": False,
        })
    return {
        "schema_version": 1, "scope": "three_senior_consumers_and_pm_retrospective",
        "verification": "read_only_structural_registration_not_runtime_closure",
        "consumers": records, "pm_retrospective": _pm_record(root),
    }


def _differences(actual, expected, path="legacy_bindings", limit=40):
    errors = []

    def compare(a, b, where):
        if len(errors) >= limit:
            return
        if type(a) is not type(b):
            errors.append(f"{where}: wrong type")
        elif isinstance(b, dict):
            if any(not isinstance(key, str) for key in a):
                errors.append(f"{where}: non-string declaration key")
                return
            for key in sorted(set(a) - set(b)):
                errors.append(f"{where}.{key}: unexpected declaration")
            for key in sorted(set(b) - set(a)):
                errors.append(f"{where}.{key}: missing declaration")
            for key in sorted(set(a) & set(b)):
                compare(a[key], b[key], where + "." + key)
        elif isinstance(b, list):
            if len(a) != len(b):
                errors.append(f"{where}: declaration inventory length mismatch")
            for i, (aa, bb) in enumerate(zip(a, b)):
                compare(aa, bb, f"{where}[{i}]")
        elif a != b:
            errors.append(f"{where}: value/hash/declaration mismatch")

    compare(actual, expected, path)
    return errors[:limit]


def read_registry(root):
    root = _root(root)
    path = checked_path(root, REGISTRY_PATH, skills=False)
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise Invalid(f"invalid central registry JSON: {exc}") from exc


def validate(root, registry):
    """Return failures; never repair or write. Missing central field is fatal."""
    if not isinstance(registry, dict) or "legacy_bindings" not in registry:
        return ["central .agents/skill-dependencies.json missing legacy_bindings"]
    try:
        expected = build_records(root)
        return _differences(registry["legacy_bindings"], expected)
    except (ValueError, TypeError, OSError, UnicodeError, RecursionError) as exc:
        return [f"legacy bindings invalid: {exc}"]


def validate_pm(root, registry):
    """Validate the declared PM binding only; do not execute its router."""
    try:
        declared = registry["legacy_bindings"]["pm_retrospective"]
        return _differences(declared, _pm_record(_root(root)),
                            path="legacy_bindings.pm_retrospective")
    except (KeyError, ValueError, TypeError, OSError, UnicodeError, RecursionError) as exc:
        return [f"PM binding invalid: {exc}"]


def resolve_consumer(root, registry, caller, target, invoker):
    """Return ONE canonical repo-relative Skill path for declared model routes.

    caller is the exact consumer ID or path. target is an exact provider path,
    not a bare alias. invoker must be 'model', even if a human started the senior
    skill. Conditional routes remain subject to their documented approval and
    host checks; this verifier does not authorize execution.
    """
    failures = validate(root, registry)
    if failures:
        raise Invalid("; ".join(failures))
    if invoker != "model":
        raise Invalid("consumer resolver accepts declared model routes only")
    consumers = registry["legacy_bindings"]["consumers"]
    matches = [c for c in consumers if caller in (c["id"], c["skill_path"])]
    if len(matches) != 1:
        raise Invalid("missing/ambiguous exact consumer")
    routes = [r for r in matches[0]["routes"] if r["provider"]["path"] == target
              and r["action"] == "declared_model_route"]
    if not routes:
        raise Invalid("target is not a declared model route")
    for route in routes:
        provider = route["provider"]
        if (provider["kind"] != "skill" or provider["invocation"] != "model_or_user"
                or provider["canonical_name"] in HUMAN_WRAPPERS
                or provider["deprecated"]):
            raise Invalid("agent/document/user-only/manual route is not a Skill target")
    checked_path(_root(root), target)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--build-records", action="store_true",
                        help="print proposed field data only; never write the registry")
    args = parser.parse_args(argv)
    try:
        if args.build_records:
            print(json.dumps(build_records(args.root), indent=2))
            return 0
        errors = validate(args.root, read_registry(args.root))
        for error in errors:
            print("ERROR: " + error, file=sys.stderr)
        if not errors:
            print("Legacy structural bindings valid; runtime closure not claimed.")
        return bool(errors)
    except (ValueError, OSError, UnicodeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
