#!/usr/bin/env python3
"""Reproduce renderer receipts; exit 2 when UML import evidence remains open.

Run with Python 3.10+ and Docker. No provider, credential or model invocation.
The output directory must be absent. --receipt also saves the receipt at a
caller-selected path, for committing a qualification run.
"""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

import openheart
from build_fixture import edge, evidence, graph
from contract import ROOT, write_json


FIXTURES = ROOT / "datasets/qualification-cases.json"


def command(argv, timeout=60):
    """Keep the exact attempted command and diagnostics, including timeouts."""
    try:
        result = subprocess.run(argv, capture_output=True, timeout=timeout)
        return {"argv": argv, "command": shlex.join(argv), "exit_code": result.returncode,
                "stdout": result.stdout.decode("utf-8", errors="replace"),
                "stderr": result.stderr.decode("utf-8", errors="replace")}
    except subprocess.TimeoutExpired as exc:
        return {"argv": argv, "command": shlex.join(argv), "exit_code": None,
                "stdout": (exc.stdout or b"").decode("utf-8", errors="replace"),
                "stderr": (exc.stderr or b"").decode("utf-8", errors="replace"),
                "error": f"Host command exceeded {timeout} seconds"}
    except OSError as exc:
        return {"argv": argv, "command": shlex.join(argv), "exit_code": None,
                "stdout": "", "stderr": str(exc)}


def renderer(image, paths):
    """Use the same syntax gate for positive exports and the planted defect."""
    parent = paths[0].parent.resolve()
    return command([
        "docker", "run", "--rm", "--network", "none", "--user",
        f"{os.getuid()}:{os.getgid()}", "-e", "PLANTUML_SECURITY_PROFILE=SECURE",
        "-v", f"{parent}:/work", image, "-tsvg", "-failfast2", "-stdrpt:1",
        *["/work/" + p.name for p in paths],
    ])


def make_model(case, fixtures):
    """Mutate committed fixtures only, leaving their source evidence unchanged."""
    java = case == "java-classifiers"
    model = openheart.load_model(ROOT / "datasets" / (
        "observer-java-model.json" if java else "checkout-model.json"))
    source = ROOT / ("references/upstream/source/examples/test_patterns_codebase" if java else "datasets")
    if case == "native-populated":
        classes = copy.deepcopy(model["diagrams"]["class"]["nodes"])
        message = edge("qualification:message", "class:Checkout", "class:Payment", "message",
                       evidence(10, 10, "return payment.charge(amount)"), "candidate charge",
                       basis="inferred", ordinal=1,
                       derivation="Synthetic renderer fixture; receiver resolution is not claimed.")
        model["diagrams"]["sequence"] = graph(classes, [message], "Synthetic renderer fixture, not runtime evidence.")
        model["diagrams"]["statemachine"] = copy.deepcopy(model["diagrams"]["cfg"])
        model["diagrams"]["statemachine"]["reason"] = "Synthetic state notation over branch blocks; not state extraction."
    if case in {"malicious-label", "untyped-member"}:
        for group in ("stages", "diagrams"):
            for view in model[group].values():
                for node in view["nodes"]:
                    if case == "malicious-label":
                        node["label"] = fixtures["malicious_label"]
                    elif node["id"] == "class:Payment":
                        node["fields"] = [copy.deepcopy(fixtures["untyped_member"])]
                        node["methods"] = [copy.deepcopy(fixtures["untyped_member"])]
                if case == "malicious-label":
                    for connection in view["edges"]:
                        connection["label"] = fixtures["malicious_label"]
    if case == "empty-evidence":
        for view in model["diagrams"].values():
            view.update(status="insufficient_evidence", reason="No supported evidence in this renderer fixture.",
                        nodes=[], edges=[], method="not run")
    return model, source


def run(out, fixtures):
    """Export every requested view, render it, then attempt bounded UML imports."""
    out.mkdir()
    render_dir = out / "plantuml"
    render_dir.mkdir()
    receipt = {"images": fixtures["images"], "cases": {}, "render": {}, "imports": {}}
    plantuml = fixtures["images"]["plantuml"]["reference"]
    uml = fixtures["images"]["uml"]["reference"]
    receipt["versions"] = {
        "plantuml": command(["docker", "run", "--rm", "--network", "none", plantuml, "-version"]),
        "uml": command(["docker", "run", "--rm", "--network", "none", "-e",
                        "QT_QPA_PLATFORM=offscreen", uml, "--version"]),
    }
    for case in fixtures["cases"]:
        model, source = make_model(case, fixtures)
        checks = openheart.validate(model, source)
        dest = out / case
        openheart.atomic_output(dest, lambda p: openheart.export(model, p, checks))
        exports = {}
        for path in sorted((dest / "diagrams").glob("*.puml")):
            text = path.read_text(encoding="utf-8")
            # A literal attack must remain text, never a renderer directive.
            if case == "malicious-label":
                openheart.require("\n!include" not in text and "<script>" not in text,
                                  "Malicious label escaped into renderer instructions")
            target = render_dir / f"{case}--{path.name}"
            target.write_text(text, encoding="utf-8")
            exports[path.name] = text
        receipt["cases"][case] = {"validation": checks, "plantuml_exports": exports}
    paths = sorted(render_dir.glob("*.puml"))
    rendered = renderer(plantuml, paths)
    svgs = {}
    for path in paths:
        svg = path.with_suffix(".svg")
        if svg.exists():
            data = svg.read_bytes()
            root = ET.fromstring(data)
            openheart.require(root.tag == "{http://www.w3.org/2000/svg}svg", "Expected SVG")
            svgs[svg.name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    rendered["outputs"] = svgs
    rendered["expected_count"] = len(paths)
    rendered["passed"] = rendered["exit_code"] == 0 and len(svgs) == len(paths)
    receipt["render"] = rendered
    negative = out / "malformed-label.puml"
    negative.write_text(fixtures["malformed_plantuml"], encoding="utf-8")
    rejected = renderer(plantuml, [negative])
    rejected["passed"] = (rejected["exit_code"] == 200
                          and "Some diagram description contains errors" in rejected["stderr"])
    receipt["negative_case"] = rejected
    for case in fixtures["cases"]:
        xmi = out / case / "diagrams/class.xmi"
        if not xmi.exists():
            receipt["imports"][case] = {"status": "not_emitted", "reason": "No classifier identities; exporter emits no XMI."}
            continue
        model, _ = make_model(case, fixtures)
        view = model["diagrams"]["class"]
        imported = command([
            "docker", "run", "--rm", "--network", "none", "-e", "QT_QPA_PLATFORM=offscreen",
            "-v", f"{out.resolve()}:/work", "--entrypoint", "timeout", uml,
            "-k", "2s", "8s", "umbrello", f"/work/{case}/diagrams/class.xmi",
            "--export", "svg", "--directory", f"/work/imported/{case}",
        ], timeout=20)
        imported["diagnostic_lines"] = [line for line in imported["stderr"].splitlines()
                                        if any(token in line for token in (
                                            "Could not", "Couldn't", "Aborting", "Not connected", "couldn't"))]
        # Exit zero or an empty diagram export cannot prove classifier import.
        imported.update(status="open", consumer_reported_omissions=None,
                        reason="No verified classifier inventory or consumer omission report was returned.",
                        input_xmi=xmi.read_text(encoding="utf-8"),
                        input_sha256=hashlib.sha256(xmi.read_bytes()).hexdigest(),
                        exporter_omissions={"fields": sum(len(n["fields"]) for n in view["nodes"]),
                                            "methods": sum(len(n["methods"]) for n in view["nodes"]),
                                            "relationships": len(view["edges"])},
                        expected_omissions=fixtures["expected_xmi_omissions"])
        receipt["imports"][case] = imported
    receipt["open_gates"] = [
        "Native-host model invocation receipt was not produced. No model session was invoked.",
        "Semantic accuracy report over independently selected, commit-pinned Java input remains open.",
        "UML consumer classifier import and consumer-reported omissions remain open for every emitted XMI case.",
        "Mermaid CI receipts belong to todo 15 and are not claimed by this run.",
    ]
    receipt["issue_65_comment"] = (
        "Todo 16 qualification receipts\n\n"
        f"PlantUML image: `{plantuml}`. UML consumer image: `{uml}`.\n\n"
        f"Rendered {len(svgs)}/{len(paths)} PlantUML exports across checkout, populated native class/sequence/state, "
        "approximate graphs, malicious-label, untyped-member, empty-evidence and existing Java classifier cases. "
        f"Renderer exit: {rendered['exit_code']}. Deliberately malformed label exit: {rejected['exit_code']}; "
        f"negative gate passed: {rejected['passed']}.\n\n"
        "Reproduce with `python3 skills/engineering/openheart-analysis/scripts/qualify_consumers.py "
        "--out /tmp/openheart-qualification-new`. Exit 2 explicitly reports the remaining consumer gap. "
        "The committed datasets/qualification-receipts.json records each exact command, stdout, stderr, "
        "exported PlantUML/XMI text, SVG hashes and per-case import gaps.\n\n"
        "Umbrello imports were attempted for checkout, native-populated, malicious-label, untyped-member "
        "and java-classifiers. The container could not produce a verified import or omission report in its "
        "headless KDE/D-Bus environment. Its bounded commands and errors are in the receipts. "
        "Empty-evidence emits no XMI. Local inspection confirms the exporter omits fields, methods, "
        "relationships, other views, layout and source provenance; these are exporter observations, "
        "not consumer-reported omissions.\n\n"
        "Issue 65 remains open. The native-host model invocation receipt, the semantic accuracy report over "
        "independently selected Java input, and all unverified UML consumer imports remain open. "
        "No paid provider, API key or model session was used. Mermaid CI and mobile catalogue performance "
        "are separate gates. Draft PR 66 readiness and acceptance criteria are unchanged."
    )
    receipt["status"] = "render_failed" if not rendered["passed"] or not rejected["passed"] else "consumer_gap"
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--gate", type=Path, help="Gate one raw PlantUML file; preserve renderer failure")
    args = parser.parse_args()
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for image in fixtures["images"].values():
        openheart.require(re.fullmatch(r"[a-z0-9./_-]+@sha256:[0-9a-f]{64}", image["reference"]), "Image must use a digest")
    if args.gate:
        result = renderer(fixtures["images"]["plantuml"]["reference"], [args.gate])
        print(json.dumps(result, indent=2))
        return 0 if result["exit_code"] == 0 else 1
    if args.out is None:
        parser.error("--out is required without --gate")
    openheart.require(not args.out.exists(), "--out must name an absent directory")
    receipt = run(args.out.resolve(), fixtures)
    write_json(args.out / "receipts.json", receipt)
    if args.receipt:
        write_json(args.receipt, receipt)
    print(json.dumps({"status": receipt["status"], "renders": len(receipt["render"]["outputs"]),
                      "negative_exit": receipt["negative_case"]["exit_code"],
                      "receipt": str(args.out / "receipts.json")}, indent=2))
    return 1 if receipt["status"] == "render_failed" else 2


if __name__ == "__main__":
    sys.exit(main())
