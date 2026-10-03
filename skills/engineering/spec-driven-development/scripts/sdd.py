#!/usr/bin/env python3
"""Structural SDD checks. Never runs project commands or grants approval."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timedelta, timezone

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
GLOBALS = ("CONSTITUTION", "MISSION", "TECH_STACK", "ROADMAP")
LOCALS = ("SPECIFICATION", "DESIGN", "INVARIANTS", "OBSERVABILITY", "TASKS")
ARTIFACTS = GLOBALS + LOCALS
SECTIONS = {
    "CONSTITUTION": ("Principles", "Boundaries", "Approval policy"),
    "MISSION": ("Problem", "Outcomes", "Scope", "Assumptions"),
    "TECH_STACK": ("Stack", "Project tree", "Commands", "Style", "Test strategy"),
    "ROADMAP": ("Capabilities", "Dependencies", "Milestones"),
    "SPECIFICATION": ("Context", "Requirements", "Acceptance criteria", "Exclusions", "Open questions"),
    "DESIGN": ("Approach", "Contracts", "Data", "Security", "Simplicity", "UI"),
    "INVARIANTS": ("Rules", "Test strategy"),
    "OBSERVABILITY": ("Policy", "Observations", "UI applicability"),
    "TASKS": ("Tasks", "Execution log", "Verification"),
}
FIELDS = {
    "Requirements": ("ID", "Type", "Statement"),
    "Rules": ("ID", "Requirements", "Rule", "Positive", "Negative"),
    "Observations": ("ID", "Requirements", "Invariants", "Event", "Fields", "Privacy", "Test"),
    "Tasks": ("ID", "Requirements", "Invariants", "Observations", "Depends", "Tests", "Files", "Verify", "Cwd", "Exit", "Done"),
    "Execution log": ("ID", "Status", "Red", "Green", "Refactor", "Verification"),
    "Artifacts": ("Artifact", "Location"),
    "Modules": ("ID", "Depends", "Owner", "Contract", "Feature"),
}
ID = {
    "REQ": re.compile(r"REQ-[1-9]\d*"),
    "INV": re.compile(r"INV-[1-9]\d*"),
    "OBS": re.compile(r"OBS-[1-9]\d*"),
    "TASK": re.compile(r"TASK-[1-9]\d*"),
    "MOD": re.compile(r"MOD-[A-Z][A-Z0-9-]*"),
}
PLACEHOLDER = re.compile(r"\b(?:TODO|TBD|FILL_ME|PLACEHOLDER)\b|<[^>\n]+>", re.I)
HOW = re.compile(
    r"```|`|CREATE\s+TABLE|SELECT\s+.+?\s+FROM|INSERT\s+INTO|"
    r"\b(?:database\s+schema|SQL|ORM|React|PostgreSQL|MongoDB|"
    r"use\s+(?:a\s+)?(?:hash\s+map|function|class|table)|"
    r"algorithm|pip\s+install|npm\s+install|Python|JavaScript|TypeScript|"
    r"HTTP|REST|JSON|endpoint|Redis|Postgres(?:ql)?|gRPC)\b|"
    r"\b(?:store|persist|write|insert|implement|use)\b.{0,60}\b(?:queue|table|column|class|function)\b", re.I
)
SENSITIVE = re.compile(
    r"email|authorization|api_?key|passwd|pwd|credential|session|card|address|dob|message_?text|"
    r"(?:^|_)(?:password|secret|token|phone|ssn|ip|body|payload|raw|cookie|auth)(?:_|$)", re.I
)
CHECKS = ("scope", "ears", "traceability", "contracts", "security_positive",
          "security_negative", "tests", "observability", "simplicity", "drift", "ui")
EARS = {
    "ubiquitous": r"The (?P<system>[^,]+?) shall (?P<response>.+)\.",
    "event": r"When (?P<condition>[^,]+), the (?P<system>[^,]+?) shall (?P<response>.+)\.",
    "state": r"While (?P<condition>[^,]+), the (?P<system>[^,]+?) shall (?P<response>.+)\.",
    "optional": r"Where (?P<condition>[^,]+), the (?P<system>[^,]+?) shall (?P<response>.+)\.",
    "unwanted": r"If (?P<condition>[^,]+), then the (?P<system>[^,]+?) shall (?P<response>.+)\.",
    "complex": r"While (?P<state>[^,]+), When (?P<condition>[^,]+), the (?P<system>[^,]+?) shall (?P<response>.+)\.",
}


class Invalid(ValueError):
    pass


def fail(message):
    raise Invalid(message)


def safe_absolute(path):
    """Reject symlink components including those above the selected root."""
    path = Path(os.path.abspath(path))
    for node in (path, *path.parents):
        if node.is_symlink():
            fail(f"symlink not allowed: {node}")
    return path


def local_path(root, raw, must_exist=True):
    if not isinstance(raw, str) or not raw or "\\" in raw:
        fail("path must be nonempty POSIX relative path")
    p = Path(raw)
    if p.is_absolute() or any(x in ("", ".", "..") for x in raw.split("/")):
        fail(f"unsafe relative path: {raw}")
    target = safe_absolute(root / p)
    if not target.is_relative_to(root):
        fail(f"path escapes root: {raw}")
    if must_exist and not target.is_file():
        fail(f"missing regular file: {raw}")
    return target


def read(path):
    safe_absolute(path)
    if not path.is_file() or path.stat().st_size > 2_000_000 or path.stat().st_nlink > 1:
        fail(f"missing, oversized, or hardlinked file: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        fail(f"empty file: {path}")
    return text


def exclusive(path, text):
    safe_absolute(path)
    # O_EXCL also rejects a symlink created at the final component.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        out.write(text)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    safe_absolute(path)
    if not path.is_file() or not 0 < path.stat().st_size <= 20_000_000 or path.stat().st_nlink > 1:
        fail(f"missing, empty, oversized, or hardlinked evidence: {path}")
    return digest(path.read_bytes())


def json_file(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                fail(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(read(path), object_pairs_hook=pairs)


def section(text, name):
    matches = list(re.finditer(r"^## (.+)\s*$", text, re.M))
    chosen = [i for i, m in enumerate(matches) if m.group(1) == name]
    if len(chosen) != 1:
        fail(f"expected exactly one section: {name}")
    i = chosen[0]
    return text[matches[i].end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()


def meaningful(text, label):
    if PLACEHOLDER.search(text) or re.search(r"^\s*- \[ \]", text, re.M):
        fail(f"{label}: unresolved draft marker/question")
    lines = [x.strip() for x in text.splitlines()
             if x.strip() and not x.startswith("#") and not x.startswith("|")]
    if not lines or all(x in ("None.", "None", "N/A", "-") for x in lines):
        fail(f"{label}: no substantive content or reasoned N/A")
    if re.search(r"\bN/A\b", text) and not re.search(r"N/A:\s*\S.{9,}", text):
        fail(f"{label}: N/A needs a reason")


def table(text, name, allow_na=False):
    body = section(text, name)
    if allow_na and re.fullmatch(r"N/A:\s*\S.{9,}", body):
        return []
    lines = [line for line in body.splitlines() if line.strip()]
    if len(lines) < 3 or any(not x.startswith("|") or not x.endswith("|") for x in lines):
        fail(f"{name}: expected a table with at least one row")
    cells = lambda line: [x.strip() for x in line.strip("|").split("|")]
    headers = cells(lines[0])
    if tuple(headers) != FIELDS[name] or len(cells(lines[1])) != len(headers) or not all(re.fullmatch(r":?-{3,}:?", x) for x in cells(lines[1])):
        fail(f"{name}: wrong table header/separator")
    result = []
    for line in lines[2:]:
        row = cells(line)
        if len(row) != len(headers) or not all(row):
            fail(f"{name}: empty cell or wrong column count")
        if any(PLACEHOLDER.search(x) for x in row):
            fail(f"{name}: unresolved placeholder")
        result.append(dict(zip(headers, row)))
    return result


def values(cell):
    if cell == "-":
        return []
    items = [x.strip() for x in cell.split(",")]
    if not all(items) or len(items) != len(set(items)):
        fail(f"invalid list: {cell}")
    return items


def index_rows(rows, kind):
    result = {}
    for row in rows:
        key = row["ID"]
        if not ID[kind].fullmatch(key) or key in result:
            fail(f"duplicate or malformed {kind} ID: {key}")
        result[key] = row
    return result


def refs(cell, ids, label, required=False):
    found = values(cell)
    if required and not found:
        fail(f"{label}: at least one reference required")
    for key in found:
        if key not in ids:
            fail(f"{label}: unknown reference {key}")
    return set(found)


def dag(nodes):
    seen, active, order = set(), set(), []
    def visit(key):
        if key in active:
            fail(f"dependency cycle at {key}")
        if key in seen:
            return
        active.add(key)
        for dep in values(nodes[key]["Depends"]):
            if dep not in nodes:
                fail(f"{key}: unknown dependency {dep}")
            visit(dep)
        active.remove(key)
        seen.add(key)
        order.append(key)
    for key in nodes:
        visit(key)
    return order


def ears(kind, statement):
    pattern = EARS.get(kind.lower())
    match = re.fullmatch(pattern, statement, re.I) if pattern else None
    if not match:
        fail(f"malformed {kind} EARS: {statement}")
    for name, part in match.groupdict().items():
        if not re.search(r"[A-Za-z0-9]", part) or re.search(r"\b(?:shall|When|While|Where|If|then)\b", part, re.I):
            fail(f"EARS {name}: empty, ambiguous, or misplaced keyword")
    if len(re.findall(r"\bshall\b", statement, re.I)) != 1:
        fail("EARS must contain one shall")


def acceptance(text, reqs):
    """Adapt the existing SpecParser without making it an EARS validator."""
    canonical = legacy_parser()
    # Installed alongside the old skill? Use its unchanged parser. Standalone
    # operation uses the small bounded GWT fallback with the same AC-N contract.
    blocks = re.findall(r"^### (AC-[1-9]\d*): ([^\n]+)\n(.*?)(?=^### |^## |\Z)",
                        section(text, "Acceptance criteria"), re.M | re.S)
    result, seen = [], set()
    for key, heading, body in blocks:
        if key in seen:
            fail(f"duplicate acceptance ID: {key}")
        seen.add(key)
        match = re.fullmatch(r".+ \((REQ-[1-9]\d*(?:, REQ-[1-9]\d*)*)\)", heading)
        if not match:
            fail(f"{key}: acceptance heading needs requirement references")
        references = refs(match.group(1), reqs, key, True)
        lines = [x.strip() for x in body.splitlines() if x.strip()]
        clauses = [(i, word.lower()) for i, line in enumerate(lines)
                   for word in ("Given", "When", "Then") if re.match(rf"^{word}\s+\S", line, re.I)]
        if not clauses or [word for _, word in clauses] != ["given", "when", "then"]:
            fail(f"{key}: Given/When/Then must each be nonempty and ordered")
        normalized = "\n".join(lines)
        if canonical is not None:
            spec = importlib.util.spec_from_file_location("sdd_legacy_extractor", canonical)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            ac = module.SpecParser(f"# Feature\n## Acceptance Criteria\n### {key}: {heading}\n{normalized}").extract_acceptance_criteria()
            complete = len(ac) == 1 and ac[0]["given"] and ac[0]["when"] and ac[0]["then"]
        else:
            complete = True
        if not complete:
            fail(f"{key}: incomplete Given/When/Then")
        result.append({"id": key, "requirements": sorted(references), "body": body.strip()})
    if not result:
        fail("no AC-N Given/When/Then criteria")
    if set().union(*(set(x["requirements"]) for x in result)) != set(reqs):
        fail("acceptance criteria do not cover every requirement")
    return result


def legacy_parser():
    """The only optional repository integration; absent means standalone."""
    canonical = HERE.parent.parent / "skills" / "spec-driven-workflow" / "scripts" / "test_extractor.py"
    safe_absolute(canonical)
    return canonical if canonical.is_file() else None


def resolve(root, feature=None):
    root = safe_absolute(root)
    if not root.is_dir():
        fail(f"root directory does not exist: {root}")
    target = root / ".specs"
    if feature is not None:
        if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", feature) or len(feature) > 64:
            fail("feature ID must be lowercase kebab-case, 1-64 characters")
        target /= Path("features") / feature
    safe_absolute(target)
    return root, target


def artifacts(root, target):
    index = target / "INDEX.md"
    mapping = {}
    if index.exists():
        for row in table(read(index), "Artifacts"):
            key = row["Artifact"]
            if key not in ARTIFACTS or key in mapping:
                fail(f"INDEX: duplicate/unknown artifact {key}")
            mapping[key] = row["Location"]
        if set(mapping) != set(ARTIFACTS):
            fail("INDEX must map all nine artifacts")
    else:
        for key in ARTIFACTS:
            parent = root / ".specs" if target != root / ".specs" and key in GLOBALS else target
            mapping[key] = (parent / f"{key}.md").relative_to(root).as_posix()
    result = {}
    for key, location in mapping.items():
        bits = location.split("#")
        if len(bits) > 2:
            fail("INDEX supports at most one explicit H1/H2 section")
        path = local_path(root, bits[0])
        text = read(path)
        if len(bits) == 2:
            # Literal section title, not a guessed GitHub slug.
            matches = list(re.finditer(r"^(#{1,2}) (.+)\s*$", text, re.M))
            chosen = [i for i, m in enumerate(matches) if m.group(2) == bits[1]]
            if len(chosen) != 1:
                fail(f"INDEX section missing/ambiguous: {location}")
            i = chosen[0]
            level = len(matches[i].group(1))
            end = next((m.start() for m in matches[i + 1:] if len(m.group(1)) <= level), len(text))
            text = text[matches[i].end():end]
        result[key] = (path, text)
    return result


def test_path(root, raw, existing):
    bits = raw.split("#")
    if len(bits) != 2 or not bits[1] or len(bits[1]) < 3:
        fail(f"test reference needs path#test-name: {raw}")
    path = local_path(root, bits[0], existing)
    if existing:
        text = read(path)
        marker = bits[1]
        if path.suffix == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                fail(f"test file is not valid Python: {raw}")
            candidates = list(tree.body) + [child for node in tree.body if isinstance(node, ast.ClassDef) for child in node.body]
            found = marker.startswith("test") and any(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == marker for node in candidates
            )
        else:
            # A bounded declaration check for JS/TS and Go, not discovery.
            found = bool(re.search(rf"\b(?:it|test)\s*\(\s*['\"]{re.escape(marker)}['\"]", text)
                         or re.search(rf"\bfunc\s+{re.escape(marker)}\s*\(", text))
        if not found:
            fail(f"test declaration not found: {raw}")


def lint(root, target, stage="ready", task=None):
    docs = artifacts(root, target)
    if target != root / ".specs":
        cap = root / ".specs" / "CAPABILITY_MAP.md"
        modules = index_rows(table(read(cap), "Modules"), "MOD")
        dag(modules)
        for key, row in modules.items():
            if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", row["Feature"]):
                fail(f"{key}: invalid feature ID")
            meaningful(row["Owner"], key)
            local_path(root, row["Contract"], stage != "spec")
        if target.name not in {x["Feature"] for x in modules.values()}:
            fail("feature absent from CAPABILITY_MAP")
    selected = set(GLOBALS + ("SPECIFICATION",))
    if stage in ("plan", "tasks", "ready"):
        selected |= {"DESIGN", "INVARIANTS", "OBSERVABILITY"}
    if stage in ("tasks", "ready"):
        selected.add("TASKS")
    for key in selected:
        text = docs[key][1]
        if PLACEHOLDER.search(text):
            fail(f"{key}: unresolved draft marker")
        for name in SECTIONS[key]:
            body = section(text, name)
            if name not in FIELDS:
                meaningful(body, f"{key}/{name}")
    spec = docs["SPECIFICATION"][1]
    behavior = "\n".join(section(spec, name) for name in ("Context", "Requirements", "Acceptance criteria"))
    if HOW.search(behavior):
        fail("SPECIFICATION contains suspected implementation detail; move how to DESIGN/TECH_STACK")
    requirements = index_rows(table(spec, "Requirements"), "REQ")
    for key, row in requirements.items():
        ears(row["Type"], row["Statement"])
    criteria = acceptance(spec, requirements)
    if stage != "spec":
        questions = section(spec, "Open questions")
        if questions.startswith("None:") and re.search(r"\?|\b(?:unresolved|unknown|undecided|pending)\b", questions, re.I):
            fail("Open questions None declaration contains unresolved question text")
        if not re.fullmatch(r"None:\s*\S.{9,}", questions, re.S) and not all(
            re.fullmatch(r"(?:Resolved:|Deferred \(non-blocking\):)\s*\S.{9,}", line)
            for line in questions.splitlines() if line.strip()
        ):
            fail("Open questions must be resolved or explicitly deferred as non-blocking")
    result = {"requirements": requirements, "criteria": criteria, "tasks": {}, "order": []}
    if stage == "spec":
        return result
    inv = index_rows(table(docs["INVARIANTS"][1], "Rules", True), "INV")
    obs = index_rows(table(docs["OBSERVABILITY"][1], "Observations", True), "OBS")
    for key, row in inv.items():
        refs(row["Requirements"], requirements, key, True)
        if row["Positive"] == row["Negative"]:
            fail(f"{key}: positive and negative tests must differ")
        for field in ("Positive", "Negative"):
            test_path(root, row[field], stage == "ready" and task is None)
    unwanted = {key for key, row in requirements.items() if row["Type"].lower() == "unwanted"}
    if not unwanted <= {key for row in inv.values() for key in values(row["Requirements"])}:
        fail("unwanted requirements need invariant attempted-violation tests")
    for key, row in obs.items():
        r = refs(row["Requirements"], requirements, key, True)
        i = refs(row["Invariants"], inv, key)
        if any(not set(values(inv[x]["Requirements"])) <= r for x in i):
            fail(f"{key}: observation invariant/requirement mismatch")
        fields = values(row["Fields"])
        if not {"event", "outcome", "correlation_id"} <= set(fields) or any(
            not re.fullmatch(r"[a-z][a-z0-9_]*", field) for field in fields
        ):
            fail(f"{key}: structured event/outcome/correlation_id fields required")
        if any(SENSITIVE.search(field) and not field.endswith(("_hash", "_redacted")) for field in fields):
            fail(f"{key}: unsafe sensitive telemetry field")
        policy = re.fullmatch(r"allowlist=([a-z0-9_, ]+); exclude=([a-z0-9_, ]+)", row["Privacy"])
        if not policy or set(values(policy.group(1))) != set(fields) or not values(policy.group(2)) or set(values(policy.group(2))) & {"none", "na"}:
            fail(f"{key}: telemetry requires exact allowlist=Fields; exclude=names policy")
        test_path(root, row["Test"], stage == "ready" and task is None)
    if stage == "plan":
        return result
    tasks = index_rows(table(docs["TASKS"][1], "Tasks"), "TASK")
    execution = index_rows(table(docs["TASKS"][1], "Execution log"), "TASK")
    if set(execution) != set(tasks):
        fail("execution log must contain every task exactly once")
    if task is not None and task not in tasks:
        fail("selected task does not exist")
    covered = {"Requirements": set(), "Invariants": set(), "Observations": set()}
    for key, row in tasks.items():
        r = refs(row["Requirements"], requirements, key, True)
        i = refs(row["Invariants"], inv, key)
        o = refs(row["Observations"], obs, key)
        if any(not set(values(inv[x]["Requirements"])) <= r for x in i) or any(
            not set(values(obs[x]["Requirements"])) <= r or not set(values(obs[x]["Invariants"])) <= i for x in o
        ):
            fail(f"{key}: requirement/invariant/observation mismatch")
        for field, found in zip(covered, (r, i, o)):
            covered[field] |= found
        tests = values(row["Tests"])
        if not tests:
            fail(f"{key}: at least one test required")
        required_tests = {inv[x][f] for x in i for f in ("Positive", "Negative")} | {obs[x]["Test"] for x in o}
        if not required_tests <= set(tests):
            fail(f"{key}: invariant/observation tests missing from task")
        existing = execution[key]["Status"] == "completed" or (stage == "ready" and (task is None or task == key))
        for test in tests:
            test_path(root, test, existing)
        owned = values(row["Files"])
        if not owned or not {test.split("#")[0] for test in tests} <= set(owned):
            fail(f"{key}: Files must include owned implementation/test paths")
        for raw in owned:
            owned_path = local_path(root, raw, existing)
            if existing:
                file_digest(owned_path)
        cwd = root if row["Cwd"] == "." else local_path(root, row["Cwd"], False)
        if not cwd.is_dir() or not re.fullmatch(r"(?:0|[1-9]\d{0,2})", row["Exit"]) or int(row["Exit"]) > 255:
            fail(f"{key}: invalid cwd or expected exit")
        if len(row["Verify"].split()) < 2:
            fail(f"{key}: full validation command required")
        if len(row["Done"]) < 12:
            fail(f"{key}: sparse completion condition")
    for field, ids in (("Requirements", requirements), ("Invariants", inv), ("Observations", obs)):
        if covered[field] != set(ids):
            fail(f"tasks do not cover all {field}")
    for key, row in execution.items():
        if row["Status"] not in ("planned", "in-progress", "completed"):
            fail(f"{key}: unknown execution status")
        if row["Status"] == "completed":
            if len({row[field] for field in ("Red", "Green", "Refactor", "Verification")}) != 4:
                fail(f"{key}: four distinct completion evidence files required")
            for field in ("Red", "Green", "Refactor", "Verification"):
                local_path(root, row[field])
            if not set(values(tasks[key]["Depends"])) <= {k for k, v in execution.items() if v["Status"] == "completed"}:
                fail(f"{key}: completed task missing completed dependency")
        elif any(row[field] != "-" for field in ("Red", "Green", "Refactor", "Verification")):
            for field in ("Red", "Green", "Refactor", "Verification"):
                if row[field] != "-":
                    local_path(root, row[field])
    result["tasks"], result["order"], result["execution"] = tasks, dag(tasks), execution
    return result


def snapshot(root, target):
    paths = {path for path, _ in artifacts(root, target).values()}
    paths |= {target / "INDEX.md"} if (target / "INDEX.md").exists() else set()
    cap = root / ".specs" / "CAPABILITY_MAP.md"
    if cap.exists():
        paths.add(cap)
        for row in table(read(cap), "Modules"):
            paths.add(local_path(root, row["Contract"]))
    files = {path.relative_to(root).as_posix(): file_digest(path) for path in sorted(paths)}
    return {"files": files, "hash": digest(json.dumps(files, sort_keys=True).encode())}


def timestamp(value):
    if not isinstance(value, str):
        fail("timestamp must be ISO8601 string with timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        fail("timestamp needs timezone")
    if parsed > datetime.now(timezone.utc) + timedelta(minutes=5):
        fail("timestamp is in the future beyond five-minute clock skew")
    return parsed


def review_record(root, target, data):
    if not isinstance(data, dict):
        fail("review must be an object")
    for key in ("reviewer", "base", "diff", "summary"):
        if not isinstance(data.get(key), str) or len(data[key].strip()) < 3 or PLACEHOLDER.search(data[key]):
            fail(f"review missing substantive {key}")
        if key != "summary" and re.search(r"[\x00-\x1f\x7f#]", data[key]):
            fail(f"review {key}: single-line plain text required")
    if re.search(r"[\x00-\x08\x0b-\x1f\x7f]", data["summary"]):
        fail("review summary has control characters")
    timestamp(data.get("reviewed_at"))
    phase = data.get("phase")
    if phase not in ("pre-build", "post-build"):
        fail("review phase must be pre-build or post-build")
    if data.get("blockers") != []:
        fail("analysis has unresolved blockers")
    checks = data.get("checks")
    if not isinstance(checks, dict) or set(checks) != set(CHECKS):
        fail("review checklist incomplete")
    for key, value in checks.items():
        if not isinstance(value, str) or len(value.strip()) < 12 or PLACEHOLDER.search(value):
            fail(f"review {key}: needs human assessment, not boolean/pass")
        if value.startswith("N/A:") and key not in ("ui", "observability", "contracts"):
            fail(f"review {key}: cannot opt out")
    paths = data.get("evidence")
    if not isinstance(paths, list) or not paths:
        fail("review needs existing evidence files")
    evidence = {}
    for path in paths:
        if not isinstance(path, str):
            fail("evidence paths must be strings")
        evidence[path] = file_digest(local_path(root, path))
    scope = data.get("scope_files")
    implementation = data.get("implementation_files")
    if not isinstance(scope, list) or not scope or len(scope) != len(set(scope)):
        fail("review needs unique scope_files including code and tests")
    if not isinstance(implementation, list) or not implementation or not set(implementation) <= set(scope):
        fail("implementation_files must be a nonempty subset of scope_files")
    active = data.get("task") if phase == "post-build" else None
    planned = lint(root, target, "ready" if active else "tasks", active)
    if phase == "post-build" and active not in planned["tasks"]:
        fail("post-build review requires one explicit task")
    if phase == "post-build":
        execution_ready(root, planned, active)
    relevant = set(planned["tasks"]) if phase == "pre-build" else {
        key for key, row in planned["execution"].items() if row["Status"] == "completed"
    } | {active}
    for key, row in planned["execution"].items():
        if key not in relevant:
            continue
        for field in ("Red", "Green", "Refactor", "Verification"):
            if row[field] != "-":
                raw = row[field]
                evidence[raw] = file_digest(local_path(root, raw))
    expected_tests = {test.split("#")[0] for key in relevant for test in values(planned["tasks"][key]["Tests"])}
    owned = {path for key in relevant for path in values(planned["tasks"][key]["Files"])}
    if not (expected_tests | owned) <= set(scope):
        fail("scope_files must include every task-owned implementation/test file")
    future = {path for row in planned["tasks"].values() for path in values(row["Files"])} - owned
    if phase == "post-build" and set(scope) & future:
        fail("post-build scope must not include unstarted future task files")
    scope_hashes = {}
    for raw in scope:
        path = local_path(root, raw, phase == "post-build" and raw in owned)
        if path.exists():
            scope_hashes[raw] = file_digest(path)
        else:
            scope_hashes[raw] = None
    task_rows = {key: digest(json.dumps(row, sort_keys=True).encode()) for key, row in planned["tasks"].items()}
    return {"snapshot": snapshot(root, target), "evidence": evidence,
            "scope_hashes": scope_hashes, "task_rows": task_rows, "review": data}


def analyze(root, target, review_path):
    data = json_file(safe_absolute(review_path))
    lint(root, target, "tasks" if data.get("phase") == "pre-build" else "ready",
         data.get("task") if data.get("phase") == "post-build" else None)
    log = target / "CROSS_ANALYSIS.md"
    if log.exists() and PLACEHOLDER.search(read(log)):
        fail("CROSS_ANALYSIS has unresolved draft markers")
    report = review_record(root, target, data)
    serial = json.dumps(report, sort_keys=True, ensure_ascii=False)
    analysis_id = digest(serial.encode())[:24]
    report["id"] = analysis_id
    directory = target / "reviews"
    safe_absolute(directory)
    directory.mkdir(exist_ok=True)
    path = directory / f"analysis-{analysis_id}.json"
    if path.exists():
        fail("identical analysis already recorded; history not overwritten")
    exclusive(path, json.dumps(report, indent=2) + "\n")
    log = target / "CROSS_ANALYSIS.md"
    safe_absolute(log)
    old = read(log) if log.exists() else "# Cross-artifact analysis\n\n"
    entry = (
        f"\n## Review {analysis_id}\n"
        f"Snapshot: {report['snapshot']['hash']}\n\n"
        f"Evidence: reviews/{path.name}\n\n"
        f"Reviewer: {report['review']['reviewer']}\n\n"
        f"Base: {report['review']['base']}\n\nDiff: {report['review']['diff']}\n\n"
        + "\n".join("> " + line for line in report["review"]["summary"].splitlines()) + "\n\n"
        "Structural checks passed. Manual assessments remain reviewer claims, not implementation proof.\n"
    )
    # Append only. Existing disagreements and prior review entries remain.
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    with os.fdopen(os.open(log, flags, 0o644), "a", encoding="utf-8") as out:
        if not log.stat().st_size:
            out.write(old)
        out.write(entry)
    return {"analysis": path.relative_to(root).as_posix(), "id": analysis_id, "snapshot": report["snapshot"]["hash"]}


def execution_ready(root, result, task):
    row = result["execution"][task]
    if row["Status"] not in ("in-progress", "completed"):
        fail("verify task must have actual execution evidence, not planned status")
    fields = ("Red", "Green", "Refactor")
    if len({row[field] for field in fields}) != 3 or any(row[field] == "-" for field in fields):
        fail("verify requires distinct red/green/refactor evidence")
    for field in fields:
        file_digest(local_path(root, row[field]))


def predecessor_review(root, target, task, evidence, result):
    path = local_path(root, evidence["analysis"])
    if path.parent != target / "reviews" or not re.fullmatch(r"analysis-[a-f0-9]{24}\.json", path.name):
        fail(f"{task}: post-build analysis must be in selected feature reviews")
    if file_digest(path) != evidence["analysis_hash"]:
        fail(f"{task}: predecessor post-build analysis hash changed")
    report = json_file(path)
    serial = json.dumps({key: report[key] for key in ("snapshot", "evidence", "scope_hashes", "task_rows", "review")},
                        sort_keys=True, ensure_ascii=False)
    if report.get("id") != digest(serial.encode())[:24] or path.stem != f"analysis-{report['id']}":
        fail(f"{task}: predecessor analysis content/address mismatch")
    if report["review"].get("phase") != "post-build" or report["review"].get("task") != task or report["review"].get("blockers") != []:
        fail(f"{task}: completed task needs its own post-build review")
    timestamp(report["review"].get("reviewed_at"))
    if report.get("task_rows", {}).get(task) != digest(json.dumps(result["tasks"][task], sort_keys=True).encode()):
        fail(f"{task}: task definition changed since post-build review")
    current = snapshot(root, target)["files"]
    docs = artifacts(root, target)
    task_path = docs["TASKS"][0].relative_to(root).as_posix()
    only_task = all(path != docs["TASKS"][0] for key, (path, _) in docs.items() if key != "TASKS")
    old = report["snapshot"].get("files", {})
    for raw, sha in current.items():
        if only_task and raw == task_path:
            continue
        if old.get(raw) != sha:
            fail(f"{task}: authoritative specs changed since post-build review")
    for raw in values(result["tasks"][task]["Files"]):
        if report.get("scope_hashes", {}).get(raw) != file_digest(local_path(root, raw)):
            fail(f"{task}: predecessor code/test differs from post-build review")
    for field in ("Red", "Green", "Refactor"):
        raw = result["execution"][task][field]
        if report.get("evidence", {}).get(raw) != file_digest(local_path(root, raw)):
            fail(f"{task}: predecessor execution evidence differs from post-build review")
    if not re.search(rf"^## Review {re.escape(report['id'])}$", read(target / "CROSS_ANALYSIS.md"), re.M):
        fail(f"{task}: predecessor CROSS_ANALYSIS evidence missing")


def gate(root, target, approval_path, task=None, purpose="build"):
    approval = json_file(safe_absolute(approval_path))
    if approval.get("decision") != "approved" or approval.get("authority") != "human":
        fail("explicit human approval required")
    for key in ("authorizer", "statement"):
        if not isinstance(approval.get(key), str) or len(approval[key].strip()) < 3 or PLACEHOLDER.search(approval[key]):
            fail(f"approval missing {key}")
    when = timestamp(approval.get("approved_at"))
    report_path = local_path(root, approval.get("analysis", ""))
    if report_path.parent != target / "reviews" or not re.fullmatch(r"analysis-[a-f0-9]{24}\.json", report_path.name):
        fail("approval must reference immutable analysis in selected feature reviews")
    report = json_file(report_path)
    phase = "pre-build" if purpose == "build" else "post-build"
    if report.get("review", {}).get("phase") != phase:
        fail(f"{purpose} needs {phase} analysis")
    selected = approval.get("task")
    if purpose == "verify" and report.get("review", {}).get("task") != selected:
        fail("verify approval task must match post-build review task")
    result = lint(root, target, "tasks" if purpose == "build" else "ready", selected if purpose == "verify" else None)
    expected = review_record(root, target, report.get("review"))
    if any(report.get(key) != expected[key] for key in ("snapshot", "evidence", "scope_hashes", "task_rows")):
        fail("stale analysis: specs, contract, or evidence changed")
    serial = json.dumps({k: report[k] for k in ("snapshot", "evidence", "scope_hashes", "task_rows", "review")}, sort_keys=True, ensure_ascii=False)
    if report.get("id") != digest(serial.encode())[:24] or report_path.stem != f"analysis-{report['id']}":
        fail("analysis content/address mismatch")
    if approval.get("snapshot") != expected["snapshot"]["hash"] or approval.get("analysis_hash") != file_digest(report_path):
        fail("approval hash does not match current analysis/specs")
    if when < timestamp(report["review"]["reviewed_at"]):
        fail("approval predates analysis review")
    if approval["authorizer"] == report["review"]["reviewer"] and (
        not isinstance(approval.get("self_review_policy"), str) or len(approval["self_review_policy"].strip()) < 12
    ):
        fail("same reviewer and authorizer require explicit self_review_policy")
    log = read(target / "CROSS_ANALYSIS.md")
    if not re.search(rf"^## Review {re.escape(report['id'])}$", log, re.M):
        fail("CROSS_ANALYSIS review evidence missing")
    if approval.get("cross_analysis_hash") != file_digest(target / "CROSS_ANALYSIS.md"):
        fail("CROSS_ANALYSIS changed after approval; human re-review required")
    completed = approval.get("completed", {})
    if not isinstance(completed, dict):
        fail("completed must map TASK IDs to evidence files")
    for key, evidence in completed.items():
        if key not in result["tasks"]:
            fail(f"unknown completed task: {key}")
        if not isinstance(evidence, dict) or set(evidence) != {"path", "sha256", "analysis", "analysis_hash"}:
            fail("completed evidence needs verification path/hash and post-build analysis/hash")
        if file_digest(local_path(root, evidence["path"])) != evidence["sha256"]:
            fail(f"{key}: completed evidence changed")
        if result["execution"][key]["Status"] != "completed" or result["execution"][key]["Verification"] != evidence["path"]:
            fail(f"{key}: completion record does not match TASKS execution log")
        predecessor_review(root, target, key, evidence, result)
    if set(completed) != {key for key, row in result["execution"].items() if row["Status"] == "completed"}:
        fail("approval completion map does not match TASKS")
    for key in completed:
        if not set(values(result["tasks"][key]["Depends"])) <= set(completed):
            fail(f"{key}: completed task missing completed dependency")
    if purpose == "verify":
        if selected not in result["tasks"]:
            fail("verify requires one explicit task")
        execution_ready(root, result, selected)
        if not set(values(result["tasks"][selected]["Depends"])) <= set(completed):
            fail("verify task dependencies lack completed evidence")
        if task is not None and task != selected:
            fail("requested task differs from human-authorized task")
        return {"status": "structurally_reviewed", "task": selected,
                "warning": "Not proof of code compliance or test execution."}
    authorized = approval.get("task")
    if authorized not in result["tasks"]:
        fail("approval must authorize one explicit task")
    if task is not None and task != authorized:
        fail("requested task differs from human-authorized task")
    selected = authorized
    if selected is None or selected not in result["tasks"] or selected in completed:
        fail("no valid pending task selected")
    if not set(values(result["tasks"][selected]["Depends"])) <= set(completed):
        fail(f"{selected}: dependencies lack verified completion evidence")
    return {"status": "structurally_authorized", "task": selected,
            "warning": "Local records are not authentication. Confirm real human authorization; review implementation separately."}


def scaffold(root, target, feature=None):
    destinations = {}
    for key in ARTIFACTS:
        parent = root / ".specs" if feature and key in GLOBALS else target
        path = parent / f"{key}.md"
        if feature and key in GLOBALS and path.exists():
            read(path)
            continue
        destinations[path] = ASSETS / "templates" / f"{key}.md"
    for key in ("INDEX", "CROSS_ANALYSIS"):
        destinations[target / f"{key}.md"] = ASSETS / "templates" / f"{key}.md"
    if feature and not (root / ".specs" / "CAPABILITY_MAP.md").exists():
        destinations[root / ".specs" / "CAPABILITY_MAP.md"] = ASSETS / "templates" / "CAPABILITY_MAP.md"
    # Preflight all targets before creating anything.
    for path in destinations:
        safe_absolute(path)
        if path.exists():
            fail(f"refusing to clobber: {path}")
    contents = {}
    for path, source in destinations.items():
        content = read(source)
        for key in ARTIFACTS:
            parent = root / ".specs" if feature and key in GLOBALS else target
            content = content.replace(f"{{{{{key}_PATH}}}}", (parent / f"{key}.md").relative_to(root).as_posix())
        contents[path] = content
    for path, content in contents.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        exclusive(path, content)
    return {"status": "draft", "created": [x.relative_to(root).as_posix() for x in destinations]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Existing project root")
    parser.add_argument("--feature", help="Safe feature ID; otherwise flat .specs")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scaffold")
    p = sub.add_parser("lint")
    p.add_argument("--stage", choices=("spec", "plan", "tasks", "ready"), default="ready")
    sub.add_parser("snapshot")
    sub.add_parser("extract")
    p = sub.add_parser("analyze")
    p.add_argument("--review", required=True)
    p = sub.add_parser("gate")
    p.add_argument("--approval", required=True)
    p.add_argument("--task")
    p.add_argument("--purpose", choices=("build", "verify"), default="build")
    args = parser.parse_args(argv)
    try:
        root, target = resolve(args.root, args.feature)
        if args.command == "scaffold":
            output = scaffold(root, target, args.feature)
        elif args.command == "lint":
            data = lint(root, target, args.stage)
            output = {"status": "structural_pass", "stage": args.stage, "task_order": data["order"]}
        elif args.command == "snapshot":
            output = snapshot(root, target)
        elif args.command == "extract":
            output = {"parser": "legacy-SpecParser" if legacy_parser() else "standalone-GWT",
                      "criteria": lint(root, target, "spec")["criteria"]}
        elif args.command == "analyze":
            output = analyze(root, target, args.review)
        else:
            output = gate(root, target, args.approval, args.task, args.purpose)
        print(json.dumps(output, indent=2))
        return 0
    except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
