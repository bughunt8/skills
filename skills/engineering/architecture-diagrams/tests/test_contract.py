"""The schema is generated from the validator, so this checks it is not stale and
that the two actually agree on behaviour.

The previous version of this file compared enum tuples and required-key lists and
called that a guarantee against drift. It was not one: the schema allowed sequence
fields on a graph document and `orientation` on a sequence document, both of which
the validator rejects, and three separate schema-only mutations left every test
green. The schema is now generated from `diagram_ir`'s field specs, which removes
the possibility instead of testing for it, and the parity matrix below checks
agreement on real documents rather than on metadata.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import diagram_ir as ir  # noqa: E402
import generate_schema  # noqa: E402


class TestSchemaIsGenerated(unittest.TestCase):
    def test_committed_schema_is_not_stale(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_schema.py"), "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_staleness_gate_can_fail(self):
        """Prove the check above is not vacuous, without touching the real file."""
        generated = generate_schema.build()
        mutated = json.loads(json.dumps(generated))
        mutated["$defs"]["node"]["properties"]["note"] = {"type": "number"}
        self.assertNotEqual(
            json.dumps(generated, sort_keys=True),
            json.dumps(mutated, sort_keys=True),
            "a schema mutation produced an identical document; the check cannot fail",
        )

    def test_schema_declares_the_generator(self):
        schema = json.loads((ROOT / "schemas" / "diagram.schema.json").read_text("utf-8"))
        self.assertIn("GENERATED FILE", schema["description"])
        self.assertIn("generate_schema.py", schema["description"])

    def test_every_object_is_closed(self):
        """The validator rejects unknown keys, so the schema must too."""
        schema = json.loads((ROOT / "schemas" / "diagram.schema.json").read_text("utf-8"))

        def walk(node, path="#"):
            if isinstance(node, dict):
                if node.get("type") == "object" and "properties" in node:
                    self.assertIs(
                        node.get("additionalProperties"),
                        False,
                        f"{path} allows unknown keys but the validator does not",
                    )
                for key, value in node.items():
                    walk(value, f"{path}/{key}")
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    walk(value, f"{path}[{i}]")

        walk(schema)


# (name, document, must_be_valid). One row per rule the contract states, so a
# change to either side that alters behaviour shows up here.
PARITY = [
    ("minimal graph", {"kind": "architecture", "title": "t",
                       "nodes": [{"id": "a", "label": "A"}]}, True),
    ("minimal sequence", {"kind": "sequence", "title": "t",
                          "participants": [{"id": "a", "label": "A"}],
                          "messages": [{"from": "a", "to": "a"}]}, True),
    ("all optional graph fields", {"kind": "workflow", "title": "t", "subtitle": "s",
                                   "footer": "f", "orientation": "TB", "legend": ["x"],
                                   "groups": [{"label": "g", "nodes": ["a"]}],
                                   "nodes": [{"id": "a", "label": "A", "shape": "round",
                                              "note": "n", "tech": "T", "accent": True}],
                                   "edges": [{"from": "a", "to": "a", "label": "l",
                                              "style": "dotted", "accent": False}]}, True),
    ("empty string title", {"kind": "architecture", "title": "",
                            "nodes": [{"id": "a", "label": "A"}]}, False),
    ("whitespace title", {"kind": "architecture", "title": "   ",
                          "nodes": [{"id": "a", "label": "A"}]}, False),
    ("no kind", {"title": "t", "nodes": [{"id": "a", "label": "A"}]}, False),
    ("unknown kind", {"kind": "gantt", "title": "t"}, False),
    ("graph with no nodes", {"kind": "architecture", "title": "t", "nodes": []}, False),
    ("orientation on a sequence", {"kind": "sequence", "title": "t", "orientation": "LR",
                                   "participants": [{"id": "a", "label": "A"}],
                                   "messages": [{"from": "a", "to": "a"}]}, False),
    ("participants on a graph", {"kind": "architecture", "title": "t",
                                 "nodes": [{"id": "a", "label": "A"}],
                                 "participants": []}, False),
    ("nodes on a sequence", {"kind": "sequence", "title": "t",
                             "participants": [{"id": "a", "label": "A"}],
                             "messages": [{"from": "a", "to": "a"}],
                             "nodes": []}, False),
    ("non-string tech", {"kind": "architecture", "title": "t",
                         "nodes": [{"id": "a", "label": "A", "tech": 7}]}, False),
    ("non-boolean accent", {"kind": "architecture", "title": "t",
                            "nodes": [{"id": "a", "label": "A", "accent": "yes"}]}, False),
    ("legend not a list", {"kind": "architecture", "title": "t",
                           "nodes": [{"id": "a", "label": "A"}], "legend": 7}, False),
    ("legend of non-strings", {"kind": "architecture", "title": "t",
                               "nodes": [{"id": "a", "label": "A"}], "legend": [1]}, False),
    ("unknown group key", {"kind": "architecture", "title": "t",
                           "nodes": [{"id": "a", "label": "A"}],
                           "groups": [{"label": "g", "nodes": ["a"], "colour": "red"}]}, False),
    ("unhashable group member", {"kind": "architecture", "title": "t",
                                 "nodes": [{"id": "a", "label": "A"}],
                                 "groups": [{"label": "g", "nodes": [{"x": 1}]}]}, False),
    ("edge to nowhere", {"kind": "architecture", "title": "t",
                         "nodes": [{"id": "a", "label": "A"}],
                         "edges": [{"from": "a", "to": "ghost"}]}, False),
    ("duplicate node id", {"kind": "architecture", "title": "t",
                           "nodes": [{"id": "a", "label": "A"}, {"id": "a", "label": "B"}]}, False),
    ("exact duplicate edge", {"kind": "architecture", "title": "t",
                              "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                              "edges": [{"from": "a", "to": "b"}, {"from": "a", "to": "b"}]}, False),
    ("parallel edges, distinct labels", {"kind": "architecture", "title": "t",
                                         "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                                         "edges": [{"from": "a", "to": "b", "label": "read"},
                                                   {"from": "a", "to": "b", "label": "write"}]}, True),
    ("node in two groups", {"kind": "architecture", "title": "t",
                            "nodes": [{"id": "a", "label": "A"}],
                            "groups": [{"label": "one", "nodes": ["a"]},
                                       {"label": "two", "nodes": ["a"]}]}, False),
    ("unknown shape", {"kind": "architecture", "title": "t",
                       "nodes": [{"id": "a", "label": "A", "shape": "hexagon"}]}, False),
    ("unknown top key", {"kind": "architecture", "title": "t",
                         "nodes": [{"id": "a", "label": "A"}], "colour": "red"}, False),
]


class TestValidatorBehaviour(unittest.TestCase):
    def test_parity_matrix(self):
        for name, doc, should_pass in PARITY:
            with self.subTest(case=name):
                try:
                    ir.validate(doc)
                    ok = True
                    detail = ""
                except ir.ValidationError as exc:
                    ok = False
                    detail = exc.problems[0]
                except Exception as exc:  # noqa: BLE001
                    self.fail(
                        f"{name}: validator raised {type(exc).__name__} instead of "
                        f"ValidationError: {exc}"
                    )
                self.assertEqual(
                    ok,
                    should_pass,
                    f"{name}: expected {'valid' if should_pass else 'invalid'}"
                    + (f", validator said: {detail}" if detail else ""),
                )

    def test_no_document_makes_the_validator_crash(self):
        """Invalid input must always arrive as ValidationError, never a traceback."""
        hostile = [
            None, 7, "text", [], {},
            {"kind": None, "title": None},
            {"kind": "architecture", "title": "t", "nodes": "not a list"},
            {"kind": "architecture", "title": "t", "nodes": [None]},
            {"kind": "architecture", "title": "t", "nodes": [{"id": {}, "label": "A"}]},
            {"kind": "sequence", "title": "t", "participants": [{"id": [], "label": "A"}],
             "messages": [{"from": "a", "to": "a"}]},
            {"kind": "architecture", "title": "t", "nodes": [{"id": "a", "label": "A"}],
             "edges": [{"from": {}, "to": "a"}]},
        ]
        for doc in hostile:
            with self.subTest(doc=repr(doc)[:60]):
                try:
                    ir.validate(doc)
                except ir.ValidationError:
                    pass
                except Exception as exc:  # noqa: BLE001
                    self.fail(f"validator raised {type(exc).__name__}: {exc}")

    def test_multiple_problems_are_reported_together(self):
        doc = {
            "kind": "architecture",
            "title": "t",
            "nodes": [{"id": "a", "label": "A", "tech": 1}, {"id": "a", "label": "B"}],
            "edges": [{"from": "a", "to": "ghost"}],
            "colour": "red",
        }
        with self.assertRaises(ir.ValidationError) as caught:
            ir.validate(doc)
        self.assertGreaterEqual(
            len(caught.exception.problems), 4, caught.exception.problems
        )

    def test_every_problem_names_a_path(self):
        doc = {"kind": "architecture", "title": "t",
               "nodes": [{"id": "a", "label": "A", "accent": "yes"}]}
        with self.assertRaises(ir.ValidationError) as caught:
            ir.validate(doc)
        for problem in caught.exception.problems:
            self.assertTrue(
                any(tok in problem for tok in ("nodes[", "edges[", "groups[", "document root",
                                               "participants[", "messages[", "title", "kind")),
                f"problem does not say where it applies: {problem}",
            )


if __name__ == "__main__":
    unittest.main()
