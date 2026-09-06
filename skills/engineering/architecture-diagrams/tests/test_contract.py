"""The schema and the validator must not drift apart.

`scripts/diagram_ir.py` is what actually runs; `schemas/diagram.schema.json` is
what an author's editor reads. Two descriptions of one contract will disagree
eventually unless something fails when they do, so this is that something.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import diagram_ir  # noqa: E402


class TestSchemaMatchesValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "schemas" / "diagram.schema.json").read_text("utf-8"))

    def test_kinds_match(self):
        self.assertEqual(
            tuple(self.schema["properties"]["kind"]["enum"]),
            diagram_ir.ALL_KINDS,
            "the kinds the schema allows differ from the kinds the validator allows",
        )

    def test_shapes_match(self):
        self.assertEqual(
            tuple(self.schema["$defs"]["shape"]["enum"]),
            diagram_ir.NODE_SHAPES,
            "shape vocabularies have drifted",
        )

    def test_styles_match(self):
        self.assertEqual(
            tuple(self.schema["$defs"]["style"]["enum"]), diagram_ir.EDGE_STYLES
        )

    def test_orientations_match(self):
        self.assertEqual(
            tuple(self.schema["properties"]["orientation"]["enum"]),
            diagram_ir.ORIENTATIONS,
        )

    def test_required_keys_match(self):
        pairs = [
            (self.schema["required"], diagram_ir.REQUIRED_TOP, "document root"),
            (self.schema["$defs"]["node"]["required"], diagram_ir.REQUIRED_NODE, "node"),
            (self.schema["$defs"]["edge"]["required"], diagram_ir.REQUIRED_EDGE, "edge"),
            (
                self.schema["$defs"]["participant"]["required"],
                diagram_ir.REQUIRED_PARTICIPANT,
                "participant",
            ),
            (
                self.schema["$defs"]["message"]["required"],
                diagram_ir.REQUIRED_MESSAGE,
                "message",
            ),
        ]
        for schema_req, validator_req, what in pairs:
            self.assertEqual(
                sorted(schema_req), sorted(validator_req), f"required keys differ for {what}"
            )

    def test_schema_closes_every_object(self):
        """additionalProperties:false everywhere, because the validator rejects
        unknown keys and the schema must say the same thing."""
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

        walk(self.schema)


if __name__ == "__main__":
    unittest.main()
