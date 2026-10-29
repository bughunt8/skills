import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import contract
import openheart
from build_fixture import JAVA_ROOT, fixture, java_fixture, node, edge, graph, evidence


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.model = json.loads((ROOT / "datasets/checkout-model.json").read_text())

    def reject(self, change):
        change(self.model)
        with self.assertRaises(openheart.Invalid):
            openheart.validate(self.model, ROOT / "datasets")

    def test_committed_contracts_and_fixture_are_current(self):
        self.assertEqual(contract.schema(), json.loads((ROOT / "schemas/analysis.schema.json").read_text()))
        self.assertEqual(contract.catalog(), json.loads((ROOT / "assets/diagram-catalog.json").read_text()))
        self.assertEqual(fixture(), self.model)

    def test_exact_catalog(self):
        self.assertEqual(len(contract.TITLES), 20)
        self.assertEqual(sum(x["upstream"] for x in contract.catalog()["diagrams"]), 19)

    def test_source_validation(self):
        self.assertEqual(openheart.validate(self.model, ROOT / "datasets")["source_consistency"], "pass")

    def test_unfilled_template_rejected(self):
        with self.assertRaises(openheart.Invalid):
            openheart.validate(contract.empty_model())

    def test_unknown_fields(self):
        self.reject(lambda m: m.update(verified=True))

    def test_stale_hash(self):
        self.reject(lambda m: m["files"][0].update(sha256="0" * 64))

    def test_wrong_line_count(self):
        self.reject(lambda m: m["files"][0].update(line_count=100))

    def test_source_path_escape(self):
        self.reject(lambda m: m["files"][0].update(path="../checkout.py"))

    def test_unlisted_evidence(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0]["evidence"][0].update(file="missing.py"))

    def test_false_excerpt(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0]["evidence"][0].update(excerpt="class Phantom:"))

    def test_invalid_range(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0]["evidence"][0].update(line_start=9, line_end=2))

    def test_bool_is_not_line_number(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0]["evidence"][0].update(line_start=True))

    def test_dangling_edge(self):
        self.reject(lambda m: m["diagrams"]["cfg"]["edges"][0].update(target="missing"))

    def test_dangling_parent(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0].update(parent="missing"))

    def test_parent_cycle(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0].update(parent="class:Payment"))

    def test_duplicate_id(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"].append(copy.deepcopy(m["diagrams"]["class"]["nodes"][0])))

    def test_inconsistent_reused_id(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0].update(label="Phantom"))

    def test_no_facts_in_inactive_graph(self):
        self.reject(lambda m: m["diagrams"]["class"].update(status="not_requested"))

    def test_empty_complete_rejected(self):
        self.reject(lambda m: m["diagrams"]["timing"].update(status="complete", reason=""))

    def test_missing_reason(self):
        self.reject(lambda m: m["diagrams"]["timing"].update(reason=""))

    def test_inferred_as_complete_rejected(self):
        self.reject(lambda m: m["diagrams"]["callgraph"].update(status="complete"))

    def test_source_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "checkout.py").symlink_to(ROOT / "datasets/checkout.py")
            with self.assertRaises(openheart.Invalid):
                openheart.validate(self.model, tmp)

    def test_fixture_truth_is_not_a_confirmed_dynamic_call(self):
        self.assertEqual({x["label"] for x in self.model["diagrams"]["class"]["nodes"]}, {"Payment", "Checkout"})
        cg = self.model["diagrams"]["callgraph"]
        self.assertEqual([x["kind"] for x in cg["edges"]], ["candidate_call"])
        self.assertFalse(any(x["target"] == "class:Payment" for x in cg["edges"]))

    def test_schema_without_source_root_does_not_claim_source_pass(self):
        self.assertEqual(openheart.validate(self.model)["source_consistency"], "not_run")

    def test_export_all_categories_and_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = openheart.make_destination(Path(tmp) / "export")
            openheart.export(self.model, out, openheart.validate(self.model, ROOT / "datasets"))
            for key in contract.TITLES:
                for ext in ("json", "mmd", "puml"):
                    self.assertTrue((out / "diagrams" / (key + "." + ext)).is_file())
            for ext in ("json", "mmd", "puml"):
                self.assertEqual((out / "diagrams" / ("ACT." + ext)).read_bytes(),
                                 (out / "diagrams" / ("activity." + ext)).read_bytes())
            ET.parse(out / "diagrams/class.xmi")
            receipt = json.loads((out / "report.json").read_text())
            self.assertEqual(receipt["validation"]["renderer_syntax"], "not_run")
            self.assertNotIn("verified", receipt)
            trace = json.loads((out / "traceability.json").read_text())
            self.assertIn("class:Payment", trace["by_file"]["checkout.py"])

    def test_output_overwrite_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(openheart.Invalid):
                openheart.make_destination(tmp)

    def test_invalid_model_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "must-not-exist"
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/openheart.py"), "export",
                str(ROOT / "datasets/scenarios.json"), "--source-root",
                str(ROOT / "datasets"), "--out", str(dest),
            ], capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(dest.exists())

    def test_declaration_direction_and_native_renderers(self):
        g = copy.deepcopy(self.model["diagrams"]["class"])
        g["edges"] = [edge("test:inherit", "class:Checkout", "class:Payment",
                           "extends", evidence(6, 10, "class Checkout:"))]
        self.assertIn("n0 --|> n1", openheart.mermaid("class", g))
        self.assertIn("n0 --|> n1", openheart.plantuml("class", g))
        self.assertIn("stateDiagram-v2", openheart.mermaid("statemachine", g))

    def test_message_order_and_invalid_ordinals(self):
        g = copy.deepcopy(self.model["diagrams"]["class"])
        ev = evidence(10, 10, "return payment.charge(amount)")
        g["edges"] = [
            edge("z", "class:Checkout", "class:Payment", "message", ev, "first", ordinal=1),
            edge("a", "class:Payment", "class:Checkout", "message", ev, "second", ordinal=2),
        ]
        self.model["diagrams"]["sequence"] = g
        openheart.validate(self.model, ROOT / "datasets")
        text = openheart.mermaid("sequence", g)
        self.assertLess(text.index("first"), text.index("second"))
        g["edges"][1]["attributes"]["ordinal"] = 1
        with self.assertRaises(openheart.Invalid):
            openheart.validate(self.model, ROOT / "datasets")

    def test_literal_blocks_directives(self):
        g = copy.deepcopy(self.model["diagrams"]["class"])
        g["nodes"][0]["label"] = '"\n!include /etc/passwd\n%%{init: x}%%<script>click'
        for fn in (openheart.mermaid, openheart.plantuml):
            text = fn("class", g)
            self.assertNotIn("\n!include", text)
            self.assertNotIn("%%{", text)
            self.assertNotIn("<script>", text)

    def test_all_nonempty_presentations_are_deterministic(self):
        g = self.model["diagrams"]["cfg"]
        shuffled = copy.deepcopy(g)
        shuffled["nodes"].reverse()
        shuffled["edges"].reverse()
        for key in contract.TITLES:
            if key in {"sequence", "communication"}:
                continue
            self.assertEqual(openheart.mermaid(key, g), openheart.mermaid(key, shuffled))
            self.assertEqual(openheart.plantuml(key, g), openheart.plantuml(key, shuffled))
            self.assertTrue(openheart.plantuml(key, g).endswith("@enduml\n"))

    def test_basis_laundering_rejected(self):
        def mutate(m):
            g = m["diagrams"]["callgraph"]
            g.update(status="complete", reason="")
            for record in g["nodes"] + g["edges"]:
                record["basis"] = "source"
        self.reject(mutate)

    def test_resolution_laundering_rejected(self):
        self.reject(lambda m: m["diagrams"]["callgraph"]["nodes"][1]["attributes"].update(resolution="resolved"))

    def test_parent_laundering_rejected(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0].update(parent="class:Checkout"))

    def test_observed_requires_runtime_evidence(self):
        def mutate(m):
            g = copy.deepcopy(m["diagrams"]["class"])
            g["edges"] = []
            g["nodes"] = [g["nodes"][0]]
            g["nodes"][0].update(id="observation:1", basis="observed")
            m["diagrams"]["timing"] = g
        self.reject(mutate)

    def test_trace_role_allows_observed_facts(self):
        self.model["files"][0]["role"] = "trace"
        for group in ("stages", "diagrams"):
            for g in self.model[group].values():
                for record in g["nodes"] + g["edges"]:
                    if record["id"] == "class:Payment":
                        record["basis"] = "observed"
        openheart.validate(self.model, ROOT / "datasets")

    def test_whitespace_evidence_rejected(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0]["evidence"][0].update(excerpt=" "))

    def test_missing_derivation_rejected(self):
        self.reject(lambda m: m["diagrams"]["cfg"]["edges"][0]["attributes"].pop("derivation"))

    def test_placeholder_method_rejected(self):
        self.reject(lambda m: m["diagrams"]["class"].update(status="complete", method="not run"))

    def test_non_sequence_ordinal_type_rejected(self):
        self.reject(lambda m: m["diagrams"]["cfg"]["edges"][0]["attributes"].update(ordinal="a"))

    def test_xmi_namespaces_and_control_characters(self):
        g = copy.deepcopy(self.model["diagrams"]["class"])
        g["nodes"][0]["label"] += "\u0001"
        root = ET.fromstring(openheart.class_xmi(g))
        self.assertEqual(root.tag, "{http://www.eclipse.org/uml2/5.0.0/UML}Model")
        self.assertEqual(root.attrib["{http://www.omg.org/spec/XMI/20131001}version"], "2.5")
        self.assertEqual(root[0].attrib["{http://www.omg.org/spec/XMI/20131001}type"], "uml:Class")
        self.assertNotIn("\u0001", openheart.class_xmi(g))

    def test_atomic_failure_cleans_up_and_allows_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out"
            def fail(partial):
                (partial / "incomplete.json").write_text("{}")
                raise OSError("simulated disk error")
            with self.assertRaises(OSError):
                openheart.atomic_output(dest, fail)
            self.assertEqual(list(Path(tmp).iterdir()), [])
            openheart.atomic_output(dest, lambda p: (p / "ok").write_text("done"))
            self.assertTrue((dest / "ok").exists())

    def test_untyped_fields_and_field_method_identity(self):
        g = copy.deepcopy(self.model["diagrams"]["class"])
        member = {"visibility": "+", "name": "x", "type_name": "", "signature": "",
                  "is_static": False, "is_final": False}
        g["nodes"][0]["fields"] = [member]
        g["nodes"][0]["methods"] = [copy.deepcopy(member)]
        for render in (openheart.mermaid, openheart.plantuml):
            text = render("class", g)
            self.assertNotIn("unnamed", text)
            self.assertIn("+x\n", text)
            self.assertIn("+x()\n", text)

    def test_communication_ordinals(self):
        g = copy.deepcopy(self.model["diagrams"]["cfg"])
        g["edges"][0]["attributes"]["ordinal"] = 2
        g["edges"][1]["attributes"]["ordinal"] = 1
        self.assertIn('|"2. true"|', openheart.mermaid("communication", g))
        self.assertIn(": 2. true", openheart.plantuml("communication", g))

    def test_editor_line_semantics_and_empty_file(self):
        self.assertEqual(openheart.source_lines("a\n# page\f break\nb='\u2028'\nc\n"),
                         ["a", "# page\f break", "b='\u2028'", "c"])
        self.assertEqual(openheart.source_lines("a\r\nb\rc\n"), ["a", "b", "c"])
        self.assertEqual(openheart.source_lines(""), [])
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "empty.py").write_bytes(b"")
            m = contract.empty_model()
            m["source"].update(repository="test", scope=["empty.py"], languages=["Python"])
            m["files"] = [{"path": "empty.py", "sha256": hashlib.sha256(b"").hexdigest(),
                           "line_count": 0, "encoding": "utf-8", "role": "source"}]
            openheart.validate(m, tmp)

    def test_duplicate_json_keys_and_nonfinite_numbers_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            for text in ('{"schema_version":"1.0","schema_version":"2.0"}', '{"x":NaN}'):
                p.write_text(text)
                with self.assertRaises(openheart.Invalid):
                    openheart.load_model(p)

    def test_overflow_numbers_and_surrogates_rejected(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0]["attributes"].update(value=float("inf")))
        self.model = fixture()
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0]["attributes"].update(label="\ud800"))
        self.model = fixture()
        self.model["diagrams"]["class"]["nodes"][0]["attributes"]["value"] = json.loads("1e999")
        with self.assertRaises(openheart.Invalid):
            openheart.validate(self.model)

    def test_scope_and_exclusions(self):
        self.reject(lambda m: m["source"].update(scope=["another-directory"]))
        self.model = fixture()
        self.reject(lambda m: m["source"].update(exclusions=["*.py"]))

    def test_unknown_kind_and_stage_mismatch_rejected(self):
        self.reject(lambda m: m["diagrams"]["class"]["nodes"][0].update(kind="invented"))
        self.model = fixture()
        self.reject(lambda m: m["stages"]["syntax"]["nodes"][0].update(kind="block"))

    def test_missing_ast_attribute_rejected(self):
        self.reject(lambda m: m["stages"]["syntax"]["nodes"][0]["attributes"].pop("node_type"))

    def test_missing_resolution_rejected(self):
        self.reject(lambda m: m["stages"]["calls"]["nodes"][1]["attributes"].pop("resolution"))

    def test_receipt_contains_machine_checks_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = openheart.make_destination(Path(tmp) / "out")
            openheart.export(self.model, out, openheart.validate(self.model, ROOT / "datasets"))
            text = (out / "VALIDATION.md").read_text()
            self.assertIn("Internal validate() in exporter 1.0.0 | pass", text)
            report = json.loads((out / "report.json").read_text())
            self.assertEqual(len(report["model_sha256"]), 64)
            self.assertEqual(report["tool"]["version"], "1.0.0")

    def test_scenario_inventory_declares_manual_and_automated_checks(self):
        cases = json.loads((ROOT / "datasets/scenarios.json").read_text())["cases"]
        self.assertEqual(len(cases), 10)
        for case in cases:
            self.assertIn(case["mode"], {"manual", "automated"})
            if case["mode"] == "automated":
                self.assertTrue(callable(getattr(self, case["test"])))

    def test_java_observer_dataset_and_ground_truth(self):
        model = json.loads((ROOT / "datasets/observer-java-model.json").read_text())
        self.assertEqual(java_fixture(), model)
        openheart.validate(model, JAVA_ROOT)
        g = model["diagrams"]["class"]
        expected_names = {"NewsAgency", "NewsChannel", "Observer", "Subject"}
        self.assertEqual({n["label"].split(".")[-1] for n in g["nodes"]}, expected_names)
        triples = {(e["source"].split(".")[-1], e["kind"], e["target"].split(".")[-1]) for e in g["edges"]}
        self.assertEqual(triples, {
            ("NewsAgency", "implements", "Subject"),
            ("NewsChannel", "implements", "Observer"),
            ("NewsAgency", "type_use", "Observer"),
        })
        self.assertIn("..|>", openheart.mermaid("class", g))
        self.assertIn("..>", openheart.plantuml("class", g))


if __name__ == "__main__":
    unittest.main()
