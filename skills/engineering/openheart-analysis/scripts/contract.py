#!/usr/bin/env python3
"""Define the portable analysis contract and generate its bundled JSON files."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = (
    "ingestion", "syntax", "symbols", "control_flow", "data_flow",
    "calls", "traceability", "paths", "uml", "unified",
)
TITLES = {
    "class": "Class", "package": "Package", "component": "Component",
    "composite": "Composite structure", "object": "Object",
    "deployment": "Deployment", "profile": "Profile", "sequence": "Sequence",
    "statemachine": "State machine", "activity": "Activity", "usecase": "Use case",
    "communication": "Communication", "interaction": "Interaction overview",
    "timing": "Timing", "cfg": "Control flow", "dfg": "Data flow",
    "cdg": "Control dependence", "callgraph": "Call graph",
    "robdd": "ROBDD path summary", "ast": "Abstract syntax tree",
}
STATUSES = ["complete", "partial", "insufficient_evidence", "not_computed", "not_requested"]
NODE_KINDS = [
    "token", "ast", "symbol", "scope", "block", "ssa", "phi", "callsite", "trace",
    "bdd", "terminal", "class", "interface", "package", "component", "object",
    "action", "state", "actor", "port", "usecase", "pattern", "interaction",
    "lifeline", "deployment", "profile", "stereotype", "file", "artifact",
    "partition", "decision", "constraint", "instance", "annotation", "initial",
    "final", "function", "expression", "variable",
]
EDGE_KINDS = [
    "next_token", "contains", "declares", "extends", "implements", "type_use",
    "control_flow", "true", "false", "loop_back", "exception", "data_flow",
    "def_use", "control_dependence", "calls", "candidate_call", "recursion",
    "source_of", "projects_to", "low", "high", "generalization", "realization",
    "composition", "aggregation", "association", "dependency", "message",
    "transition", "include", "extend", "allocation", "deployment", "assembly",
    "delegation", "nesting", "return", "create", "destroy", "state_transition",
    "instantiates", "uses", "owns", "satisfies", "supplies", "links", "enters", "exits",
]
STAGE_NODE_KINDS = {
    "ingestion": {"token", "file"}, "syntax": {"ast"},
    "symbols": {"symbol", "scope", "class", "interface"},
    "control_flow": {"block"}, "data_flow": {"ssa", "phi", "variable"},
    "calls": {"callsite", "symbol"}, "traceability": {"trace"},
    "paths": {"bdd", "terminal"}, "uml": set(NODE_KINDS) - {"token", "ssa", "phi"},
    "unified": set(NODE_KINDS),
}
STAGE_EDGE_KINDS = {
    "ingestion": {"next_token", "contains"}, "syntax": {"contains"},
    "symbols": {"declares", "extends", "implements", "type_use", "contains", "dependency"},
    "control_flow": {"control_flow", "true", "false", "loop_back", "exception", "return"},
    "data_flow": {"data_flow", "def_use", "control_dependence"},
    "calls": {"calls", "candidate_call", "recursion"},
    "traceability": {"source_of", "projects_to"}, "paths": {"low", "high"},
    "uml": set(EDGE_KINDS), "unified": set(EDGE_KINDS),
}


def obj(properties, required=None, additional=False):
    return {
        "type": "object", "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": additional,
    }


def string(minimum=0, pattern=None):
    result = {"type": "string", "minLength": minimum}
    if pattern:
        result["pattern"] = pattern
    return result


def array(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


def ref(name):
    return {"$ref": "#/$defs/" + name}


def schema():
    evidence = obj({
        "file": string(1), "line_start": {"type": "integer", "minimum": 1},
        "line_end": {"type": "integer", "minimum": 1}, "excerpt": string(1),
    })
    member = obj({
        "visibility": {"enum": ["+", "-", "#", "~"]}, "name": string(1),
        "type_name": string(), "signature": string(),
        "is_static": {"type": "boolean"}, "is_final": {"type": "boolean"},
    })
    shared = {
        "id": string(1),
        "basis": {"enum": ["source", "derived", "inferred", "observed"]},
        "evidence": array(ref("evidence"), 1),
        "attributes": {"type": "object"},
    }
    node = obj({
        **shared, "label": string(1), "kind": {"enum": NODE_KINDS},
        "parent": {"type": ["string", "null"]},
        "fields": array(ref("member")), "methods": array(ref("member")),
    })
    edge = obj({
        **shared, "source": string(1), "target": string(1), "label": string(),
        "kind": {"enum": EDGE_KINDS},
    })
    graph = obj({
        "status": {"enum": STATUSES}, "reason": string(),
        "method": string(1), "nodes": array(ref("node")), "edges": array(ref("edge")),
    })
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:bughunt8:openheart-analysis:1.0",
        "title": "OpenHeart-derived normalized analysis, not binary SCPG",
        **obj({
            "schema_version": {"const": "1.0"},
            "source": obj({
                "repository": string(1), "revision": string(1),
                "scope": array(string(1), 1), "languages": array(string(1), 1),
                "exclusions": array(string(1)),
            }),
            "files": array(obj({
                "path": string(1), "sha256": string(64, r"^[a-f0-9]{64}$"),
                "line_count": {"type": "integer", "minimum": 0},
                "encoding": {"const": "utf-8"},
                "role": {"enum": ["source", "trace", "snapshot", "specification"]},
            })),
            "stages": obj({name: ref("graph") for name in STAGES}),
            "diagrams": obj({name: ref("graph") for name in TITLES}),
            "limitations": array(string(1)),
        }),
        "$defs": {
            "evidence": evidence, "member": member, "node": node,
            "edge": edge, "graph": graph,
        },
    }


def catalog():
    return {
        "schema_version": "1.0",
        "upstream_commit": "0bf962fc06e975e9ea7610242b8997b1391fec05",
        "act_alias": {"id": "ACT", "canonical": "activity", "provisional": True},
        "diagrams": [
            {
                "id": key, "title": title, "upstream": key != "ast",
                "mermaid": {
                    "class": "classDiagram", "sequence": "sequenceDiagram",
                    "statemachine": "stateDiagram-v2",
                }.get(key, "flowchart TD"),
                "native_notation": key in {"class", "sequence", "statemachine"},
            }
            for key, title in TITLES.items()
        ],
    }


def empty_graph(status="not_requested", reason="Outside this run's requested scope."):
    return {
        "status": status, "reason": reason, "method": "not run",
        "nodes": [], "edges": [],
    }


def empty_model():
    return {
        "schema_version": "1.0",
        "source": {
            "repository": "FILL_ME", "revision": "unversioned",
            "scope": ["FILL_ME"], "languages": ["FILL_ME"], "exclusions": [],
        },
        "files": [],
        "stages": {
            name: empty_graph("not_computed", "Analysis has not started.")
            for name in STAGES
        },
        "diagrams": {key: empty_graph() for key in TITLES},
        "limitations": ["Unfilled analysis template; not a completed analysis."],
    }


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", required=True)
    parser.parse_args()
    write_json(ROOT / "schemas/analysis.schema.json", schema())
    write_json(ROOT / "assets/diagram-catalog.json", catalog())
