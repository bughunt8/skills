#!/usr/bin/env python3
"""Validate a scaffolded repository's structure and catch the traps that break it silently.

Standard library only. Deterministic. No network access.

Checks
------
Presence
  Required artifacts exist in one of the locations GitHub actually searches
  (.github/ -> root -> docs/), and LICENSE exists at root because it CANNOT be inherited from an
  organization default community health file.

Structural traps
  1. Every workflow declares `permissions:`.
  2. No action is referenced by a bare tag — a SHA is the only immutable reference.
  3. No workflow combines `pull_request_target` with checking out the PR head.
  4. Every pull-request-triggered workflow sets `concurrency`.
  5. `.env` is ignored and `.env.example` is not; same for `.dev.vars`.
  6. `.github/ISSUE_TEMPLATE/config.yml` exists whenever the directory does.
  7. No unresolved scaffold marker remains.
  8. Issue forms do not rely on `required: true` in a private repository without saying so.
  9. No committed `.env` or `.dev.vars` file.

Usage
-----
  validate_repo.py [--root .] [--visibility private|public] [--output text|json] [--require-agentic]
  validate_repo.py --self-test

Exit codes
----------
  0  no errors        1  at least one error        2  invalid arguments
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import pathlib
import re
import shutil
import sys
import tempfile

# name -> locations searched, in GitHub's own order
HEALTH_FILES = {
    "README.md": [".github", ".", "docs"],
    "CONTRIBUTING.md": [".github", ".", "docs"],
    "CODE_OF_CONDUCT.md": [".github", ".", "docs"],
    "SECURITY.md": [".github", ".", "docs"],
    "SUPPORT.md": [".github", ".", "docs"],
}
ROOT_ONLY = ["LICENSE"]  # cannot be inherited from an org .github repository
OTHER_REQUIRED = [
    "AGENTS.md",
    ".gitignore",
    ".github/pull_request_template.md",
    ".github/dependabot.yml",
]

USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)", re.M)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SCAFFOLD_MARKERS = ("REPLACE-WITH-CANONICAL-TEXT", "SCAFFOLD-PIN-SHA")


def extract_regex_literals(text: str) -> list[str]:
    """Return the source of every `/pattern/flags` literal bound to a `pattern` key."""
    return re.findall(r"pattern:\s*/(.*?)/[gimsuy]*", text)


def regex_matches(text: str, pattern: str) -> bool:
    """Case-insensitive search that treats an unparseable pattern as no match."""
    try:
        return re.search(pattern, text, re.I) is not None
    except re.error:
        return False


def supported_regex(pattern: str) -> bool:
    r"""Check common regex syntax using Python's re only as a syntax check.

    Allow literals, the any-character metacharacter, character classes,
    anchors, *, +, ?, {n}, {n,m}, capturing groups, non-capturing groups,
    lookaheads and alternation. Allow d, w, s, b, S and the control
    escapes n, r, t, f and v, plus escaped punctuation. JavaScript RegExp
    is the matching authority. This check cannot detect matching differences:
    $ matches before a trailing newline in Python but not in JavaScript,
    \d and \w are Unicode-aware in Python and ASCII-only in JavaScript, and
    the two engines disagree on which Unicode code points count as whitespace.
    This does not validate the full JavaScript RegExp dialect.
    """
    if not isinstance(pattern, str):
        return False
    index = 0
    in_class = False
    quantified = False
    while index < len(pattern):
        char = pattern[index]
        if char == "\\":
            index += 1
            if index == len(pattern):
                return False
            escaped = pattern[index]
            if escaped not in "dwsbSnrtfv" and (escaped.isalnum() or escaped == "_"):
                return False
            quantified = False
        elif in_class:
            if char == "]":
                in_class = False
        elif char == "[":
            if pattern.startswith("[]", index) or pattern.startswith("[^]", index):
                return False
            in_class = True
            quantified = False
        elif pattern.startswith("(?", index):
            if pattern[index:index + 3] not in ("(?:", "(?=", "(?!"):
                return False
            index += 2
            quantified = False
        elif char in "*+?{":
            if quantified:
                return False
            if char == "{":
                counted = re.match(r"\{[0-9]+(?:,[0-9]*)?\}", pattern[index:])
                if counted is None:
                    return False
                index += len(counted.group()) - 1
            quantified = True
        elif char == "}":
            return False
        else:
            quantified = False
        index += 1
    try:
        re.compile(pattern)
    except (re.error, OverflowError):
        return False
    return True


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, m: str) -> None:
        self.errors.append(m)

    def warn(self, m: str) -> None:
        self.warnings.append(m)


def found_in(root: pathlib.Path, name: str, locations) -> str | None:
    for loc in locations:
        candidate = root / loc / name if loc != "." else root / name
        if candidate.is_file():
            return candidate.relative_to(root).as_posix()
    return None


def check_presence(root: pathlib.Path, rep: Report) -> None:
    for name, locations in HEALTH_FILES.items():
        if not found_in(root, name, locations):
            rep.error(f"missing {name} (searched {', '.join(locations)})")
    for name in ROOT_ONLY:
        if not (root / name).is_file():
            rep.error(f"missing {name} at the repository root — it cannot be inherited from an "
                      "organization default community health file")
    for rel in OTHER_REQUIRED:
        if not (root / rel).is_file():
            rep.error(f"missing {rel}")

    issue_dir = root / ".github" / "ISSUE_TEMPLATE"
    if issue_dir.is_dir():
        if not (issue_dir / "config.yml").is_file():
            rep.error(".github/ISSUE_TEMPLATE/ exists without config.yml — every surveyed repo "
                      "with this directory ships one; without it, blank issues stay enabled and "
                      "questions land in the tracker")
        forms = sorted(issue_dir.glob("*.yml")) + sorted(issue_dir.glob("*.yaml"))
        if len(forms) <= 1:
            rep.warn(".github/ISSUE_TEMPLATE/ has no issue forms besides config.yml")
    else:
        rep.warn("no .github/ISSUE_TEMPLATE/ directory")

    if (root / ".github" / "PULL_REQUEST_TEMPLATE").is_dir():
        rep.warn("a PULL_REQUEST_TEMPLATE/ directory is present; selection requires a hand-built "
                 "?quick_pull=1&template=... URL, so document those URLs in CONTRIBUTING.md")


def check_workflows(root: pathlib.Path, rep: Report) -> None:
    wf_dir = root / ".github" / "workflows"
    if not wf_dir.is_dir():
        rep.warn("no .github/workflows/ directory")
        return

    files = sorted(list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml")))
    if not files:
        rep.warn(".github/workflows/ contains no workflow files")

    for path in files:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")

        if not re.search(r"^permissions:", text, re.M):
            rep.error(f"{rel}: no top-level `permissions:` — the workflow inherits the default "
                      "token scope")

        # A freshly scaffolded workflow carries the pin marker. Report that once instead of
        # repeating the same finding for every action in the file.
        awaiting_pins = "SCAFFOLD-PIN-SHA" in text
        unpinned = []
        for ref in USES_RE.findall(text):
            if ref.startswith("./") or ref.startswith("docker://"):
                continue
            if "@" not in ref:
                rep.error(f"{rel}: action {ref!r} has no version reference at all")
                continue
            if not SHA_RE.match(ref.rsplit("@", 1)[1]):
                unpinned.append(ref)

        if unpinned and awaiting_pins:
            rep.error(f"{rel}: {len(unpinned)} action(s) still awaiting SHA resolution "
                      f"({', '.join(sorted(set(unpinned)))}) — resolve each to a full-length commit "
                      "SHA and remove the SCAFFOLD-PIN-SHA comments")
        elif unpinned:
            for ref in sorted(set(unpinned)):
                rep.error(f"{rel}: action {ref!r} is pinned to a mutable reference — resolve it to "
                          "a full-length commit SHA")

        triggers = text.split("jobs:", 1)[0]

        # Only a real trigger key counts. Prose mentioning the trigger in a comment does not.
        if re.search(r"^\s{2,}pull_request_target:", triggers, re.M):
            head_checkout = bool(
                re.search(r"ref:\s*\$\{\{\s*github\.event\.pull_request\.head", text)
                or "head.sha" in text
            )
            if head_checkout:
                rep.error(f"{rel}: combines pull_request_target with a checkout of the pull request "
                          "head — this runs untrusted code with a privileged token")
            else:
                rep.warn(f"{rel}: uses pull_request_target; confirm it never checks out PR head code")

        if re.search(r"^\s{2,}pull_request:", triggers, re.M) and not re.search(
                r"^concurrency:", text, re.M):
            rep.warn(f"{rel}: pull-request-triggered without `concurrency:` — runs will pile up")

        for marker in SCAFFOLD_MARKERS:
            if marker in text and marker != "SCAFFOLD-PIN-SHA":
                rep.error(f"{rel}: scaffold marker {marker} was never resolved")


def check_env(root: pathlib.Path, rep: Report) -> None:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return
    ignore = gitignore.read_text(encoding="utf-8")

    for secret, example in ((".env", ".env.example"), (".dev.vars", ".dev.vars.example")):
        has_example = (root / example).is_file()
        ignores_secret = re.search(rf"^{re.escape(secret)}(\.\*)?\s*$", ignore, re.M)
        negates_example = f"!{example}" in ignore

        if has_example and not ignores_secret:
            rep.error(f"{example} is committed but .gitignore does not ignore {secret}")
        if has_example and re.search(rf"^{re.escape(secret)}\.\*", ignore, re.M) and not negates_example:
            rep.error(f".gitignore ignores {secret}.* without a `!{example}` negation, so the "
                      "committed template will be excluded")

    for leaked in (".env", ".dev.vars"):
        if (root / leaked).is_file():
            rep.error(f"{leaked} exists in the working tree — it must never be committed")


def check_markers(root: pathlib.Path, rep: Report) -> None:
    for name in ("LICENSE", "NOTICE", "CODE_OF_CONDUCT.md"):
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in SCAFFOLD_MARKERS:
            if marker in text:
                rep.error(f"{name}: scaffold marker {marker} was never resolved")


def check_forms(root: pathlib.Path, rep: Report, visibility: str) -> None:
    if visibility != "private":
        return
    issue_dir = root / ".github" / "ISSUE_TEMPLATE"
    if not issue_dir.is_dir():
        return
    for path in sorted(issue_dir.glob("*.yml")):
        if path.name == "config.yml":
            continue
        text = path.read_text(encoding="utf-8")
        if "required: true" in text and "*(required)*" not in text:
            rep.warn(f"{path.relative_to(root).as_posix()}: uses `required: true`, which is not "
                     "enforced in a private repository — mark the requirement in the field label too")


AGENTIC_REQUIRED_DESTS = [
    "config/persona.json",
    "config/hitl_triggers.json",
    "config/system_prompt.md",
    "config/vector_store.yaml",
    "config/tools.json",
    "db/migrations/0001_create_agent_sessions.sql",
    "db/migrations/0002_create_hitl_records.sql",
    "src/agent/state.ts",
    "src/agent/router.ts",
    "src/agent/endpoints.ts",
    "src/agent/ui_contracts.ts",
    "src/agent/agentic_stack.test.ts",
    "src/safety/filters.ts",
    "tests/eval_dataset.json",
    "docs/architecture/hitl-protocol.md",
]


def check_agentic_stack(root: pathlib.Path, rep: Report, require_agentic: bool = False) -> None:
    marker = root / "config" / "hitl_triggers.json"
    if not marker.is_file():
        if require_agentic:
            rep.error("the agentic stack is required but config/hitl_triggers.json is missing")
        return

    missing = [rel for rel in AGENTIC_REQUIRED_DESTS if not (root / rel).is_file()]
    if missing:
        for rel in missing:
            rep.error(f"missing agentic stack file {rel}")
        return

    def read_json(rel: str, expected):
        path = root / rel
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            rep.error(f"{rel}: invalid JSON ({exc})")
            return None
        if not isinstance(value, expected):
            rep.error(f"{rel}: expected {expected.__name__}")
            return None
        return value

    persona = read_json("config/persona.json", dict)
    if persona is not None:
        metadata = persona.get("agent_metadata")
        if not isinstance(metadata, dict):
            rep.error("config/persona.json: agent_metadata must be an object")
        else:
            for key in ("identifier", "version", "temperature", "max_tokens"):
                if key not in metadata:
                    rep.error(f"config/persona.json: agent_metadata missing {key}")
        boundaries = persona.get("behavioral_boundaries")
        if not isinstance(boundaries, dict):
            rep.error("config/persona.json: behavioral_boundaries must be an object")
        else:
            for key in ("allowed_domains", "forbidden_topics"):
                value = boundaries.get(key)
                if not isinstance(value, list) or not value or not all(
                        isinstance(item, str) and item for item in value):
                    rep.error(f"config/persona.json: {key} must be a non-empty list of strings")
            if not isinstance(boundaries.get("linguistic_style"), str) or not boundaries["linguistic_style"]:
                rep.error("config/persona.json: linguistic_style must be a non-empty string")
        mitigation = persona.get("adversarial_mitigation")
        if not isinstance(mitigation, dict):
            rep.error("config/persona.json: adversarial_mitigation must be an object")
        else:
            if not isinstance(mitigation.get("strip_markdown_injections"), bool):
                rep.error("config/persona.json: strip_markdown_injections must be boolean")
            keywords = mitigation.get("reject_system_override_keywords")
            keyword_values: list[str] = []
            if not isinstance(keywords, list) or not keywords or not all(
                    isinstance(item, str) and item for item in keywords):
                rep.error("config/persona.json: reject_system_override_keywords must be a non-empty list of strings")
            elif isinstance(persona.get("behavioral_boundaries"), dict):
                keyword_values = [item for item in keywords if isinstance(item, str)]
                allowed = persona["behavioral_boundaries"].get("allowed_domains", [])
                forbidden = persona["behavioral_boundaries"].get("forbidden_topics", [])
                identifier = metadata.get("identifier") if isinstance(metadata, dict) else None
                if (isinstance(allowed, list) and isinstance(forbidden, list)
                        and all(isinstance(item, str) for item in allowed + forbidden)
                        and len(allowed) == 1 and isinstance(identifier, str)
                        and identifier == f"{allowed[0]}-agent"):
                    rep.warn("config/persona.json: allowed_domains still holds the scaffold default; "
                             "replace it with the real scope before the agent runs in production")
                allowed_values: list[str] = []
                forbidden_values: list[str] = []
                if isinstance(allowed, list):
                    allowed_values = [item for item in allowed if isinstance(item, str)]
                if isinstance(forbidden, list):
                    forbidden_values = [item for item in forbidden if isinstance(item, str)]
                overlap = sorted(set(allowed_values) & set(forbidden_values))
                if overlap:
                    rep.warn(f"config/persona.json: allowed_domains and forbidden_topics overlap: {overlap}")
            filters = root / "src" / "safety" / "filters.ts"
            if filters.is_file():
                enforced = extract_regex_literals(filters.read_text(encoding="utf-8"))
                uncovered = [word for word in keyword_values
                             if not any(regex_matches(word, pattern) for pattern in enforced)]
                if uncovered:
                    rep.warn("config/persona.json: no pattern in src/safety/filters.ts matches "
                             f"these declared keywords: {uncovered}")

    triggers_data = read_json("config/hitl_triggers.json", dict)
    trigger_ids: set[str] = set()
    if triggers_data is not None:
        triggers = triggers_data.get("triggers")
        if not isinstance(triggers, list) or not triggers:
            rep.error("config/hitl_triggers.json: triggers must be a non-empty list")
            triggers = []
        categories = {"FINANCIAL", "DELETION", "EXTERNAL_SIDE_EFFECT", "PRIVACY", "CUSTOM"}
        kinds = {"argument_threshold", "tool_name_in", "argument_matches"}
        actions = {"APPROVE_REJECT_MODIFY", "MFA_CHALLENGE", "NOTIFY_ONLY"}
        for trigger in triggers:
            if not isinstance(trigger, dict):
                rep.error("config/hitl_triggers.json: every trigger must be an object")
                continue
            trigger_id = trigger.get("trigger_id")
            if not isinstance(trigger_id, str) or not re.fullmatch(r"TR-[0-9]{2,}", trigger_id):
                rep.error("config/hitl_triggers.json: trigger_id must match ^TR-[0-9]{2,}$")
            elif trigger_id in trigger_ids:
                rep.error(f"config/hitl_triggers.json: duplicate trigger_id {trigger_id}")
            else:
                trigger_ids.add(trigger_id)
            if not isinstance(trigger.get("category"), str) or trigger["category"] not in categories:
                rep.error("config/hitl_triggers.json: invalid category")
            if not isinstance(trigger.get("description"), str) or not trigger["description"]:
                rep.error("config/hitl_triggers.json: description must be non-empty")
            match = trigger.get("match")
            if (not isinstance(match, dict) or not isinstance(match.get("kind"), str)
                    or match["kind"] not in kinds):
                rep.error("config/hitl_triggers.json: match.kind is invalid")
            elif match["kind"] == "argument_threshold":
                valid_ops = {"gt", "gte", "lt", "lte", "eq"}
                if not isinstance(match.get("field"), str) or not match["field"]:
                    rep.error("config/hitl_triggers.json: argument_threshold field must be a non-empty string")
                if not isinstance(match.get("op"), str) or match["op"] not in valid_ops:
                    rep.error(f"config/hitl_triggers.json: argument_threshold op must be one of {sorted(valid_ops)}")
                if not isinstance(match.get("value"), (int, float)) or isinstance(match.get("value"), bool):
                    rep.error("config/hitl_triggers.json: argument_threshold value must be a number")
                elif isinstance(match["value"], float) and not math.isfinite(match["value"]):
                    rep.error("config/hitl_triggers.json: argument_threshold value must be finite")
                elif isinstance(match["value"], int) and abs(match["value"]) > 2**53 - 1:
                    rep.error("config/hitl_triggers.json: argument_threshold value must be within "
                              "the JavaScript safe integer range")
            elif match["kind"] == "tool_name_in":
                tool_names = match.get("tool_names")
                if not isinstance(tool_names, list) or not tool_names or not all(
                        isinstance(n, str) and n for n in tool_names):
                    rep.error("config/hitl_triggers.json: tool_name_in needs non-empty list of non-empty strings")
            elif match["kind"] == "argument_matches":
                if not isinstance(match.get("field"), str) or not match["field"]:
                    rep.error("config/hitl_triggers.json: argument_matches field must be a non-empty string")
                pattern = match.get("pattern")
                if not isinstance(pattern, str) or not pattern:
                    rep.error("config/hitl_triggers.json: argument_matches needs non-empty pattern")
                elif not supported_regex(pattern):
                    rep.error(f"config/hitl_triggers.json: argument_matches pattern {pattern!r} "
                              "violates the common regex subset rule or does not compile: "
                              "use literals, character classes, anchors, *, +, ?, {n}, {n,m}, "
                              "groups (...), (?:...), (?=...), (?!...), alternation and "
                              r"escapes \d, \w, \s, \b, \S or escaped punctuation; "
                              "backreferences and other (? extensions are forbidden")
            if (not isinstance(trigger.get("action_required"), str)
                    or trigger["action_required"] not in actions):
                rep.error("config/hitl_triggers.json: invalid action_required")
            if not isinstance(trigger.get("frontend_component"), str) or not trigger["frontend_component"]:
                rep.error("config/hitl_triggers.json: frontend_component must be non-empty")
            if not isinstance(trigger.get("timeout_seconds"), int) or isinstance(
                    trigger.get("timeout_seconds"), bool) or trigger["timeout_seconds"] <= 0:
                rep.error("config/hitl_triggers.json: timeout_seconds must be a positive integer")

    required_text = {
        "src/agent/state.ts": ("RUNNING", "PENDING_HUMAN_APPROVAL", "RESUMING_LOOP",
                                "TASK_ABORTED", "TASK_COMPLETED", "MAX_EXECUTION_LOOPS"),
        "src/agent/router.ts": ("supervisor", "MAX_EXECUTION_LOOPS"),
        "src/safety/filters.ts": ("[REDACTED_PII]", "SECURITY_VIOLATION", "luhn"),
    }
    for rel, needles in required_text.items():
        path = root / rel
        if not path.is_file():
            rep.error(f"missing agentic stack file {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle.lower() not in text.lower():
                rep.error(f"{rel}: missing required text {needle}")

    tools = read_json("config/tools.json", dict)
    if tools is not None:
        definitions = tools.get("tool_definitions")
        if not isinstance(definitions, list) or not definitions:
            rep.error("config/tools.json: tool_definitions must be a non-empty list")
            definitions = []
        names: set[str] = set()
        for tool in definitions:
            if not isinstance(tool, dict):
                rep.error("config/tools.json: every tool must be an object")
                continue
            name = tool.get("name")
            if not isinstance(name, str) or not name:
                rep.error("config/tools.json: tool name must be non-empty")
            elif name in names:
                rep.error(f"config/tools.json: duplicate tool name {name}")
            else:
                names.add(name)
            if not isinstance(tool.get("description"), str) or not tool["description"]:
                rep.error("config/tools.json: tool description must be non-empty")
            if not isinstance(tool.get("parameters"), dict) or tool["parameters"].get("type") != "object":
                rep.error("config/tools.json: parameters.type must be object")
        sandbox = tools.get("sandbox_profile")
        if not isinstance(sandbox, dict):
            rep.error("config/tools.json: sandbox_profile must be an object")
        else:
            for key in ("runtime", "network_egress"):
                if not isinstance(sandbox.get(key), str) or not sandbox[key]:
                    rep.error(f"config/tools.json: sandbox_profile.{key} must be non-empty")
            for key in ("timeout_ms", "max_memory_mb"):
                if not isinstance(sandbox.get(key), int) or isinstance(sandbox.get(key), bool) or sandbox[key] <= 0:
                    rep.error(f"config/tools.json: sandbox_profile.{key} must be a positive integer")

    vector = root / "config" / "vector_store.yaml"
    if not vector.is_file():
        rep.error("missing agentic stack file config/vector_store.yaml")
    else:
        text = vector.read_text(encoding="utf-8")
        values = {}
        for key in ("dimension", "metric", "chunk_size", "chunk_overlap"):
            match = re.search(rf"^\s*{key}:\s*([^#\n]+)", text, re.M)
            if not match:
                rep.error(f"config/vector_store.yaml: missing {key}")
            else:
                values[key] = match.group(1).strip()
        for key in ("dimension", "chunk_size"):
            if key in values and (not re.fullmatch(r"[1-9][0-9]*", values[key])):
                rep.error(f"config/vector_store.yaml: {key} must be a positive integer")
        if "metric" in values and not values["metric"]:
            rep.error("config/vector_store.yaml: metric must be non-empty")
        if "chunk_overlap" in values and not re.fullmatch(r"-?[0-9]+", values["chunk_overlap"]):
            rep.error("config/vector_store.yaml: chunk_overlap must be an integer")
        if "chunk_size" in values and "chunk_overlap" in values and re.fullmatch(
                r"[1-9][0-9]*", values["chunk_size"]) and re.fullmatch(r"-?[0-9]+", values["chunk_overlap"]):
            if int(values["chunk_overlap"]) >= int(values["chunk_size"]):
                rep.error("config/vector_store.yaml: chunk_overlap must be less than chunk_size")
        for field in ("document_id", "user_scope_id", "classification_level"):
            listed = re.search(rf"^\s*(?:-\s*)?name:\s*{field}\b", text, re.M)
            mapped = re.search(rf"^\s*{field}\s*:", text, re.M)
            if not listed and not mapped:
                rep.error(f"config/vector_store.yaml: missing metadata field {field}")

    dataset = read_json("tests/eval_dataset.json", list)
    if dataset is not None:
        eval_ids: set[str] = set()
        positive_control = False
        for entry in dataset:
            if not isinstance(entry, dict):
                rep.error("tests/eval_dataset.json: every entry must be an object")
                continue
            eval_id = entry.get("eval_id")
            if not isinstance(eval_id, str) or not re.fullmatch(r"TC-[0-9]{3}", eval_id):
                rep.error("tests/eval_dataset.json: eval_id must match ^TC-[0-9]{3}$")
            elif eval_id in eval_ids:
                rep.error(f"tests/eval_dataset.json: duplicate eval_id {eval_id}")
            else:
                eval_ids.add(eval_id)
            if not isinstance(entry.get("input_scenario"), str) or not entry["input_scenario"]:
                rep.error("tests/eval_dataset.json: input_scenario must be non-empty")
            if (not isinstance(entry.get("expected_routing_node"), str)
                    or entry["expected_routing_node"] not in {"router", "researcher", "writer", "supervisor", "end"}):
                rep.error("tests/eval_dataset.json: invalid expected_routing_node")
            triggers = entry.get("expected_hitl_trigger")
            if not isinstance(triggers, list) or not all(isinstance(value, str) for value in triggers):
                rep.error("tests/eval_dataset.json: expected_hitl_trigger must be a list of strings")
            else:
                if not triggers:
                    positive_control = True
                for trigger_id in triggers:
                    if trigger_id not in trigger_ids:
                        rep.error(f"tests/eval_dataset.json: unknown trigger_id {trigger_id}")
            keywords = entry.get("ground_truth_keywords")
            if not isinstance(keywords, list) or not keywords or not all(
                    isinstance(value, str) and value for value in keywords):
                rep.error("tests/eval_dataset.json: ground_truth_keywords must be a non-empty list")
        if not positive_control:
            rep.error("tests/eval_dataset.json: no positive control with empty expected_hitl_trigger")

    migrations = root / "db" / "migrations"
    if not migrations.is_dir():
        rep.error("missing agentic stack directory db/migrations")
    else:
        sql_files = list(migrations.glob("*.sql"))
        sessions = [path for path in sql_files if re.search(r"create\s+table\s+(?:if\s+not\s+exists\s+)?agent_sessions", path.read_text(encoding="utf-8"), re.I)]
        hitl = [path for path in sql_files if re.search(r"create\s+table\s+(?:if\s+not\s+exists\s+)?hitl_records", path.read_text(encoding="utf-8"), re.I)]
        if not sessions:
            rep.error("db/migrations: no file defines agent_sessions")
        elif not all(state in sessions[0].read_text(encoding="utf-8") for state in (
                "RUNNING", "PENDING_HUMAN_APPROVAL", "RESUMING_LOOP", "TASK_ABORTED", "TASK_COMPLETED")):
            rep.error("db/migrations: agent_sessions status constraint omits a required state")
        if not hitl:
            rep.error("db/migrations: no file defines hitl_records")
        elif not all(resolution in hitl[0].read_text(encoding="utf-8") for resolution in (
                "PENDING", "APPROVED", "MODIFIED", "DENIED", "TIMEOUT")):
            rep.error("db/migrations: hitl_records resolution constraint omits a required resolution")
        elif not all(action in hitl[0].read_text(encoding="utf-8") for action in (
                "APPROVE_REJECT_MODIFY", "MFA_CHALLENGE", "NOTIFY_ONLY")):
            rep.error("db/migrations: hitl_records action_required constraint omits a required action value")


def validate(root: pathlib.Path, visibility: str, require_agentic: bool = False) -> Report:
    rep = Report()
    check_presence(root, rep)
    check_workflows(root, rep)
    check_env(root, rep)
    check_markers(root, rep)
    check_forms(root, rep, visibility)
    check_agentic_stack(root, rep, require_agentic)
    return rep


def emit(rep: Report, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings,
                          "error_count": len(rep.errors),
                          "warning_count": len(rep.warnings)}, indent=2))
        return
    for m in rep.warnings:
        print(f"warn:  {m}")
    for m in rep.errors:
        print(f"error: {m}")
    print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")


def self_test() -> int:
    failures = []
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
        for name in ("README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
                     "SUPPORT.md", "LICENSE", "AGENTS.md"):
            (root / name).write_text("x\n", encoding="utf-8")
        (root / ".github" / "pull_request_template.md").write_text("x\n", encoding="utf-8")
        (root / ".github" / "dependabot.yml").write_text("version: 2\n", encoding="utf-8")
        (root / ".github" / "ISSUE_TEMPLATE" / "config.yml").write_text(
            "blank_issues_enabled: false\n", encoding="utf-8")
        (root / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").write_text(
            "name: Bug\nbody: []\n", encoding="utf-8")
        (root / ".gitignore").write_text(".env\n.env.*\n!.env.example\n", encoding="utf-8")
        (root / ".env.example").write_text("A=\n", encoding="utf-8")

        good = ("name: CI\non:\n  pull_request:\npermissions:\n  contents: read\n"
                "concurrency:\n  group: ci\njobs:\n  a:\n    steps:\n"
                "      - uses: actions/checkout@" + "a" * 40 + "\n")
        (root / ".github" / "workflows" / "ci.yml").write_text(good, encoding="utf-8")

        def write_agentic_fixture() -> None:
            (root / "config").mkdir()
            (root / "src" / "agent").mkdir(parents=True)
            (root / "src" / "safety").mkdir(parents=True)
            (root / "tests").mkdir()
            (root / "db" / "migrations").mkdir(parents=True)
            (root / "config" / "persona.json").write_text(json.dumps({
                "agent_metadata": {"identifier": f"{root.name}-agent", "version": "1", "temperature": 0.2, "max_tokens": 1000},
                "behavioral_boundaries": {"allowed_domains": [root.name], "forbidden_topics": [root.name], "linguistic_style": "direct"},
                "adversarial_mitigation": {"strip_markdown_injections": True, "reject_system_override_keywords": ["ignore previous"]},
            }), encoding="utf-8")
            (root / "config" / "hitl_triggers.json").write_text(json.dumps({"triggers": [{
                "trigger_id": "TR-01", "category": "CUSTOM", "description": "Review", "match": {"kind": "tool_name_in", "tool_names": ["delete"]},
                "action_required": "APPROVE_REJECT_MODIFY", "frontend_component": "Approval", "timeout_seconds": 60,
            }]}), encoding="utf-8")
            (root / "config" / "tools.json").write_text(json.dumps({
                "tool_definitions": [{"name": "search", "description": "Search", "parameters": {"type": "object"}}],
                "sandbox_profile": {"runtime": "node", "network_egress": "allowlist", "timeout_ms": 1000, "max_memory_mb": 128},
            }), encoding="utf-8")
            (root / "config" / "vector_store.yaml").write_text(
                "dimension: 1536\nmetric: cosine\nchunk_size: 500\nchunk_overlap: 50\nmetadata:\n  document_id: string\n  user_scope_id: string\n  classification_level: string\n", encoding="utf-8")
            (root / "src" / "agent" / "state.ts").write_text(
                "RUNNING PENDING_HUMAN_APPROVAL RESUMING_LOOP TASK_ABORTED TASK_COMPLETED MAX_EXECUTION_LOOPS\n", encoding="utf-8")
            (root / "src" / "agent" / "router.ts").write_text(
                "supervisor(MAX_EXECUTION_LOOPS)\n", encoding="utf-8")
            (root / "src" / "safety" / "filters.ts").write_text(
                'const SYSTEM_OVERRIDE_KEYWORDS = ["ignore previous"];\nconst pii = "[REDACTED_PII]";\nconst code = "SECURITY_VIOLATION";\nfunction luhn() {}\n', encoding="utf-8")
            (root / "tests" / "eval_dataset.json").write_text(json.dumps([{
                "eval_id": "TC-001", "input_scenario": "search", "expected_routing_node": "router",
                "expected_hitl_trigger": [], "ground_truth_keywords": ["search"],
            }, {
                "eval_id": "TC-002", "input_scenario": "delete", "expected_routing_node": "supervisor",
                "expected_hitl_trigger": ["TR-01"], "ground_truth_keywords": ["approval"],
            }]), encoding="utf-8")
            (root / "db" / "migrations" / "0001_create_agent_sessions.sql").write_text(
                "CREATE TABLE agent_sessions (status TEXT CHECK (status IN ('RUNNING','PENDING_HUMAN_APPROVAL','RESUMING_LOOP','TASK_ABORTED','TASK_COMPLETED')));\n", encoding="utf-8")
            (root / "db" / "migrations" / "0002_create_hitl_records.sql").write_text(
                "CREATE TABLE hitl_records (resolution TEXT CHECK (resolution IN ('PENDING','APPROVED','MODIFIED','DENIED','TIMEOUT')), CONSTRAINT hitl_records_action_check CHECK (action_required IN ('APPROVE_REJECT_MODIFY', 'MFA_CHALLENGE', 'NOTIFY_ONLY')));\n", encoding="utf-8")
            (root / "config" / "system_prompt.md").write_text("x\n", encoding="utf-8")
            (root / "src" / "agent" / "endpoints.ts").write_text("x\n", encoding="utf-8")
            (root / "src" / "agent" / "ui_contracts.ts").write_text("x\n", encoding="utf-8")
            (root / "src" / "agent" / "agentic_stack.test.ts").write_text("x\n", encoding="utf-8")
            (root / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "architecture" / "hitl-protocol.md").write_text("x\n", encoding="utf-8")

        write_agentic_fixture()

        rep = validate(root, "public")
        if rep.errors:
            failures.append(f"clean sample should pass, got: {rep.errors}")

        trigger_path = root / "config" / "hitl_triggers.json"
        trigger_data = json.loads(trigger_path.read_text(encoding="utf-8"))
        trigger_data["triggers"][0]["action_required"] = "UNKNOWN"
        trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")
        if not any("action_required" in e for e in validate(root, "public").errors):
            failures.append("failed to catch an unknown HITL action")
        trigger_data["triggers"][0]["action_required"] = "APPROVE_REJECT_MODIFY"
        trigger_data["triggers"].append(dict(trigger_data["triggers"][0]))
        trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")
        if not any("duplicate trigger_id" in e for e in validate(root, "public").errors):
            failures.append("failed to catch a duplicate trigger_id")
        trigger_data["triggers"].pop()
        trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")

        threshold_trigger = {
            "trigger_id": "TR-02", "category": "FINANCIAL", "description": "Threshold",
            "match": {"kind": "argument_threshold", "field": "amount", "op": "gt", "value": 100},
            "action_required": "APPROVE_REJECT_MODIFY", "frontend_component": "Approval", "timeout_seconds": 60,
        }
        trigger_data["triggers"].append(threshold_trigger)
        trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")
        if validate(root, "public").errors:
            failures.append("valid argument_threshold trigger should pass")

        bad_op = dict(threshold_trigger)
        bad_op["match"] = dict(threshold_trigger["match"])
        bad_op["match"]["op"] = "unknown_op"
        trigger_data["triggers"][-1] = bad_op
        trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")
        if not any("op" in e for e in validate(root, "public").errors):
            failures.append("failed to catch an unknown op in argument_threshold")

        bad_value = dict(threshold_trigger)
        bad_value["match"] = dict(threshold_trigger["match"])
        bad_value["match"]["value"] = "not-a-number"
        trigger_data["triggers"][-1] = bad_value
        trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")
        if not any("value must be a number" in e for e in validate(root, "public").errors):
            failures.append("failed to catch a non-numeric threshold value")

        for value in ("100", float("nan"), float("inf"), float("-inf"),
                      10**400, 2**53, -(2**53)):
            bad_value["match"]["value"] = value
            trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")
            if isinstance(value, str):
                expected = "value must be a number"
            elif isinstance(value, int):
                expected = "JavaScript safe integer range"
            else:
                expected = "value must be finite"
            if not any(expected in e for e in validate(root, "public").errors):
                failures.append(f"failed to catch invalid threshold value {value!r}")

        for value in (2**53 - 1, -(2**53 - 1), 1e100):
            bad_value["match"]["value"] = value
            trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")
            if validate(root, "public").errors:
                failures.append(f"rejected valid threshold value {value!r}")

        for field in ("op", "category", "action_required", "kind"):
            for value in ([], {}):
                malformed = {**threshold_trigger, "match": dict(threshold_trigger["match"])}
                target = malformed["match"] if field in ("op", "kind") else malformed
                target[field] = value
                trigger_data["triggers"][-1] = malformed
                trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")
                expected = "match.kind" if field == "kind" else field
                if not any(expected in e for e in validate(root, "public").errors):
                    failures.append(f"failed to catch {field}={value!r}")

        bad_tool_names = {
            "trigger_id": "TR-02", "category": "DELETION", "description": "Tool check",
            "match": {"kind": "tool_name_in", "tool_names": [42]},
            "action_required": "NOTIFY_ONLY", "frontend_component": "Notice", "timeout_seconds": 30,
        }
        trigger_data["triggers"][-1] = bad_tool_names
        trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")
        if not any("non-empty list of non-empty strings" in e for e in validate(root, "public").errors):
            failures.append("failed to catch a non-string tool_names entry")

        bad_pattern = {
            "trigger_id": "TR-02", "category": "PRIVACY", "description": "Pattern check",
            "match": {"kind": "argument_matches", "field": "query", "pattern": "[invalid("},
            "action_required": "NOTIFY_ONLY", "frontend_component": "Notice", "timeout_seconds": 30,
        }
        trigger_data["triggers"][-1] = bad_pattern
        trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")
        if not any("does not compile" in e for e in validate(root, "public").errors):
            failures.append("failed to catch a pattern that does not compile")

        for pattern in ("(?P<account>production)", "(?<account>production)", "(?<=x)y",
                        "(?<!x)y", "(?i)abc", "(?>a)", r"(a)\1", r"\k<name>",
                        r"\Aabc", "a++", "[]a]", "[^]a]"):
            bad_pattern["match"]["pattern"] = pattern
            trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")
            if not any("common regex subset rule" in e for e in validate(root, "public").errors):
                failures.append(f"failed to catch unsupported pattern {pattern!r}")
        for pattern in ("^production$", r"\d{3}-\d{2}-\d{4}", "(?:a|b)+", "(?=x)y",
                        "(?!x)y", "[a-z]{2,4}", r"\bword\b", r"\S+", r"a\.b",
                        r"^prod.*$", "a{2,}", "a{2,4}", "a.b", r"line\nbreak"):
            if not supported_regex(pattern):
                failures.append(f"rejected supported pattern {pattern!r}")

        trigger_data["triggers"].pop()
        trigger_path.write_text(json.dumps(trigger_data), encoding="utf-8")

        required_path = root / "config" / "system_prompt.md"
        required_path.unlink()
        required_path.mkdir()
        if "missing agentic stack file config/system_prompt.md" not in validate(root, "public").errors:
            failures.append("accepted a directory as a required agentic file")
        required_path.rmdir()
        required_path.write_text("x\n", encoding="utf-8")

        no_hitl_root = pathlib.Path(tempfile.mkdtemp())
        try:
            (no_hitl_root / ".github" / "workflows").mkdir(parents=True)
            (no_hitl_root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
            for name in ("README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
                         "SUPPORT.md", "LICENSE", "AGENTS.md"):
                (no_hitl_root / name).write_text("x\n", encoding="utf-8")
            (no_hitl_root / ".github" / "pull_request_template.md").write_text("x\n", encoding="utf-8")
            (no_hitl_root / ".github" / "dependabot.yml").write_text("version: 2\n", encoding="utf-8")
            (no_hitl_root / ".github" / "ISSUE_TEMPLATE" / "config.yml").write_text(
                "blank_issues_enabled: false\n", encoding="utf-8")
            (no_hitl_root / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").write_text(
                "name: Bug\nbody: []\n", encoding="utf-8")
            (no_hitl_root / ".gitignore").write_text(".env\n.env.*\n!.env.example\n", encoding="utf-8")
            (no_hitl_root / ".env.example").write_text("A=\n", encoding="utf-8")
            (no_hitl_root / ".github" / "workflows" / "ci.yml").write_text(good, encoding="utf-8")
            (no_hitl_root / "config").mkdir()
            (no_hitl_root / "config" / "persona.json").write_text("{}\n", encoding="utf-8")
            no_hitl_rep = validate(no_hitl_root, "public")
            agentic_errors = [e for e in no_hitl_rep.errors if "agentic stack" in e or "config/" in e or "src/agent" in e]
            if agentic_errors:
                failures.append(f"stray persona.json triggered agentic checks: {agentic_errors}")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(["--root", str(no_hitl_root), "--visibility", "public",
                               "--output", "json", "--require-agentic"])
            required_report = json.loads(output.getvalue())
            if status != 1 or not any("agentic stack is required" in e
                                      for e in required_report["errors"]):
                failures.append("--require-agentic failed to report a missing stack")
        finally:
            import shutil as _shutil
            _shutil.rmtree(no_hitl_root, ignore_errors=True)

        dataset_path = root / "tests" / "eval_dataset.json"
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
        for value in ([], {}):
            dataset[0]["expected_routing_node"] = value
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
            try:
                errors = validate(root, "public").errors
            except TypeError:
                failures.append(f"expected_routing_node={value!r} raised TypeError")
            else:
                if not any("invalid expected_routing_node" in e for e in errors):
                    failures.append(f"failed to catch expected_routing_node={value!r}")
        dataset[0]["expected_routing_node"] = "router"
        dataset[0]["expected_hitl_trigger"] = ["TR-01"]
        dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
        if not any("positive control" in e for e in validate(root, "public").errors):
            failures.append("failed to catch a missing evaluation positive control")
        dataset[0]["expected_hitl_trigger"] = []
        dataset[1]["expected_hitl_trigger"] = ["TR-99"]
        dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
        if not any("unknown trigger_id" in e for e in validate(root, "public").errors):
            failures.append("failed to catch an unknown evaluation trigger")

        # unpinned action
        (root / ".github" / "workflows" / "ci.yml").write_text(
            good.replace("a" * 40, "v4"), encoding="utf-8")
        if not any("mutable reference" in e for e in validate(root, "public").errors):
            failures.append("failed to catch an unpinned action")

        # missing permissions
        (root / ".github" / "workflows" / "ci.yml").write_text(
            good.replace("permissions:\n  contents: read\n", ""), encoding="utf-8")
        if not any("permissions" in e for e in validate(root, "public").errors):
            failures.append("failed to catch a workflow without permissions")

        # pull_request_target + head checkout
        danger = good + ("  b:\n    steps:\n      - uses: actions/checkout@" + "b" * 40 +
                         "\n        with:\n          ref: ${{ github.event.pull_request.head.sha }}\n")
        (root / ".github" / "workflows" / "ci.yml").write_text(
            danger.replace("pull_request:", "pull_request_target:"), encoding="utf-8")
        if not any("pull_request_target" in e for e in validate(root, "public").errors):
            failures.append("failed to catch pull_request_target with a head checkout")
        (root / ".github" / "workflows" / "ci.yml").write_text(good, encoding="utf-8")

        # env negation missing
        (root / ".gitignore").write_text(".env\n.env.*\n", encoding="utf-8")
        if not any("negation" in e for e in validate(root, "public").errors):
            failures.append("failed to catch a missing .env.example negation")
        (root / ".gitignore").write_text(".env\n.env.*\n!.env.example\n", encoding="utf-8")

        # missing config.yml
        (root / ".github" / "ISSUE_TEMPLATE" / "config.yml").unlink()
        if not any("config.yml" in e for e in validate(root, "public").errors):
            failures.append("failed to catch a missing ISSUE_TEMPLATE/config.yml")
        (root / ".github" / "ISSUE_TEMPLATE" / "config.yml").write_text("x\n", encoding="utf-8")

        # scaffold marker
        (root / "LICENSE").write_text("SCAFFOLD MARKER: REPLACE-WITH-CANONICAL-TEXT\n",
                                      encoding="utf-8")
        if not any("REPLACE-WITH-CANONICAL-TEXT" in e for e in validate(root, "public").errors):
            failures.append("failed to catch an unresolved scaffold marker")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    for f in failures:
        print(f"FAIL: {f}")
    print(f"\nself-test: {len(failures)} failure(s)")
    return 1 if failures else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate a scaffolded repository.")
    ap.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    ap.add_argument("--visibility", choices=("private", "public"), default="private")
    ap.add_argument("--output", choices=("text", "json"), default="text")
    ap.add_argument("--require-agentic", action="store_true",
                    help="require and validate all agentic stack files")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 2

    rep = validate(args.root, args.visibility, args.require_agentic)
    emit(rep, args.output)
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
