#!/usr/bin/env python3
"""Generate schemas/diagram.schema.json from the validator's field specs.

    generate_schema.py --write   regenerate the schema
    generate_schema.py --check   fail if the committed schema is stale

The previous arrangement had two hand-written descriptions of one contract and a
test that compared a few enums and required-key lists. That test passed while the
two genuinely disagreed: the schema allowed sequence fields on a graph document
and `orientation` on a sequence document, both of which the validator rejects, and
three independent schema mutations left the whole suite green.

Generating one side from the other removes the possibility rather than testing for
it. `scripts/diagram_ir.py` is the source of truth; this file is derived.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = HERE.parent / "schemas" / "diagram.schema.json"
sys.path.insert(0, str(HERE))
import diagram_ir as ir  # noqa: E402

DOC = {
    "kind": "One diagram answers one question. The kind picks the layout and the vocabulary.",
    "title": "Short. Names the system or the flow.",
    "subtitle": "One or two sentences. State what the diagram asserts, so a reader can tell when it has gone stale.",
    "footer": "Provenance: commit, date, or source of truth. Rendered in the artifact's footer.",
    "orientation": "LR (default) or TB. Not accepted on a sequence document.",
    "legend": "Extra legend entries. Loop, async and boundary entries are derived automatically.",
    "groups": "Boundaries: trust, network or ownership, not teams or directories. Laid out as swimlanes, so a node belongs to at most one.",
    "nodes": "Required for every kind except sequence.",
    "edges": "Direction is meaning: an edge points the way a request or a record travels. Exact duplicates are rejected.",
    "participants": "Required for the sequence kind. Lifelines, left to right.",
    "messages": "Required for the sequence kind. Rendered in order, numbered.",
    "id": "Referenced by edges and groups. Short and stable.",
    "label": "What a reader calls this thing. Wrapped automatically, including tokens with no spaces.",
    "shape": "box service, round start or end state, cylinder datastore, queue queue or topic, cloud managed or third-party service, actor a person, decision a branch.",
    "note": "One short line that says something the label cannot: a constraint, a guarantee, a gotcha.",
    "tech": "The concrete technology, shown small and monospaced.",
    "accent": "Use once per diagram, on the thing the diagram exists to show.",
    "style": "Edges that close a cycle default to dashed.",
    "from": "A declared id.",
    "to": "A declared id.",
}

# Maps a spec type to its JSON Schema fragment. Mirrors _type_ok in diagram_ir.
FRAGMENTS = {
    "str": {"type": "string", "minLength": 1},
    "text": {"type": "string"},
    "bool": {"type": "boolean"},
    "strlist": {"type": "array", "items": {"type": "string"}},
    "ids": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
}


def fragment(kind, key):
    base = kind.rstrip("!")
    if base in ir.ENUMS:
        frag = {"enum": list(ir.ENUMS[base])}
        if base in ("shape", "style"):
            frag["default"] = ir.ENUMS[base][0]
        if base == "orientation":
            frag["default"] = "LR"
        return frag
    if base == "objlist":
        return {"type": "array", "items": {"$ref": f"#/$defs/{ITEM_OF[key]}"}}
    return dict(FRAGMENTS[base])


ITEM_OF = {
    "nodes": "node",
    "edges": "edge",
    "groups": "group",
    "participants": "participant",
    "messages": "message",
}
MIN_ITEMS = {"nodes", "participants", "messages"}


def obj_schema(spec, title=None):
    props = {}
    for key, kind in spec.items():
        frag = fragment(kind, key)
        if key in DOC:
            frag["description"] = DOC[key]
        if key in MIN_ITEMS:
            frag["minItems"] = 1
        props[key] = frag
    out = {
        "type": "object",
        "required": [k for k, v in spec.items() if v.endswith("!")],
        "properties": props,
        "additionalProperties": False,
    }
    if title:
        out["title"] = title
    return out


def build():
    graph = obj_schema(ir.TOP_GRAPH)
    sequence = obj_schema(ir.TOP_SEQUENCE)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/bughunt8/skills/skills/engineering/architecture-diagrams/schemas/diagram.schema.json",
        "title": "Diagram document",
        "description": (
            "GENERATED FILE. Do not edit by hand. Produced from the field specs in "
            "scripts/diagram_ir.py by scripts/generate_schema.py, which is the only "
            "definition of this contract. Regenerate with: python3 "
            "scripts/generate_schema.py --write. A test fails if this file is stale. "
            "A graph document (architecture, workflow, dataflow, lifecycle) and a "
            "sequence document accept different keys, so the two shapes are given as "
            "a oneOf rather than merged."
        ),
        "oneOf": [
            dict(graph, title="Graph document: architecture, workflow, dataflow, lifecycle"),
            dict(sequence, title="Sequence document"),
        ],
        "$defs": {
            "node": obj_schema(ir.NODE_SPEC, "Node"),
            "edge": obj_schema(ir.EDGE_SPEC, "Edge"),
            "group": obj_schema(ir.GROUP_SPEC, "Group, drawn as a boundary"),
            "participant": obj_schema(ir.PARTICIPANT_SPEC, "Sequence participant"),
            "message": obj_schema(ir.MESSAGE_SPEC, "Sequence message"),
        },
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    text = json.dumps(build(), indent=2) + "\n"
    if args.check:
        current = SCHEMA.read_text("utf-8") if SCHEMA.exists() else ""
        if current != text:
            print(
                "error: schemas/diagram.schema.json is stale against the validator's "
                "field specs. Run: python3 scripts/generate_schema.py --write",
                file=sys.stderr,
            )
            return 1
        print("schema is up to date with the validator")
        return 0
    SCHEMA.write_text(text, encoding="utf-8")
    print(f"wrote {SCHEMA.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
