"""Render tests.

These assert properties of the output rather than comparing against a stored
blob. A byte-for-byte golden file would fail on every cosmetic change and teach
everyone to regenerate it without reading the diff, which is worse than no test.
Determinism is asserted directly instead.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import diagram_ir  # noqa: E402
import diagram_layout  # noqa: E402
import render_diagram  # noqa: E402

EXAMPLES = sorted((ROOT / "examples").glob("*.json"))


def load(path):
    return json.loads(Path(path).read_text("utf-8"))


class TestExamples(unittest.TestCase):
    def test_examples_exist(self):
        self.assertGreaterEqual(len(EXAMPLES), 3, "the examples are part of the docs")

    def test_every_example_is_valid(self):
        for path in EXAMPLES:
            with self.subTest(example=path.name):
                diagram_ir.validate(load(path))

    def test_every_example_renders(self):
        for path in EXAMPLES:
            with self.subTest(example=path.name):
                doc = load(path)
                html = render_diagram.render_html(doc, diagram_layout.layout(doc))
                self.assertIn("<svg", html)
                self.assertGreater(len(html), 5000)
                # No template placeholder may survive into the artifact.
                import re

                left = re.findall(r"__[A-Z][A-Z0-9_]*__", html)
                self.assertEqual(left, [], f"unsubstituted template tokens: {set(left)}")

    def test_kinds_are_covered(self):
        kinds = {load(p)["kind"] for p in EXAMPLES}
        self.assertIn("sequence", kinds, "the sequence layout needs an example")
        self.assertTrue(kinds - {"sequence"}, "the graph layout needs an example")


class TestOutputProperties(unittest.TestCase):
    def setUp(self):
        self.doc = load(ROOT / "examples" / "web-platform.architecture.json")
        self.geo = diagram_layout.layout(self.doc)
        self.html = render_diagram.render_html(self.doc, self.geo)

    def test_standalone_no_network(self):
        """The artifact must not fetch anything at open time.

        Checked against the patterns that actually load a resource, not against
        the substring "http". The SVG namespace declaration
        xmlns="http://www.w3.org/2000/svg" is an identifier that no browser ever
        dereferences, and flagging it makes the test cry wolf on correct output.
        """
        import re

        offenders = []
        for pattern, what in [
            (r"<link\b", "<link> element"),
            (r"<script[^>]*\bsrc\s*=", "external script"),
            (r"<img[^>]*\bsrc\s*=\s*[\"']https?:", "remote image"),
            (r"@import", "CSS @import"),
            (r"url\(\s*[\"']?https?:", "CSS remote url()"),
            (r"<use[^>]*\bhref\s*=\s*[\"']https?:", "remote SVG use"),
            (r"@font-face", "webfont"),
        ]:
            if re.search(pattern, self.html, re.I):
                offenders.append(what)
        self.assertEqual(offenders, [], f"artifact loads external resources: {offenders}")

        # Sanity-check the check itself: it must catch a planted reference.
        planted = self.html.replace("</head>", '<link rel="stylesheet" href="x.css"></head>')
        self.assertRegex(planted, r"<link\b")

    def test_css_and_script_are_inlined(self):
        self.assertIn("<style>", self.html)
        self.assertIn("--bg:", self.html.replace(" ", "").replace("\n", "") or "")
        self.assertIn("<script>", self.html)

    def test_every_node_is_present_and_addressable(self):
        for node in self.doc["nodes"]:
            self.assertIn(f'data-id="{node["id"]}"', self.html)

    def test_edges_carry_their_endpoints(self):
        # The focus interaction depends on these attributes.
        for edge in self.doc["edges"]:
            self.assertIn(f'data-from="{edge["from"]}"', self.html)

    def test_accessible_description_is_not_empty(self):
        desc = render_diagram.a11y_description(self.doc, self.geo)
        self.assertGreater(len(desc), 60)
        self.assertIn(self.doc["title"], desc)

    def test_deterministic(self):
        again = render_diagram.render_html(self.doc, diagram_layout.layout(self.doc))
        self.assertEqual(self.html, again, "rendering is not deterministic")

    def test_group_boxes_do_not_overlap(self):
        """Groups are laid out as swimlanes precisely so this holds. Free layout
        let two boundaries occupy the same space and become unreadable."""
        boxes = self.geo["groups"]
        self.assertGreaterEqual(len(boxes), 2)
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
                oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
                self.assertFalse(
                    ox > 1 and oy > 1,
                    f"group {a['label']!r} overlaps {b['label']!r}",
                )

    def test_nodes_stay_inside_their_group(self):
        by_id = {n["id"]: n for n in self.geo["nodes"]}
        for gi, group in enumerate(self.doc.get("groups", [])):
            box = self.geo["groups"][gi]
            for member in group["nodes"]:
                node = by_id[member]
                self.assertGreaterEqual(node["x"], box["x"])
                self.assertGreaterEqual(node["y"], box["y"])
                self.assertLessEqual(node["x"] + node["w"], box["x"] + box["w"])
                self.assertLessEqual(node["y"] + node["h"], box["y"] + box["h"])

    def test_escaping(self):
        doc = {
            "kind": "architecture",
            "title": 'Ampersands & "quotes" <tags>',
            "nodes": [{"id": "a", "label": "<script>alert(1)</script>"}],
        }
        html = render_diagram.render_html(doc, diagram_layout.layout(doc))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


class TestCycles(unittest.TestCase):
    def test_cyclic_document_lays_out(self):
        """A lifecycle state machine is cyclic. Ranking needs a DAG, so cycles
        must be detected and set aside rather than causing a failure."""
        doc = load(ROOT / "examples" / "deploy.lifecycle.json")
        geo = diagram_layout.layout(doc)
        back = [e for e in geo["edges"] if e["back"]]
        self.assertTrue(back, "the lifecycle example is cyclic; no back edge was identified")
        for edge in back:
            self.assertEqual(edge["style"], "dashed")

    def test_back_edges_are_routed_clear_of_nodes(self):
        doc = load(ROOT / "examples" / "deploy.lifecycle.json")
        geo = diagram_layout.layout(doc)
        top = min(n["y"] for n in geo["nodes"])
        for edge in geo["edges"]:
            if edge["back"]:
                self.assertLess(
                    edge["ly"], top, "a back-edge label sits over the node area"
                )

    def test_self_loop_does_not_crash(self):
        doc = {
            "kind": "lifecycle",
            "title": "self loop",
            "nodes": [{"id": "a", "label": "A"}],
            "edges": [{"from": "a", "to": "a", "label": "retry"}],
        }
        geo = diagram_layout.layout(diagram_ir.validate(doc))
        self.assertEqual(len(geo["edges"]), 1)


class TestCli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "render_diagram.py"), *args],
            capture_output=True,
            text=True,
        )

    def test_self_test_passes(self):
        result = self.run_cli("--self-test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("self-test passed", result.stdout)

    def test_check_accepts_examples(self):
        for path in EXAMPLES:
            with self.subTest(example=path.name):
                result = self.run_cli(str(path), "--check")
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_document_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text(
                json.dumps(
                    {
                        "kind": "architecture",
                        "title": "t",
                        "nodes": [{"id": "a", "label": "A"}],
                        "edges": [{"from": "a", "to": "missing"}],
                    }
                ),
                "utf-8",
            )
            result = self.run_cli(str(bad), "--check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("not a declared node id", result.stderr)

    def test_malformed_json_is_reported_with_a_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "broken.json"
            bad.write_text('{"kind": "architecture",,}', "utf-8")
            result = self.run_cli(str(bad), "--check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("line", result.stderr)

    def test_writes_html_and_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = EXAMPLES[0]
            html = Path(tmp) / "out.html"
            svg = Path(tmp) / "out.svg"
            self.assertEqual(self.run_cli(str(src), "-o", str(html)).returncode, 0)
            self.assertEqual(self.run_cli(str(src), "--svg", "-o", str(svg)).returncode, 0)
            self.assertTrue(html.read_text("utf-8").startswith("<!DOCTYPE html>"))
            self.assertTrue(svg.read_text("utf-8").startswith("<svg"))


if __name__ == "__main__":
    unittest.main()
