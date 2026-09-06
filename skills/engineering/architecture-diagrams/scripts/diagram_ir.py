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


def _check_keys(obj, path, required, optional, problems):
    """Require what must be present and reject what is not recognised.

    Unknown keys are errors rather than warnings. A silently ignored key is how
    an author ends up convinced they set something that never took effect.
    """
    if not isinstance(obj, dict):
        problems.append(f"{path}: expected an object, got {type(obj).__name__}")
        return False
    ok = True
    for key in required:
        if key not in obj:
            problems.append(f"{path}: missing required key '{key}'")
            ok = False
        elif not _is_str(obj[key]) and key not in ("nodes",):
            problems.append(f"{path}.{key}: must be a non-empty string")
            ok = False
    allowed = set(required) | set(optional)
    for key in obj:
        if key not in allowed:
            problems.append(
                f"{path}: unknown key '{key}' (allowed: {', '.join(sorted(allowed))})"
            )
            ok = False
    return ok


def _check_enum(obj, path, key, allowed, problems):
    if key in obj and obj[key] not in allowed:
        problems.append(
            f"{path}.{key}: {obj[key]!r} is not one of {', '.join(map(repr, allowed))}"
        )


def validate(doc):
    """Validate a loaded diagram document. Raises ValidationError, else returns doc."""
    problems = []

    if not isinstance(doc, dict):
        raise ValidationError([f"document root: expected an object, got {type(doc).__name__}"])

    for key in REQUIRED_TOP:
        if key not in doc:
            problems.append(f"document root: missing required key '{key}'")
        elif not _is_str(doc[key]):
            problems.append(f"{key}: must be a non-empty string")

    kind = doc.get("kind")
    if kind is not None and kind not in ALL_KINDS:
        problems.append(
            f"kind: {kind!r} is not one of {', '.join(map(repr, ALL_KINDS))}"
        )
        # Without a known kind the rest cannot be checked meaningfully.
        raise ValidationError(problems)

    _check_enum(doc, "document root", "orientation", ORIENTATIONS, problems)
    for key in ("subtitle", "footer"):
        if key in doc and not isinstance(doc[key], str):
            problems.append(f"{key}: must be a string")

    if kind in SEQUENCE_KINDS:
        _validate_sequence(doc, problems)
    else:
        _validate_graph(doc, problems)

    if problems:
        raise ValidationError(problems)
    return doc


def _validate_graph(doc, problems):
    top_optional = ("subtitle", "footer", "orientation", "groups", "legend")
    for key in doc:
        if key not in set(REQUIRED_TOP) | set(top_optional) | {"nodes", "edges"}:
            problems.append(f"document root: unknown key '{key}' for kind {doc['kind']!r}")

    nodes = doc.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        problems.append("nodes: a graph diagram needs a non-empty list of nodes")
        raise ValidationError(problems)

    ids = {}
    for i, node in enumerate(nodes):
        path = f"nodes[{i}]"
        if not _check_keys(
            node, path, REQUIRED_NODE, ("shape", "note", "tech", "accent"), problems
        ):
            continue
        _check_enum(node, path, "shape", NODE_SHAPES, problems)
        nid = node["id"]
        if nid in ids:
            problems.append(f"{path}.id: duplicate node id {nid!r} (also at nodes[{ids[nid]}])")
        else:
            ids[nid] = i

    edges = doc.get("edges", [])
    if not isinstance(edges, list):
        problems.append("edges: must be a list")
        edges = []
    for i, edge in enumerate(edges):
        path = f"edges[{i}]"
        if not _check_keys(
            edge, path, REQUIRED_EDGE, ("label", "style", "accent"), problems
        ):
            continue
        _check_enum(edge, path, "style", EDGE_STYLES, problems)
        for end in ("from", "to"):
            if edge[end] not in ids:
                problems.append(
                    f"{path}.{end}: {edge[end]!r} is not a declared node id. "
                    f"An edge to a node that does not exist is the most common "
                    f"authoring mistake, so it is an error rather than a dropped edge."
                )

    groups = doc.get("groups", [])
    if not isinstance(groups, list):
        problems.append("groups: must be a list")
        groups = []
    claimed = {}
    for i, group in enumerate(groups):
        path = f"groups[{i}]"
        if not isinstance(group, dict):
            problems.append(f"{path}: expected an object")
            continue
        if not _is_str(group.get("label")):
            problems.append(f"{path}.label: must be a non-empty string")
        members = group.get("nodes")
        if not isinstance(members, list) or not members:
            problems.append(f"{path}.nodes: must be a non-empty list of node ids")
            continue
        for member in members:
            if member not in ids:
                problems.append(f"{path}.nodes: {member!r} is not a declared node id")
            elif member in claimed:
                # Overlapping groups cannot both be drawn as a clean boundary.
                problems.append(
                    f"{path}.nodes: node {member!r} is already in groups[{claimed[member]}]; "
                    f"a node may belong to at most one group"
                )
            else:
                claimed[member] = i


def _validate_sequence(doc, problems):
    top_optional = ("subtitle", "footer", "legend")
    for key in doc:
        if key not in set(REQUIRED_TOP) | set(top_optional) | {"participants", "messages"}:
            problems.append(f"document root: unknown key '{key}' for kind 'sequence'")

    parts = doc.get("participants")
    if not isinstance(parts, list) or not parts:
        problems.append("participants: a sequence diagram needs a non-empty list")
        raise ValidationError(problems)

    ids = {}
    for i, part in enumerate(parts):
        path = f"participants[{i}]"
        if not _check_keys(part, path, REQUIRED_PARTICIPANT, ("shape", "note"), problems):
            continue
        _check_enum(part, path, "shape", NODE_SHAPES, problems)
        pid = part["id"]
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
        if not _check_keys(
            msg, path, REQUIRED_MESSAGE, ("label", "style", "note", "accent"), problems
        ):
            continue
        _check_enum(msg, path, "style", EDGE_STYLES, problems)
        for end in ("from", "to"):
            if msg[end] not in ids:
                problems.append(
                    f"{path}.{end}: {msg[end]!r} is not a declared participant id"
                )
