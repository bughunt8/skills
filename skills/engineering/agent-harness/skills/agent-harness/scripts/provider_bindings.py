"""Shared exact-provider bindings. Python 3.10+ and PyYAML are required."""

import hashlib
import json
import os
from pathlib import Path
import re

import yaml

MANIFEST_SCHEMA = "agent-harness/manifest.v2"
PLAN_SCHEMA = "agent-harness/plan.v2"
STATE_SCHEMA = "agent-harness/state.v2"
BINDING_SCHEMA = "agent-harness/provider.v1"
SKIP_DIRS = {".git", ".github", "node_modules", "__pycache__", ".claude-plugin",
             "expected_outputs", ".codex", ".gemini", ".hermes", ".vibe"}
DISCOVERY_SKIP = SKIP_DIRS | {"assets", "references", "scripts", "tests"}
TARGETS = ("business-growth business-operations c-level-advisor commercial "
           "compliance-os engineering engineering-team finance loop-library "
           "markdown-html marketing marketing-skill product-team productivity "
           "project-management ra-qm-team research research-ops").split()


class BindingError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key, value in node.value:
        k = loader.construct_object(key, deep=deep)
        if k in result:
            raise BindingError("duplicate YAML key: %s" % k)
        result[k] = loader.construct_object(value, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def yaml_mapping(text):
    data = yaml.load(text, Loader=UniqueLoader)
    if not isinstance(data, dict):
        raise BindingError("YAML must be a mapping")
    return data


def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise BindingError("missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise BindingError("unterminated YAML frontmatter") from exc
    return yaml_mapping("\n".join(lines[1:end]))


def checked_path(root, relative, directory=False):
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or relative.startswith("/") or
            any(x in ("", ".", "..") for x in relative.split("/"))):
        raise BindingError("unsafe checkout-relative path: %r" % relative)
    path = root
    for part in relative.split("/"):
        path = path / part
        if path.is_symlink():
            raise BindingError("symlink path refused: %s" % relative)
    if not (path.is_dir() if directory else path.is_file()):
        raise BindingError("missing file/resource: %s" % relative)
    return path


def checkout_root(value):
    root = Path(os.path.abspath(value))
    for path in (root, *root.parents):
        if path.is_symlink():
            raise BindingError("symlink checkout root refused")
    checked_path(root, "AGENTS.md")
    checked_path(root, "skills", directory=True)
    return root


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def invocation(meta, codex_path=None):
    nested = meta.get("metadata", {})
    if not isinstance(nested, dict):
        raise BindingError("metadata must be a mapping")
    values = [m["disable-model-invocation"] for m in (meta, nested)
              if "disable-model-invocation" in m]
    if any(type(v) is not bool for v in values):
        raise BindingError("disable-model-invocation must be a YAML boolean")
    if len(set(values)) > 1:
        raise BindingError("conflicting top-level/nested invocation metadata")
    disabled = bool(values and values[0])
    if codex_path is not None:
        codex = yaml_mapping(codex_path.read_text(encoding="utf-8"))
        policy = codex.get("policy", {})
        if not isinstance(policy, dict):
            raise BindingError("Codex policy must be a mapping")
        implicit = policy.get("allow_implicit_invocation", True)
        if type(implicit) is not bool or implicit == disabled:
            raise BindingError("invocation YAML/Codex disagreement")
    return "user_only" if disabled else "model_or_user"


def walk_error(error):
    raise BindingError("unreadable provider inventory: %s" % error)


def find_skills(domain_path):
    hits = []
    for root, dirs, files in os.walk(domain_path, followlinks=False, onerror=walk_error):
        # Refuse links even when they would otherwise be silently skipped.
        for name in dirs + files:
            if (Path(root) / name).is_symlink():
                raise BindingError("symlink path refused: %s" % (Path(root) / name))
        dirs[:] = sorted(d for d in dirs if d not in DISCOVERY_SKIP)
        if "SKILL.md" in files:
            hits.append((root, str(Path(root) / "SKILL.md")))
    return sorted(hits)


def file_inventory(root, skill_path):
    base = checked_path(root, skill_path, directory=True)
    files = []
    for current, dirs, names in os.walk(base, followlinks=False, onerror=walk_error):
        for name in dirs + names:
            if (Path(current) / name).is_symlink():
                raise BindingError("symlink path refused: %s" % (Path(current) / name))
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        # Generated manifests cannot hash themselves. --check binds them to
        # regenerated inventories instead. No other assets are excluded.
        if (skill_path == "skills/engineering/agent-harness/skills/agent-harness"
                and Path(current) == base / "assets"):
            dirs[:] = [d for d in dirs if d != "harnesses"]
        for name in sorted(names):
            if name.endswith((".pyc", ".pyo")):
                continue
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            checked_path(root, rel)
            suffix = path.relative_to(base).as_posix()
            role = ("skill_body" if suffix == "SKILL.md" else
                    "codex_invocation_metadata" if suffix == "agents/openai.yaml" else
                    "owned_resource")
            files.append({"path": rel, "sha256": sha256(path), "role": role})
    return sorted(files, key=lambda f: f["path"])


def registered_provider(root, skill_md, name, role):
    registry_path = root / ".agents/skill-dependencies.json"
    if not registry_path.exists() and not registry_path.is_symlink():
        return
    registry = json.loads(checked_path(root, ".agents/skill-dependencies.json")
                          .read_text(encoding="utf-8"))
    entries = registry.get("providers", []) + registry.get("auxiliary_providers", [])
    matches = [e for e in entries if e["path"] == skill_md]
    if len(matches) > 1:
        raise BindingError("duplicate registered provider path")
    for entry in matches:
        if entry["name"] != name or entry["invocation"] != role:
            raise BindingError("registered provider identity/invocation mismatch")
        required = entry.get("files", [])
        if "sha256" in entry:
            required = [{"path": skill_md, "sha256": entry["sha256"]}]
            if entry.get("codex"):
                required.append(entry["codex"])
        for item in required:
            path = checked_path(root, item["path"])
            if sha256(path) != item["sha256"]:
                raise BindingError("registered provider hash drift: %s" % item["path"])


def live_binding(root, skill_path):
    if not isinstance(skill_path, str) or not skill_path.startswith("skills/"):
        raise BindingError("legacy provider path; regenerate manifests and recompile")
    base = checked_path(root, skill_path, directory=True)
    md = checked_path(root, skill_path + "/SKILL.md")
    meta = frontmatter(md.read_text(encoding="utf-8"))
    name = meta.get("name")
    if (not isinstance(name, str) or not 1 <= len(name) <= 64
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
            or name != base.name):
        raise BindingError("provider YAML name/directory identity mismatch: %s" % skill_path)
    description = meta.get("description")
    if not isinstance(description, str) or not description.strip():
        raise BindingError("provider description must be a nonempty YAML string")
    codex_rel = skill_path + "/agents/openai.yaml"
    codex = root / codex_rel
    if codex.exists() or codex.is_symlink():
        codex = checked_path(root, codex_rel)
    else:
        codex = None
    role = invocation(meta, codex)
    registered_provider(root, skill_path + "/SKILL.md", name, role)
    return {"schema": BINDING_SCHEMA, "name": name, "skill_path": skill_path,
            "invocation": role, "files": file_inventory(root, skill_path)}


def validate_binding(root, binding, model=False):
    if not isinstance(binding, dict) or binding.get("schema") != BINDING_SCHEMA:
        raise BindingError("legacy/missing binding; regenerate manifests and recompile")
    live = live_binding(root, binding.get("skill_path", ""))
    if live != binding:
        raise BindingError("provider binding drift or forged identity/role; regenerate and recompile")
    if model and live["invocation"] == "user_only":
        raise BindingError("HUMAN-COMMAND-REQUIRED: /%s at %s/SKILL.md"
                           % (live["name"], live["skill_path"]))
    return live


def validate_tasks(root, document, schema):
    if not isinstance(document, dict) or document.get("schema") != schema:
        raise BindingError("legacy plan/state schema; recompile into a new state file; never reset old state")
    if not isinstance(document.get("tasks"), list) or not document["tasks"]:
        raise BindingError("plan/state has no tasks")
    for task in document["tasks"]:
        if not isinstance(task, dict):
            raise BindingError("invalid task binding record")
        binding = validate_binding(root, task.get("provider_binding"), model=True)
        if task.get("skill_path") != binding["skill_path"] or task.get("skill") != binding["name"]:
            raise BindingError("task/provider identity mismatch")
