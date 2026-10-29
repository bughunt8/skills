#!/usr/bin/env python3
"""Validate and export an agent-authored model; never execute analysed code."""

import argparse
import fnmatch
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

from contract import ROOT, STAGES, TITLES, STAGE_NODE_KINDS, STAGE_EDGE_KINDS, catalog, empty_model, schema, write_json

MAX_MODEL_BYTES = 10 * 1024 * 1024
MAX_SOURCE_BYTES = 5 * 1024 * 1024
VERSION = "1.0.0"
FORMAT_LOSSES = [
    "Normalized JSON is not binary SCPG and not OpenHeart GraphIR.",
    "Only class, sequence and state use native diagram notation.",
    "Other views are labelled graph approximations, not full UML notation.",
    "Parents, fragments, ports, timing and full member flags remain in JSON.",
    "ACT is a provisional alias for activity, not an upstream artifact.",
    "XMI is class-identity-only; members, relationships and other views are unsupported.",
    "Source-consistency validation does not prove semantic correctness.",
    "Renderer syntax and UML/XMI interoperability are not validated by this exporter.",
]


class Invalid(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise Invalid(message)


def check_schema(value, spec, root, path="$"):
    """Evaluate exactly the JSON Schema keywords used by the bundled contract."""
    if "$ref" in spec:
        name = spec["$ref"].removeprefix("#/$defs/")
        return check_schema(value, root["$defs"][name], root, path)
    if "const" in spec:
        require(value == spec["const"], f"{path}: wrong constant")
    if "enum" in spec:
        require(value in spec["enum"], f"{path}: invalid enum value")
    checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: type(v) is int,
        "boolean": lambda v: type(v) is bool,
        "null": lambda v: v is None,
    }
    types = spec.get("type")
    if types:
        types = types if isinstance(types, list) else [types]
        require(any(checks[t](value) for t in types), f"{path}: wrong type, expected {types}")
    if isinstance(value, dict):
        for key in spec.get("required", []):
            require(key in value, f"{path}: missing {key}")
        props = spec.get("properties", {})
        if spec.get("additionalProperties") is False:
            require(not set(value) - set(props), f"{path}: unexpected fields {set(value) - set(props)}")
        for key, val in value.items():
            if key in props:
                check_schema(val, props[key], root, path + "." + key)
    elif isinstance(value, list):
        require(len(value) >= spec.get("minItems", 0), f"{path}: too few items")
        for i, val in enumerate(value):
            check_schema(val, spec["items"], root, f"{path}[{i}]")
    elif isinstance(value, str):
        require(len(value) >= spec.get("minLength", 0), f"{path}: string too short")
        if "pattern" in spec:
            require(re.fullmatch(spec["pattern"], value) is not None, f"{path}: pattern mismatch")
    elif type(value) is int:
        require(value >= spec.get("minimum", value), f"{path}: below minimum")


def safe_relative(path):
    require("\\" not in path and not any(ord(c) < 32 for c in path), "Invalid source path")
    p = PurePosixPath(path)
    require(bool(p.parts) and not p.is_absolute() and path == p.as_posix()
            and all(x not in {"", ".", ".."} for x in p.parts),
            f"Unsafe or noncanonical source path: {path}")
    if os.name == "nt":
        reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{s}{i}" for s in ("COM", "LPT") for i in range(1, 10)}
        require(":" not in path and all(part.split(".")[0].upper() not in reserved for part in p.parts),
                "Windows device or alternate data stream path refused")
    return p


def source_lines(text):
    """Editor lines: CRLF/CR become LF; other Unicode separators stay literal."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        return []
    result = text.split("\n")
    return result[:-1] if result[-1] == "" else result


def in_scope(path, selectors):
    return any(selector == "." or path == selector or path.startswith(selector.rstrip("/") + "/")
               or fnmatch.fnmatchcase(path, selector) for selector in selectors)


def source_file(root, path):
    rel = safe_relative(path)
    current = root
    for part in rel.parts:
        current = current / part
        require(not current.is_symlink(), f"Source symlink refused: {path}")
    require(current.resolve().is_relative_to(root), f"Source escapes root: {path}")
    require(current.is_file(), f"Missing source file: {path}")
    require(current.stat().st_size <= MAX_SOURCE_BYTES, f"Source exceeds byte budget: {path}")
    return current


def validate(model, source_root=None):
    def portable_json(value):
        if isinstance(value, dict):
            for key, item in value.items():
                portable_json(key)
                portable_json(item)
        elif isinstance(value, list):
            for item in value:
                portable_json(item)
        elif isinstance(value, float):
            require(math.isfinite(value), "Non-finite JSON number")
        elif isinstance(value, str):
            require(not any(0xD800 <= ord(c) <= 0xDFFF for c in value), "Unpaired Unicode surrogate")
    portable_json(model)
    contract = schema()
    check_schema(model, contract, contract)
    require(model["source"]["repository"] != "FILL_ME", "Unfilled repository")
    require("FILL_ME" not in model["source"]["scope"], "Unfilled scope")
    require("FILL_ME" not in model["source"]["languages"], "Unfilled languages")
    require(bool(model["files"]), "No included source files")
    files = {f["path"]: f for f in model["files"]}
    require(len(files) == len(model["files"]), "Duplicate source paths")
    texts = {}
    root = Path(source_root).resolve() if source_root is not None else None
    if root:
        require(root.is_dir(), "Source root is not a directory")
    for path, record in files.items():
        safe_relative(path)
        require(in_scope(path, model["source"]["scope"]), f"File outside declared scope: {path}")
        require(not in_scope(path, model["source"]["exclusions"]), f"Included file is excluded: {path}")
        if root:
            data = source_file(root, path).read_bytes()
            require(hashlib.sha256(data).hexdigest() == record["sha256"], f"Stale source hash: {path}")
            text = data.decode("utf-8")
            require(len(source_lines(text)) == record["line_count"], f"Wrong line count: {path}")
            texts[path] = source_lines(text)

    def evidence(entries):
        for ev in entries:
            require(bool(ev["excerpt"].strip()), "Evidence excerpt is whitespace-only")
            require(ev["file"] in files, f"Evidence refers to unlisted file: {ev['file']}")
            require(ev["line_start"] <= ev["line_end"] <= files[ev["file"]]["line_count"],
                    f"Invalid evidence range: {ev}")
            if root:
                lines = texts[ev["file"]][ev["line_start"] - 1:ev["line_end"]]
                require(ev["excerpt"] in "\n".join(lines), f"Excerpt not in source range: {ev}")

    identities = {}
    stage_ids = set()
    for group in ("stages", "diagrams"):
        for name, graph in model[group].items():
            nodes = {n["id"]: n for n in graph["nodes"]}
            edges = {e["id"]: e for e in graph["edges"]}
            require(len(nodes) == len(graph["nodes"]), f"{name}: duplicate node IDs")
            require(len(edges) == len(graph["edges"]), f"{name}: duplicate edge IDs")
            require(not set(nodes) & set(edges), f"{name}: node/edge ID collision")
            status = graph["status"]
            if status != "complete":
                require(bool(graph["reason"].strip()), f"{name}: incomplete status needs reason")
            else:
                require(bool(nodes), f"{name}: empty graph cannot be complete")
            if status in {"insufficient_evidence", "not_computed", "not_requested"}:
                require(not nodes and not edges, f"{name}: inactive status cannot carry facts")
            if group == "stages":
                require(not stage_ids & (set(nodes) | set(edges)), "IDs reused across stages")
                stage_ids.update(nodes)
                stage_ids.update(edges)
                require(all(n["kind"] in STAGE_NODE_KINDS[name] for n in graph["nodes"]),
                        f"{name}: invalid stage node kind")
                require(all(e["kind"] in STAGE_EDGE_KINDS[name] for e in graph["edges"]),
                        f"{name}: invalid stage edge kind")
            if graph["nodes"]:
                require(graph["method"].strip().lower() not in {"not run", "unknown", "fill_me", "todo", ""},
                        f"{name}: populated graph requires an actual method")
            done = set()
            for start in nodes:
                cursor, visited = start, set()
                while cursor is not None and cursor not in done:
                    require(cursor in nodes, f"{name}: dangling parent")
                    require(cursor not in visited, f"{name}: parent cycle")
                    visited.add(cursor)
                    cursor = nodes[cursor]["parent"]
                done.update(visited)
            for node in graph["nodes"]:
                evidence(node["evidence"])
                identity = ("node", json.dumps(node, sort_keys=True, ensure_ascii=True))
                if node["id"] in identities:
                    require(identities[node["id"]] == identity, f"Inconsistent reused ID: {node['id']}")
                identities[node["id"]] = identity
                if node["basis"] == "inferred":
                    require(status == "partial", f"{name}: inferred node requires partial status")
                if node["kind"] == "ast":
                    require(isinstance(node["attributes"].get("node_type"), str)
                            and node["attributes"]["node_type"].strip(), f"{name}: AST needs node_type")
                if node["kind"] == "callsite":
                    require(node["attributes"].get("resolution") in {"resolved", "candidate", "unresolved"},
                            f"{name}: callsite needs resolution")
                if node["kind"] == "bdd":
                    attrs = node["attributes"]
                    require(attrs.get("low") in nodes and attrs.get("high") in nodes
                            and attrs["low"] != attrs["high"], f"{name}: invalid or unreduced BDD children")
                    require(isinstance(attrs.get("variable"), str) and attrs["variable"].strip(),
                            f"{name}: BDD needs variable")
                if node["kind"] == "terminal":
                    require(type(node["attributes"].get("value")) is bool, f"{name}: terminal needs Boolean value")
            for edge in graph["edges"]:
                require(edge["source"] in nodes and edge["target"] in nodes, f"{name}: dangling endpoint")
                evidence(edge["evidence"])
                identity = ("edge", json.dumps(edge, sort_keys=True, ensure_ascii=True))
                if edge["id"] in identities:
                    require(identities[edge["id"]] == identity, f"Inconsistent reused ID: {edge['id']}")
                identities[edge["id"]] = identity
                if edge["basis"] == "inferred":
                    require(status == "partial", f"{name}: inferred edge requires partial status")
            for record in graph["nodes"] + graph["edges"]:
                if record["basis"] == "observed":
                    require(any(files[e["file"]]["role"] in {"trace", "snapshot"} for e in record["evidence"]),
                            f"{name}: observed fact needs trace/snapshot evidence")
                if record["basis"] == "derived":
                    require(isinstance(record["attributes"].get("derivation"), str)
                            and record["attributes"]["derivation"].strip(),
                            f"{name}: derived record needs derivation")
                if "ordinal" in record["attributes"]:
                    require(type(record["attributes"]["ordinal"]) is int
                            and record["attributes"]["ordinal"] > 0, f"{name}: invalid ordinal")
            if name in {"sequence", "communication"} and group == "diagrams":
                ordinals = [e["attributes"].get("ordinal") for e in graph["edges"]]
                require(all(type(x) is int and x > 0 for x in ordinals)
                        and len(set(ordinals)) == len(ordinals),
                        "Scenario messages require unique positive integer ordinals")
    return {
        "schema": "pass", "cross_references": "pass",
        "source_consistency": "pass" if root else "not_run",
        "semantic_accuracy": "not_validated", "renderer_syntax": "not_run",
        "revision_consistency": "not_validated",
    }


def literal(value):
    """Plain display labels only; original labels remain unmodified in JSON."""
    text = str(value)
    return re.sub(r"\s+", " ", "".join(
        c if c.isalnum() or c in " _.:/,+?=!-()" else " " for c in text
    )).strip() or "unnamed"


def ordered(graph):
    nodes = sorted(graph["nodes"], key=lambda n: n["id"])
    edges = sorted(graph["edges"], key=lambda e: (e["attributes"].get("ordinal", 0), e["id"]))
    return nodes, edges, {n["id"]: "n" + str(i) for i, n in enumerate(nodes)}


def mermaid(key, graph):
    nodes, edges, ids = ordered(graph)
    note = literal(graph["status"] + ": " + graph["reason"])
    if not nodes:
        return f'flowchart TD\n    status["{note}"]\n'
    lines = ["%% " + note]
    if key == "class":
        lines.append("classDiagram")
        for node in nodes:
            nid = ids[node["id"]]
            lines.append(f'    class {nid}["{literal(node["label"])}"] {{')
            for members, suffix in ((node["fields"], ""), (node["methods"], "()")):
                for member in members:
                    text = literal(member["name"]) + suffix
                    if member["type_name"].strip():
                        text += " " + literal(member["type_name"])
                    lines.append("        " + member["visibility"] + text)
            lines.append("    }")
        arrows = {"extends": "--|>", "generalization": "--|>",
                  "implements": "..|>", "realization": "..|>",
                  "composition": "*--", "aggregation": "o--", "dependency": "..>", "type_use": "..>"}
        for edge in edges:
            arrow = arrows.get(edge["kind"], "-->")
            lines.append(f'    {ids[edge["source"]]} {arrow} {ids[edge["target"]]} : {literal(edge["label"] or edge["kind"])}')
    elif key == "sequence":
        lines.append("sequenceDiagram")
        for node in nodes:
            lines.append(f'    participant {ids[node["id"]]} as {literal(node["label"])}')
        for edge in edges:
            lines.append(f'    {ids[edge["source"]]}->>{ids[edge["target"]]}: {edge["attributes"]["ordinal"]}. {literal(edge["label"] or edge["kind"])}')
    elif key == "statemachine":
        lines.append("stateDiagram-v2")
        for node in nodes:
            lines.append(f'    state "{literal(node["label"])}" as {ids[node["id"]]}')
        for edge in edges:
            lines.append(f'    {ids[edge["source"]]} --> {ids[edge["target"]]} : {literal(edge["label"] or edge["kind"])}')
    else:
        lines.append("flowchart TD")
        for node in nodes:
            lines.append(f'    {ids[node["id"]]}["{literal(node["kind"])}: {literal(node["label"])}"]')
        for edge in edges:
            prefix = str(edge["attributes"]["ordinal"]) + ". " if key == "communication" else ""
            lines.append(f'    {ids[edge["source"]]} -->|"{prefix}{literal(edge["label"] or edge["kind"])}"| {ids[edge["target"]]}')
    return "\n".join(lines) + "\n"


def plantuml(key, graph):
    nodes, edges, ids = ordered(graph)
    lines = ["@startuml", "' " + literal(graph["status"] + ": " + graph["reason"])]
    if not nodes:
        lines.append(f'rectangle "{literal(graph["status"] + ": " + graph["reason"])}" as status')
    elif key == "class":
        for node in nodes:
            nid = ids[node["id"]]
            lines.append(f'class "{literal(node["label"])}" as {nid} {{')
            for members, suffix in ((node["fields"], ""), (node["methods"], "()")):
                for member in members:
                    text = "    " + member["visibility"] + literal(member["name"]) + suffix
                    if member["type_name"].strip():
                        text += " : " + literal(member["type_name"])
                    lines.append(text)
            lines.append("}")
    else:
        kind = {"sequence": "participant", "statemachine": "state"}.get(key, "rectangle")
        for node in nodes:
            lines.append(f'{kind} "{literal(node["label"])}" as {ids[node["id"]]}')
    arrows = {"extends": "--|>", "generalization": "--|>",
              "implements": "..|>", "realization": "..|>",
              "composition": "*--", "aggregation": "o--", "dependency": "..>", "type_use": "..>"}
    for edge in edges:
        arrow = arrows.get(edge["kind"], "-->") if key == "class" else "->"
        prefix = str(edge["attributes"]["ordinal"]) + ". " if key in {"sequence", "communication"} else ""
        lines.append(f'{ids[edge["source"]]} {arrow} {ids[edge["target"]]} : {prefix}{literal(edge["label"] or edge["kind"])}')
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def traceability(model):
    by_entity, by_file = {}, {}
    for group in ("stages", "diagrams"):
        for key, graph in model[group].items():
            for item in graph["nodes"] + graph["edges"]:
                entry = by_entity.setdefault(item["id"], {
                    "basis": item["basis"], "attributes": item["attributes"],
                    "evidence": item["evidence"], "views": [],
                })
                entry["views"].append(group + "/" + key)
                for ev in item["evidence"]:
                    by_file.setdefault(ev["file"], set()).add(item["id"])
    return {"by_entity": by_entity, "by_file": {p: sorted(ids) for p, ids in by_file.items()}}


def class_xmi(graph):
    xmi = "http://www.omg.org/spec/XMI/20131001"
    uml = "http://www.eclipse.org/uml2/5.0.0/UML"
    ET.register_namespace("xmi", xmi)
    ET.register_namespace("uml", uml)
    root = ET.Element(f"{{{uml}}}Model", {
        f"{{{xmi}}}version": "2.5", f"{{{xmi}}}id": "model",
        "name": "Identity-only class export",
    })
    for i, node in enumerate(sorted(graph["nodes"], key=lambda n: n["id"])):
        if node["kind"] not in {"class", "interface"}:
            continue
        ET.SubElement(root, "packagedElement", {
            f"{{{xmi}}}type": "uml:Interface" if node["kind"] == "interface" else "uml:Class",
            f"{{{xmi}}}id": f"n{i}", "name": "".join(c for c in node["label"] if
                c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD
                or 0x10000 <= ord(c) <= 0x10FFFF),
        })
    return ET.tostring(root, encoding="unicode", xml_declaration=True) + "\n"


def make_destination(path):
    dest = Path(path)
    require(not dest.exists() and not dest.is_symlink(), "Output destination must not exist")
    require(dest.parent.exists() and dest.parent.is_dir(), "Output parent must exist")
    dest.mkdir()
    return dest


def templates(dest, checks=None, model_hash=None):
    for name in ("REPORT.md", "VALIDATION.md"):
        shutil.copyfile(ROOT / "templates" / (name + ".tmpl"), dest / name)
    if checks:
        path = dest / "VALIDATION.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace("FILL_ME", f"Model canonical SHA-256: {model_hash}. Exporter {VERSION}.", 1)
        for label, result in (("Schema and cross-references", checks["schema"]),
                              ("File hashes, ranges and excerpts", checks["source_consistency"])):
            text = text.replace(
                f"| {label} | FILL_ME | NOT RUN | FILL_ME |",
                f"| {label} | Internal validate() in exporter {VERSION} | {result} | report.json |")
        path.write_text(text, encoding="utf-8")


def export(model, dest, checks):
    model_hash = hashlib.sha256(json.dumps(model, sort_keys=True, separators=(",", ":"),
                                          ensure_ascii=True).encode()).hexdigest()
    write_json(dest / "analysis.json", model)
    write_json(dest / "traceability.json", traceability(model))
    statuses = {}
    for key, graph in model["diagrams"].items():
        statuses[key] = {k: graph[k] for k in ("status", "reason", "method")}
        if graph["status"] == "not_requested":
            continue
        write_json(dest / "diagrams" / (key + ".json"), graph)
        for extension, content in (("mmd", mermaid(key, graph)), ("puml", plantuml(key, graph))):
            (dest / "diagrams" / (key + "." + extension)).write_text(content, encoding="utf-8")
        if key == "activity":
            for extension in ("json", "mmd", "puml"):
                shutil.copyfile(dest / "diagrams" / ("activity." + extension),
                                dest / "diagrams" / ("ACT." + extension))
        if key == "class" and any(n["kind"] in {"class", "interface"} for n in graph["nodes"]):
            (dest / "diagrams/class.xmi").write_text(class_xmi(graph), encoding="utf-8")
    write_json(dest / "report.json", {
        "source": model["source"], "validation": checks,
        "model_sha256": model_hash,
        "tool": {"name": "openheart-analysis", "version": VERSION,
                 "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "files_in_scope": len(model["files"]),
        "source_lines_in_scope": sum(f["line_count"] for f in model["files"]),
        "stages": {k: {"status": g["status"], "reason": g["reason"],
                       "method": g["method"], "nodes": len(g["nodes"]), "edges": len(g["edges"])}
                   for k, g in model["stages"].items()},
        "diagrams": statuses, "limitations": model["limitations"],
        "format_losses": FORMAT_LOSSES,
    })
    templates(dest, checks, model_hash)


def atomic_output(path, writer):
    dest = Path(path)
    require(not dest.exists() and not dest.is_symlink(), "Output destination must not exist")
    require(dest.parent.is_dir(), "Output parent must exist")
    temp = Path(tempfile.mkdtemp(prefix=".openheart-", dir=dest.parent))
    try:
        writer(temp)
        require(not dest.exists() and not dest.is_symlink(), "Output destination appeared during export")
        temp.rename(dest)
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def load_model(path):
    path = Path(path)
    require(path.stat().st_size <= MAX_MODEL_BYTES, "Model exceeds byte budget")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def invalid_constant(value):
        raise Invalid("Non-finite JSON number: " + value)
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=invalid_constant)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "contracts"):
        cmd = subs.add_parser(name)
        cmd.add_argument("--out", required=True)
    for name in ("validate", "export"):
        cmd = subs.add_parser(name)
        cmd.add_argument("model")
        cmd.add_argument("--source-root", required=name == "export")
        if name == "export":
            cmd.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in {"init", "contracts"}:
            dest = make_destination(args.out)
            if args.command == "init":
                write_json(dest / "analysis.json", empty_model())
                templates(dest)
            else:
                write_json(dest / "analysis.schema.json", schema())
                write_json(dest / "diagram-catalog.json", catalog())
        else:
            model = load_model(args.model)
            checks = validate(model, args.source_root)
            if args.command == "export":
                atomic_output(args.out, lambda dest: export(model, dest, checks))
            print(json.dumps(checks, indent=2))
        return 0
    except Exception as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
