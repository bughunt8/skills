#!/usr/bin/env python3
"""Regenerate the explicitly partial, originally authored checkout model."""

import hashlib
from pathlib import Path

from contract import ROOT, empty_model, write_json


def evidence(start, end, excerpt):
    return [{"file": "checkout.py", "line_start": start, "line_end": end, "excerpt": excerpt}]


def node(identity, label, kind, ev, basis="source", **attributes):
    return {
        "id": identity, "label": label, "kind": kind, "basis": basis,
        "parent": None, "evidence": ev, "fields": [], "methods": [],
        "attributes": attributes,
    }


def edge(identity, source, target, kind, ev, label="", basis="derived", **attributes):
    if basis == "derived":
        attributes.setdefault("derivation", "Manually reconstructed from the cited scoped source statement.")
    return {
        "id": identity, "source": source, "target": target, "kind": kind,
        "label": label, "basis": basis, "evidence": ev, "attributes": attributes,
    }


def graph(nodes, edges, reason):
    return {
        "status": "partial", "reason": reason,
        "method": "Manually reconstructed fixture, not parser/solver output",
        "nodes": nodes, "edges": edges,
    }


def fixture():
    model = empty_model()
    data = (ROOT / "datasets/checkout.py").read_bytes()
    model["source"] = {
        "repository": "Originally authored checkout fixture", "revision": "fixture-v1",
        "scope": ["checkout.py"], "languages": ["Python"], "exclusions": [],
    }
    model["files"] = [{
        "path": "checkout.py", "sha256": hashlib.sha256(data).hexdigest(),
        "line_count": 10, "encoding": "utf-8", "role": "source",
    }]
    payment_ev = evidence(1, 3, "class Payment:")
    checkout_ev = evidence(6, 10, "class Checkout:")
    branch_ev = evidence(7, 10, "if amount <= 0:")
    call_ev = evidence(10, 10, "return payment.charge(amount)")
    classes = [
        node("class:Payment", "Payment", "class", payment_ev),
        node("class:Checkout", "Checkout", "class", checkout_ev),
    ]
    model["stages"]["symbols"] = graph(classes, [], "Only class declarations are catalogued.")
    model["diagrams"]["class"] = graph(classes, [], "Members and relationships omitted in this fixture.")
    ast_nodes = [
        node("ast:submit", "submit", "ast", evidence(7, 10, "def submit(self, payment, amount):"), node_type="FunctionDef"),
        node("ast:if", "if amount <= 0", "ast", branch_ev, node_type="If"),
        node("ast:call", "payment.charge", "ast", call_ev, node_type="Call"),
    ]
    ast_edges = [
        edge("ast:contains:if", "ast:submit", "ast:if", "contains", branch_ev),
        edge("ast:contains:call", "ast:submit", "ast:call", "contains", call_ev),
    ]
    model["stages"]["syntax"] = graph(ast_nodes, ast_edges, "Selected syntax only; no parser run.")
    model["diagrams"]["ast"] = graph(ast_nodes, ast_edges, "Selected syntax only; no parser run.")
    blocks = [
        node("block:guard", "amount <= 0", "block", branch_ev),
        node("block:false", "return False", "block", evidence(9, 9, "return False")),
        node("block:charge", "return payment.charge(amount)", "block", call_ev),
    ]
    flows = [
        edge("cfg:true", "block:guard", "block:false", "true", branch_ev, "true",
             derivation="The if body returns False when amount is nonpositive."),
        edge("cfg:false", "block:guard", "block:charge", "false", branch_ev, "false",
             derivation="The fallthrough returns the call result."),
    ]
    model["stages"]["control_flow"] = graph(blocks, flows, "Entry/exit and exceptional paths omitted.")
    for key in ("activity", "cfg"):
        model["diagrams"][key] = graph(blocks, flows, "Selected branch view; exceptions omitted.")
    calls = [
        node("call:caller", "Checkout.submit", "symbol", evidence(7, 10, "def submit(")),
        node("call:unresolved", "payment.charge, unresolved receiver", "callsite",
             call_ev, basis="inferred", resolution="unresolved"),
    ]
    call_edges = [
        edge("call:site", "call:caller", "call:unresolved", "candidate_call", call_ev,
             "unresolved receiver", basis="inferred",
             derivation="Receiver type is not constrained; Payment is not a confirmed callee."),
    ]
    model["stages"]["calls"] = graph(calls, call_edges, "Dynamic receiver cannot be resolved from this source.")
    model["diagrams"]["callgraph"] = graph(calls, call_edges, "Dynamic receiver unresolved.")
    for key in model["diagrams"]:
        if model["diagrams"][key]["status"] == "not_requested":
            model["diagrams"][key].update(
                status="insufficient_evidence", reason="This fixture supplies no supported projection for this category.")
    model["limitations"] = [
        "Partial manually authored regression fixture, not automatic extraction.",
        "No token corpus, SSA, postdominators, path solver, timing or deployment analysis.",
        "No inferred edge from payment.charge to Payment.charge.",
    ]
    for key, reason in {
        "ingestion": "File inventory is present; a lexical token corpus was not computed.",
        "traceability": "Per-record evidence is present; binary TRA links are not computed. Export builds the normalized source index.",
        "uml": "Class projection uses declaration records; a separate UMA record graph is not computed.",
        "unified": "The normalized model is the container; binary SCPG unification is not computed.",
    }.items():
        model["stages"][key]["reason"] = reason
    return model


JAVA_ROOT = ROOT / "references/upstream/source/examples/test_patterns_codebase"
JAVA_PACKAGE = "com/patterns/behavioral/observer"


def java_fixture():
    """Independent declaration truth, not copied upstream output JSON."""
    from openheart import source_lines
    model = empty_model()
    model["source"] = {
        "repository": "OpenHeart MIT Observer source fixture",
        "revision": "0bf962fc06e975e9ea7610242b8997b1391fec05",
        "scope": [JAVA_PACKAGE], "languages": ["Java"], "exclusions": [],
    }
    nodes = []
    specifications = [
        ("NewsAgency", "class", 6, "public class NewsAgency implements Subject {",
         [("-", "news", "String"), ("-", "observers", "List<Observer>")],
         [("setNews", "String news"), ("attach", "Observer observer"),
          ("detach", "Observer observer"), ("notifyObservers", "")]),
        ("NewsChannel", "class", 3, "public class NewsChannel implements Observer {",
         [("-", "news", "String")], [("update", "String news")]),
        ("Observer", "interface", 3, "public interface Observer {", [], [("update", "String news")]),
        ("Subject", "interface", 3, "public interface Subject {", [],
         [("attach", "Observer observer"), ("detach", "Observer observer"), ("notifyObservers", "")]),
    ]
    def qualified(name):
        return "com.patterns.behavioral.observer." + name
    def member(visibility, name, type_name, signature):
        return {"visibility": visibility, "name": name, "type_name": type_name,
                "signature": signature, "is_static": False, "is_final": False}
    for name, kind, line, declaration, fields, methods in specifications:
        path = f"{JAVA_PACKAGE}/{name}.java"
        data = (JAVA_ROOT / path).read_bytes()
        lines = source_lines(data.decode("utf-8"))
        model["files"].append({
            "path": path, "sha256": hashlib.sha256(data).hexdigest(),
            "line_count": len(lines), "encoding": "utf-8", "role": "source",
        })
        ev = [{"file": path, "line_start": line, "line_end": len(lines), "excerpt": declaration}]
        n = node("java:" + qualified(name), qualified(name), kind, ev,
                 qualified_name=qualified(name), symbol_kind=kind)
        n["fields"] = [member(v, f, t, f"{t} {f}") for v, f, t in fields]
        n["methods"] = [member("+", m, "void", f"void {m}({params})") for m, params in methods]
        nodes.append(n)
    by_name = {n["label"].split(".")[-1]: n for n in nodes}
    edges = []
    for child, parent in [("NewsAgency", "Subject"), ("NewsChannel", "Observer")]:
        edges.append(edge(
            f"java:implements:{child}:{parent}", by_name[child]["id"], by_name[parent]["id"],
            "implements", by_name[child]["evidence"], "implements",
            derivation=f"The declaration explicitly states implements {parent}.",
        ))
    field_ev = [{
        "file": JAVA_PACKAGE + "/NewsAgency.java", "line_start": 8, "line_end": 8,
        "excerpt": "private List<Observer> observers = new ArrayList<>();",
    }]
    edges.append(edge("java:type-use:NewsAgency:Observer", by_name["NewsAgency"]["id"],
                      by_name["Observer"]["id"], "type_use", field_ev, "observer element type",
                      derivation="The declared generic element type refers to the same-package Observer interface."))
    model["stages"]["symbols"] = graph(nodes, edges, "JDK types and full name-resolution tables are omitted.")
    model["diagrams"]["class"] = graph(nodes, edges, "Scoped declarations only; JDK types and full UML ownership semantics omitted.")
    model["limitations"] = [
        "Model independently authored from four MIT-licensed Java inputs at the pinned upstream revision.",
        "No upstream executable or output JSON used as the truth oracle.",
        "Only declarations, signatures, two realizations and one type dependency are qualified.",
        "No token, CFG, SSA, call, ROBDD, runtime, deployment or whole-language benchmark is claimed.",
    ]
    for key in model["stages"]:
        if key != "symbols":
            model["stages"][key]["reason"] = "Not computed in this declaration-only Java regression."
    return model


if __name__ == "__main__":
    write_json(ROOT / "datasets/checkout-model.json", fixture())
    write_json(ROOT / "datasets/observer-java-model.json", java_fixture())
