#!/usr/bin/env python3
"""Render a diagram document to a standalone, explorable HTML artifact.

    render_diagram.py diagram.json -o out.html
    render_diagram.py diagram.json --svg -o out.svg
    render_diagram.py diagram.json --check          # validate only, write nothing
    render_diagram.py --self-test                   # prove the checks can fail

The output is one HTML file with the SVG, CSS and JavaScript inlined. It has no
dependencies, makes no network requests, and opens from a file:// path. That is
the whole point: a diagram committed next to the code it describes should still
open years later, on a machine with no toolchain, behind an air gap.

Requires Python 3.9+ and nothing else. A skill that an agent drops into an
arbitrary repository cannot assume it may install packages.

Exit codes
    0  rendered, or validation passed under --check
    1  the document is invalid, or a self-test found a gate that cannot fail
    2  usage or environment error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"

sys.path.insert(0, str(HERE))
import diagram_ir  # noqa: E402
import diagram_layout  # noqa: E402

KIND_LABELS = {
    "architecture": "Architecture",
    "workflow": "Workflow",
    "dataflow": "Data flow",
    "lifecycle": "Lifecycle",
    "sequence": "Sequence",
}


def die(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def e(text):
    """Escape text for XML content."""
    return escape("" if text is None else str(text))


# ------------------------------------------------------------------- shapes
def shape_markup(node):
    """The outline for a node. Shapes carry meaning, so they are worth having:
    a queue reads differently from a datastore at a glance."""
    x, y, w, h = node["x"], node["y"], node["w"], node["h"]
    shape = node["shape"]
    if shape == "round":
        return f'<rect class="shape" x="{x}" y="{y}" width="{w}" height="{h}" rx="{min(h / 2, 26)}"/>'
    if shape == "cylinder":
        r = 9
        d = (
            f"M {x} {y + r} A {w / 2} {r} 0 0 0 {x + w} {y + r} "
            f"L {x + w} {y + h - r} A {w / 2} {r} 0 0 1 {x} {y + h - r} Z"
        )
        return (
            f'<path class="shape" d="{d}"/>'
            f'<path class="shape" fill="none" d="M {x} {y + r} A {w / 2} {r} 0 0 1 {x + w} {y + r}"/>'
        )
    if shape == "queue":
        return (
            f'<rect class="shape" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>'
            f'<path class="shape" fill="none" d="M {x + w - 16} {y} L {x + w - 16} {y + h}"/>'
        )
    if shape == "cloud":
        d = (
            f"M {x + 26} {y + h - 8} a 26 26 0 0 1 -2 -50 a 30 30 0 0 1 56 -10 "
            f"a 26 26 0 0 1 {w - 96} 12 a 24 24 0 0 1 -6 48 Z"
        )
        return f'<path class="shape" d="{d}"/>'
    if shape == "decision":
        cx, cy = x + w / 2, y + h / 2
        d = f"M {cx} {y} L {x + w} {cy} L {cx} {y + h} L {x} {cy} Z"
        return f'<path class="shape" d="{d}"/>'
    if shape == "actor":
        cx = x + w / 2
        head = diagram_layout.ACTOR_HEAD
        return (
            f'<ellipse class="shape" cx="{cx}" cy="{y + 15}" rx="14" ry="14"/>'
            f'<rect class="shape" x="{x}" y="{y + head}" width="{w}" height="{h - head}" rx="10"/>'
        )
    return f'<rect class="shape" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>'


def node_markup(node):
    cx = node["x"] + node["w"] / 2
    y = node["y"] + 26
    if node["shape"] == "actor":
        y += diagram_layout.ACTOR_HEAD
    parts = [shape_markup(node)]

    for line in node["label_lines"]:
        parts.append(
            f'<text class="label" x="{cx}" y="{y}" text-anchor="middle">{e(line)}</text>'
        )
        y += diagram_layout.LINE_H
    if node["note_lines"]:
        y += 4
        for line in node["note_lines"]:
            parts.append(
                f'<text class="note" x="{cx}" y="{y}" text-anchor="middle">{e(line)}</text>'
            )
            y += diagram_layout.NOTE_LINE_H
    if node.get("tech"):
        parts.append(
            f'<text class="tech" x="{cx}" y="{node["y"] + node["h"] - 12}" '
            f'text-anchor="middle">{e(node["tech"])}</text>'
        )

    search = " ".join(
        [node["id"], " ".join(node["label_lines"]), " ".join(node["note_lines"]), node.get("tech") or ""]
    )
    aria = " ".join(node["label_lines"])
    cls = "node accent" if node.get("accent") else "node"
    return (
        f'<g class="{cls}" data-id={quoteattr(node["id"])} data-search={quoteattr(search)} '
        f'tabindex="0" role="button" aria-label={quoteattr(aria)}>'
        + "".join(parts)
        + "</g>"
    )


def edge_markup(edge):
    cls = "edge " + edge["style"] + (" accent" if edge.get("accent") else "")
    out = [
        f'<g class="{cls.strip()}" data-from={quoteattr(edge["from"])} data-to={quoteattr(edge["to"])}>',
        f'<path d="{edge["path"]}" marker-end="url(#arrow)"/>',
    ]
    if edge.get("label"):
        out.append(f'<text x="{edge["lx"]}" y="{edge["ly"]}">{e(edge["label"])}</text>')
    out.append("</g>")
    return "".join(out)


def group_markup(group):
    return (
        f'<g class="group">'
        f'<rect x="{group["x"]}" y="{group["y"]}" width="{group["w"]}" height="{group["h"]}" rx="14"/>'
        f'<text class="glabel" x="{group["x"] + 16}" y="{group["y"] + 20}">{e(group["label"])}</text>'
        f"</g>"
    )


# ------------------------------------------------------------------ sequence
def sequence_markup(geo):
    out = []
    for lane in geo["lanes"]:
        out.append(
            f'<line class="lifeline" x1="{lane["cx"]}" y1="{geo["lifeline_top"]}" '
            f'x2="{lane["cx"]}" y2="{geo["lifeline_bottom"]}"/>'
        )
    for lane in geo["lanes"]:
        node = {
            "x": lane["x"],
            "y": diagram_layout.SEQ_TOP,
            "w": lane["w"],
            "h": lane["h"],
            "shape": lane["shape"],
            "label_lines": lane["label_lines"],
            "note_lines": [],
            "tech": None,
            "id": lane["id"],
            "accent": None,
        }
        out.append(node_markup(node))

    for msg in geo["messages"]:
        cls = "msg " + msg["style"] + (" accent" if msg.get("accent") else "")
        out.append(
            f'<g class="{cls.strip()}" data-from={quoteattr(msg["from"])} '
            f'data-to={quoteattr(msg["to"])}>'
        )
        y = msg["y"]
        if msg["self"]:
            x = msg["x1"]
            d = f"M {x} {y} C {x + 70} {y + 6} {x + 70} {y + 44} {x + 5} {y + 44}"
            out.append(f'<path d="{d}" marker-end="url(#arrow)"/>')
            if msg.get("label"):
                out.append(
                    f'<text x="{x + 82}" y="{y + 28}" text-anchor="start">{e(msg["label"])}</text>'
                )
        else:
            out.append(
                f'<line x1="{msg["x1"]}" y1="{y}" x2="{msg["x2"]}" y2="{y}" '
                f'marker-end="url(#arrow)"/>'
            )
            if msg.get("label"):
                mid = (msg["x1"] + msg["x2"]) / 2
                out.append(
                    f'<text x="{mid}" y="{y - 9}" text-anchor="middle">{e(msg["label"])}</text>'
                )
        out.append(
            f'<text class="num" x="{min(msg["x1"], msg["x2"]) - 26}" y="{y + 4}">'
            f'{msg["index"]:02d}</text>'
        )
        if msg.get("note"):
            out.append(
                f'<text class="msgnote" x="{(msg["x1"] + msg["x2"]) / 2}" y="{y + 20}" '
                f'text-anchor="middle">{e(msg["note"])}</text>'
            )
        out.append("</g>")
    return out


# -------------------------------------------------------------------- render
def build_body(geo):
    if geo["kind"] == "sequence":
        return "\n          ".join(sequence_markup(geo))
    parts = [group_markup(g) for g in geo["groups"]]
    parts += [edge_markup(x) for x in geo["edges"]]
    parts += [node_markup(n) for n in geo["nodes"]]
    return "\n          ".join(parts)


def build_legend(doc, geo):
    """A legend only when it says something the reader cannot infer."""
    items = []
    if geo["kind"] != "sequence":
        if any(x["back"] for x in geo["edges"]):
            items.append('<span><i class="dashed"></i>loop or return path</span>')
        if any(x["style"] == "dashed" and not x["back"] for x in geo["edges"]):
            items.append('<span><i class="dashed"></i>asynchronous</span>')
        if geo["groups"]:
            items.append(f"<span>{len(geo['groups'])} boundaries</span>")
    for entry in doc.get("legend", []) or []:
        items.append(f"<span>{e(entry)}</span>")
    return "".join(items)


def stat_line(geo):
    if geo["kind"] == "sequence":
        return f"{len(geo['lanes'])} participants, {len(geo['messages'])} messages"
    return f"{len(geo['nodes'])} nodes, {len(geo['edges'])} edges"


def a11y_description(doc, geo):
    """SVG needs a text alternative. Describe the structure, not the picture."""
    if geo["kind"] == "sequence":
        lines = [f"Sequence diagram: {doc['title']}."]
        for msg in geo["messages"]:
            label = msg.get("label") or "message"
            lines.append(f"{msg['index']}. {msg['from']} to {msg['to']}: {label}.")
        return " ".join(lines)
    lines = [f"{KIND_LABELS.get(geo['kind'], geo['kind'])} diagram: {doc['title']}."]
    lines.append(f"{len(geo['nodes'])} nodes.")
    for edge in geo["edges"]:
        label = edge.get("label")
        lines.append(f"{edge['from']} to {edge['to']}{': ' + label if label else ''}.")
    return " ".join(lines)


def render_html(doc, geo):
    template = (TEMPLATES / "viewer.html").read_text(encoding="utf-8")
    css = (TEMPLATES / "theme.css").read_text(encoding="utf-8")

    subtitle = doc.get("subtitle") or ""
    replacements = {
        "__TITLE__": e(doc["title"]),
        "__SUBTITLE__": e(subtitle),
        "__DESCRIPTION__": e(subtitle or doc["title"]),
        "__KIND__": e(KIND_LABELS.get(doc["kind"], doc["kind"])),
        "__CSS__": css,
        "__BODY__": build_body(geo),
        "__LEGEND__": build_legend(doc, geo),
        "__STAT__": e(stat_line(geo)),
        "__A11Y_DESC__": e(a11y_description(doc, geo)),
        "__MIN_X__": str(geo["min_x"]),
        "__MIN_Y__": str(geo["min_y"]),
        "__WIDTH__": str(geo["width"]),
        "__HEIGHT__": str(geo["height"]),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)

    leftover = [t for t in replacements if t in template]
    if leftover:
        die(f"template still contains unsubstituted tokens: {', '.join(leftover)}", 1)
    return template


def render_svg(doc, geo):
    css = (TEMPLATES / "theme.css").read_text(encoding="utf-8")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{geo["min_x"]} {geo["min_y"]} {geo["width"]} {geo["height"]}" '
        f'width="{geo["width"]}" height="{geo["height"]}" data-theme="dark" '
        f'role="img" aria-label={quoteattr(a11y_description(doc, geo))}>'
        f"<style>{css}\nsvg{{background:var(--bg)}}</style>"
        f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs>'
        f'<g data-theme="dark">{build_body(geo)}</g></svg>'
    )


def load(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        die(f"cannot read {path}: {exc}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"{path} is not valid JSON: line {exc.lineno} column {exc.colno}: {exc.msg}", 1)


# ----------------------------------------------------------------- self test
SELF_TEST_CASES = [
    ("edge to a node that does not exist", {
        "kind": "architecture", "title": "t",
        "nodes": [{"id": "a", "label": "A"}],
        "edges": [{"from": "a", "to": "ghost"}],
    }),
    ("unknown top-level key", {
        "kind": "architecture", "title": "t", "colour": "red",
        "nodes": [{"id": "a", "label": "A"}],
    }),
    ("duplicate node id", {
        "kind": "architecture", "title": "t",
        "nodes": [{"id": "a", "label": "A"}, {"id": "a", "label": "B"}],
    }),
    ("unknown shape", {
        "kind": "architecture", "title": "t",
        "nodes": [{"id": "a", "label": "A", "shape": "hexagon"}],
    }),
    ("node in two groups", {
        "kind": "architecture", "title": "t",
        "nodes": [{"id": "a", "label": "A"}],
        "groups": [{"label": "one", "nodes": ["a"]}, {"label": "two", "nodes": ["a"]}],
    }),
    ("missing title", {
        "kind": "architecture",
        "nodes": [{"id": "a", "label": "A"}],
    }),
    ("unknown kind", {"kind": "gantt", "title": "t"}),
    ("sequence message to unknown participant", {
        "kind": "sequence", "title": "t",
        "participants": [{"id": "a", "label": "A"}],
        "messages": [{"from": "a", "to": "b"}],
    }),
]


def self_test():
    """Prove the validator rejects what it claims to reject.

    A validator that never fires is indistinguishable from no validator, and that
    is a failure mode worth testing for directly rather than assuming away.
    """
    failures = []
    for name, doc in SELF_TEST_CASES:
        try:
            diagram_ir.validate(doc)
        except diagram_ir.ValidationError:
            print(f"  ok    rejected: {name}")
        else:
            failures.append(name)
            print(f"  FAIL  accepted invalid document: {name}")

    valid = {
        "kind": "architecture",
        "title": "Self test",
        "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
        "edges": [{"from": "a", "to": "b"}],
    }
    try:
        geo = diagram_layout.layout(diagram_ir.validate(valid))
        html = render_html(valid, geo)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"a valid document failed to render: {exc}")
        print(f"  FAIL  a valid document failed to render: {exc}")
    else:
        if "<article" in html or len(html) < 2000:
            failures.append("rendered output looks wrong")
        else:
            print("  ok    a valid document renders")

    if failures:
        print(f"\nself-test FAILED: {len(failures)} problem(s)", file=sys.stderr)
        return 1
    print(f"\nself-test passed: {len(SELF_TEST_CASES)} invalid documents rejected, valid one rendered")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(
        description="Render a diagram document to standalone HTML.",
        epilog="See references/authoring-contract.md for the document format.",
    )
    ap.add_argument("input", nargs="?", help="path to the diagram JSON document")
    ap.add_argument("-o", "--out", help="output path (default: alongside the input)")
    ap.add_argument("--svg", action="store_true", help="emit a bare SVG instead of HTML")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--self-test", action="store_true", help="prove the validator can fail")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.input:
        ap.print_usage(sys.stderr)
        die("an input document is required")

    doc = load(args.input)
    try:
        diagram_ir.validate(doc)
    except diagram_ir.ValidationError as exc:
        print(f"error: {args.input} is not a valid diagram document.\n{exc}", file=sys.stderr)
        return 1

    if args.check:
        kind = doc["kind"]
        count = len(doc.get("nodes") or doc.get("participants") or [])
        print(f"valid: {args.input} ({kind}, {count} nodes/participants)")
        return 0

    geo = diagram_layout.layout(doc)
    body = render_svg(doc, geo) if args.svg else render_html(doc, geo)
    out = Path(args.out) if args.out else Path(args.input).with_suffix(".svg" if args.svg else ".html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"wrote {out} ({len(body):,} bytes, {stat_line(geo)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
