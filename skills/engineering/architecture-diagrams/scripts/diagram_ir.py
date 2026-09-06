"""Validation for the diagram intermediate representation (IR).

This module is the authoritative definition of what a valid diagram document is.
`schemas/diagram.schema.json` documents the same contract for editors and for
anyone who wants to validate with a general JSON Schema tool, and
`tests/test_contract.py` fails if the two ever disagree.

Validation is hand-rolled against the standard library on purpose. A skill that
an agent drops into an arbitrary repository cannot assume `pip install` is
available or allowed, so the whole renderer runs on a bare Python 3.9+.

Two document shapes exist:

  Graph kinds (architecture, workflow, dataflow, lifecycle)
      nodes + edges, optionally grouped. Cycles are permitted; lifecycle state
      machines need them.

  Sequence kind
      participants + messages down a set of lifelines.

Errors are collected rather than raised one at a time, so an author fixing a
document sees everything wrong with it in one pass. Every message names the
JSON path it applies to.
"""

from __future__ import annotations

GRAPH_KINDS = ("architecture", "workflow", "dataflow", "lifecycle")
SEQUENCE_KINDS = ("sequence",)
ALL_KINDS = GRAPH_KINDS + SEQUENCE_KINDS

NODE_SHAPES = ("box", "round", "cylinder", "queue", "cloud", "actor", "decision")
EDGE_STYLES = ("solid", "dashed", "dotted")
ORIENTATIONS = ("LR", "TB")

# Kept in sync with schemas/diagram.schema.json by tests/test_contract.py.
REQUIRED_TOP = ("kind", "title")
REQUIRED_NODE = ("id", "label")
REQUIRED_EDGE = ("from", "to")
REQUIRED_PARTICIPANT = ("id", "label")
REQUIRED_MESSAGE = ("from", "to")


class ValidationError(Exception):
    """Raised with every problem found, not just the first."""

    def __init__(self, problems):
        self.problems = list(problems)
        joined = "\n".join(f"  - {p}" for p in self.problems)
        super().__init__(f"{len(self.problems)} problem(s) in the diagram document:\n{joined}")


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


# Field specifications. The suffix "!" marks a required field. These are the
# single source of truth: schemas/diagram.schema.json is generated from them by
# scripts/generate_schema.py, so the two cannot drift.
NODE_SPEC = {
    "id": "str!",
    "label": "str!",
    "shape": "shape",
    "note": "text",
    "tech": "text",
    "accent": "bool",
}
EDGE_SPEC = {"from": "str!", "to": "str!", "label": "text", "style": "style", "accent": "bool"}
PARTICIPANT_SPEC = {"id": "str!", "label": "str!", "shape": "shape", "note": "text"}
MESSAGE_SPEC = {
    "from": "str!",
    "to": "str!",
    "label": "text",
    "style": "style",
    "note": "text",
    "accent": "bool",
}
GROUP_SPEC = {"label": "str!", "nodes": "ids!"}
TOP_COMMON = {"kind": "kind!", "title": "str!", "subtitle": "text", "footer": "text",
              "legend": "strlist"}
TOP_GRAPH = dict(TOP_COMMON, orientation="orientation", groups="objlist", nodes="objlist!",
                 edges="objlist")
TOP_SEQUENCE = dict(TOP_COMMON, participants="objlist!", messages="objlist!")

ENUMS = {
    "shape": NODE_SHAPES,
    "style": EDGE_STYLES,
    "orientation": ORIENTATIONS,
    "kind": ALL_KINDS,
}

REQUIRED_TOP = ("kind", "title")
REQUIRED_NODE = ("id", "label")
REQUIRED_EDGE = ("from", "to")
REQUIRED_PARTICIPANT = ("id", "label")
REQUIRED_MESSAGE = ("from", "to")


def _type_ok(kind, value, path, problems):
    """Check one field's type. Returns False when the value is unusable.

    Every optional field is checked, not just the required ones. Previously only
    required fields were type-checked, so {"legend": 7} and {"tech": 7} passed
    validation and then crashed the renderer with a TypeError. A validator that
    lets a document through and leaves the renderer to fail is worse than no
    validator, because the error surfaces far from its cause.
    """
    base = kind.rstrip("!")
    if base == "str":
        if not _is_str(value):
            problems.append(f"{path}: must be a non-empty string")
            return False
    elif base == "text":
        if not isinstance(value, str):
            problems.append(f"{path}: must be a string, got {type(value).__name__}")
            return False
    elif base == "bool":
        if not isinstance(value, bool):
            problems.append(f"{path}: must be true or false, got {type(value).__name__}")
            return False
    elif base in ENUMS:
        if not isinstance(value, str):
            problems.append(f"{path}: must be a string, got {type(value).__name__}")
            return False
        if value not in ENUMS[base]:
            problems.append(
                f"{path}: {value!r} is not one of {', '.join(map(repr, ENUMS[base]))}"
            )
            return False
    elif base in ("strlist", "ids"):
        if not isinstance(value, list):
            problems.append(f"{path}: must be a list, got {type(value).__name__}")
            return False
        if base == "ids" and not value:
            problems.append(f"{path}: must not be empty")
            return False
        for i, item in enumerate(value):
            # Checked before the value is ever used as a dict key: an unhashable
            # member used to crash the validator itself with a TypeError.
            if not _is_str(item):
                problems.append(f"{path}[{i}]: must be a non-empty string")
                return False
    elif base == "objlist":
        if not isinstance(value, list):
            problems.append(f"{path}: must be a list, got {type(value).__name__}")
            return False
    return True


def _check_object(obj, path, spec, problems):
    """Validate one object against a spec: required keys, no unknown keys, types."""
    if not isinstance(obj, dict):
        problems.append(f"{path}: expected an object, got {type(obj).__name__}")
        return False
    ok = True
    for key, kind in spec.items():
        if kind.endswith("!") and key not in obj:
            problems.append(f"{path}: missing required key '{key}'")
            ok = False
    for key in obj:
        if key not in spec:
            problems.append(
                f"{path}: unknown key '{key}' (allowed: {', '.join(sorted(spec))})"
            )
            ok = False
            continue
        if not _type_ok(spec[key], obj[key], f"{path}.{key}", problems):
            ok = False
    return ok


def validate(doc):
    """Validate a loaded diagram document. Raises ValidationError, else returns doc."""
    problems = []

    if not isinstance(doc, dict):
        raise ValidationError([f"document root: expected an object, got {type(doc).__name__}"])

    kind = doc.get("kind")
    if kind is None:
        problems.append("document root: missing required key 'kind'")
    elif kind not in ALL_KINDS:
        problems.append(
            f"kind: {kind!r} is not one of {', '.join(map(repr, ALL_KINDS))}"
        )

    # An unknown kind means the body shape is unknown, but the parts that do not
    # depend on it are still worth reporting in the same pass.
    if kind not in ALL_KINDS:
        if "title" in doc and not _is_str(doc["title"]):
            problems.append("title: must be a non-empty string")
        elif "title" not in doc:
            problems.append("document root: missing required key 'title'")
        problems.append(
            "further checks were skipped because 'kind' decides which fields apply"
        )
        raise ValidationError(problems)

    spec = TOP_SEQUENCE if kind in SEQUENCE_KINDS else TOP_GRAPH
    _check_object(doc, "document root", spec, problems)

    if kind in SEQUENCE_KINDS:
        _validate_sequence(doc, problems)
    else:
        _validate_graph(doc, problems)

    if problems:
        raise ValidationError(problems)
    return doc


def _validate_graph(doc, problems):
    nodes = doc.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        problems.append("nodes: a graph diagram needs a non-empty list of nodes")
        raise ValidationError(problems)

    ids = {}
    for i, node in enumerate(nodes):
        path = f"nodes[{i}]"
        _check_object(node, path, NODE_SPEC, problems)
        nid = node.get("id") if isinstance(node, dict) else None
        if not _is_str(nid):
            continue
        if nid in ids:
            problems.append(f"{path}.id: duplicate node id {nid!r} (also at nodes[{ids[nid]}])")
        else:
            ids[nid] = i

    edges = doc.get("edges", [])
    if isinstance(edges, list):
        seen_edges = {}
        for i, edge in enumerate(edges):
            path = f"edges[{i}]"
            _check_object(edge, path, EDGE_SPEC, problems)
            if not isinstance(edge, dict) or not all(
                _is_str(edge.get(k)) for k in ("from", "to")
            ):
                continue
            for end in ("from", "to"):
                if edge[end] not in ids:
                    problems.append(
                        f"{path}.{end}: {edge[end]!r} is not a declared node id. "
                        f"An edge to a node that does not exist is the most common "
                        f"authoring mistake, so it is an error rather than a dropped edge."
                    )
            # An exact duplicate draws itself twice in the same place, with no
            # way for a reader to tell. Parallel edges with different labels are
            # legitimate and are fanned apart by the layout instead.
            key = (edge["from"], edge["to"], edge.get("label"), edge.get("style"))
            if key in seen_edges:
                problems.append(
                    f"{path}: exact duplicate of edges[{seen_edges[key]}]; it would be "
                    f"drawn twice in the same place. Remove it, or give it a distinct label."
                )
            else:
                seen_edges[key] = i

    groups = doc.get("groups", [])
    if isinstance(groups, list):
        claimed = {}
        for i, group in enumerate(groups):
            path = f"groups[{i}]"
            _check_object(group, path, GROUP_SPEC, problems)
            members = group.get("nodes") if isinstance(group, dict) else None
            if not isinstance(members, list):
                continue
            for member in members:
                if not _is_str(member):
                    continue
                if member not in ids:
                    problems.append(f"{path}.nodes: {member!r} is not a declared node id")
                elif member in claimed:
                    problems.append(
                        f"{path}.nodes: node {member!r} is already in groups[{claimed[member]}]; "
                        f"a node may belong to at most one group"
                    )
                else:
                    claimed[member] = i


def _validate_sequence(doc, problems):
    parts = doc.get("participants")
    if not isinstance(parts, list) or not parts:
        problems.append("participants: a sequence diagram needs a non-empty list")
        raise ValidationError(problems)

    ids = {}
    for i, part in enumerate(parts):
        path = f"participants[{i}]"
        _check_object(part, path, PARTICIPANT_SPEC, problems)
        pid = part.get("id") if isinstance(part, dict) else None
        if not _is_str(pid):
            continue
        if pid in ids:
            problems.append(f"{path}.id: duplicate participant id {pid!r}")
        else:
            ids[pid] = i

    messages = doc.get("messages")
    if not isinstance(messages, list) or not messages:
        problems.append("messages: a sequence diagram needs a non-empty list")
        return
    for i, msg in enumerate(messages):
        path = f"messages[{i}]"
        _check_object(msg, path, MESSAGE_SPEC, problems)
        if not isinstance(msg, dict) or not all(
            _is_str(msg.get(k)) for k in ("from", "to")
        ):
            continue
        for end in ("from", "to"):
            if msg[end] not in ids:
                problems.append(
                    f"{path}.{end}: {msg[end]!r} is not a declared participant id"
                )
