"""Executable negative/positive tests for coverage records, not application tests."""
import copy
import pathlib
import subprocess
import sys
import tempfile
import unittest

import architecture_register as register


class RegisterTests(unittest.TestCase):
    def setUp(self):
        self.data = register.initial()
        self.row = next(r for r in self.data["records"] if r["id"] == "DS05")

    def accepted(self):
        self.row.update(
            applicability="applicable", decision_state="accepted",
            rationale="Externally retried actions", owner="Reviewer",
            selected_approach="Unique key with transactional replay record",
            document="TRD.md#retry", approval="Reviewer decision record",
            workload_constraints="100 concurrent requests",
            requirements=["NFR-01"], epic="E-1", feature="F-1", story="S-1",
            tests=["Concurrent duplicate request"], alternatives=["No automatic retry"],
        )

    def test_catalog_counts_and_viewpoints(self):
        groups = register.load(register.CATALOG)["groups"]
        original = [g for g in groups if g["kind"] == "original"]
        self.assertEqual(len(original), 12)
        self.assertEqual(sum(len(g["topics"]) for g in original), 81)
        self.assertEqual(len(register.catalog()), 97)
        self.assertIn("AR07", register.catalog())
        self.assertIn("DS07", register.catalog())

    def test_initial_draft_not_plan_or_story(self):
        self.assertEqual(register.validate(self.data), [])
        self.assertTrue(register.validate(self.data, "plan"))
        self.assertTrue(register.validate(self.data, "story", ["DS05"]))

    def test_missing_duplicate_unknown_and_renamed_topics_fail(self):
        for mutation in (
            lambda d: d["records"].pop(),
            lambda d: d["records"].append(copy.deepcopy(d["records"][0])),
            lambda d: d["records"][0].update(id="typo"),
            lambda d: d["records"][0].update(topic="replacement"),
        ):
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(self.data)
                mutation(data)
                self.assertTrue(register.validate(data))

    def test_invalid_enums_and_types_fail(self):
        for field, value in (("applicability", "optional"), ("decision_state", "done"),
                             ("implementation_state", "green"), ("tests", "test"),
                             ("evidence", "URL"), ("owner", None)):
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                data["records"][0][field] = value
                self.assertTrue(register.validate(data))

    def test_exclusion_requires_reason_owner_and_readiness_approval(self):
        self.row.update(applicability="not_applicable", implementation_state="not_applicable")
        self.assertTrue(register.validate(self.data))
        self.row.update(rationale="No retried mutation", owner="Reviewer")
        self.assertEqual(register.validate(self.data), [])
        self.assertTrue(register.validate(self.data, "story", ["DS05"]))
        self.row["approval"] = "Reviewer exclusion record"
        self.assertEqual(register.validate(self.data, "story", ["DS05"]), [])

    def test_accepted_does_not_mean_verified(self):
        self.accepted()
        self.assertEqual(register.validate(self.data, "story", ["DS05"]), [])
        self.assertTrue(register.validate(self.data, "release", ["DS05"]))
        self.row["implementation_state"] = "verified"
        self.assertTrue(register.validate(self.data, "release", ["DS05"]))
        self.row["evidence"] = [dict(reference="ci/run", revision="abc123",
                                     environment="test", result="passed")]
        self.assertEqual(register.validate(self.data, "release", ["DS05"]), [])
        self.row["evidence"][0]["result"] = "failed"
        self.assertTrue(register.validate(self.data, "release", ["DS05"]))

    def test_approval_and_traceability_required(self):
        self.accepted()
        for field in ("approval", "document", "selected_approach", "requirements",
                      "epic", "feature", "story", "tests", "workload_constraints"):
            with self.subTest(field=field):
                original = self.row[field]
                self.row[field] = [] if isinstance(original, list) else ""
                self.assertTrue(register.validate(self.data, "story", ["DS05"]))
                self.row[field] = original

    def test_unrelated_pending_does_not_block_accepted_story(self):
        self.accepted()
        self.assertEqual(register.validate(self.data, "story", ["DS05"]), [])
        self.assertTrue(register.validate(self.data, "story", ["DS05", "AI01"]))

    def test_empty_unknown_impacts_and_dangling_relations_fail(self):
        self.assertTrue(register.validate(self.data, "story"))
        self.assertTrue(register.validate(self.data, "release", ["UNKNOWN"]))
        self.row["related_to"] = ["missing"]
        self.assertTrue(register.validate(self.data))

    def test_deferred_requires_impact_and_revisit_and_blocks_story(self):
        self.accepted()
        self.row["decision_state"] = "deferred"
        self.assertTrue(register.validate(self.data))
        self.row.update(impact="Blocks mutation work", revisit="Before implementation")
        self.assertEqual(register.validate(self.data), [])
        self.assertTrue(register.validate(self.data, "story", ["DS05"]))

    def test_plan_allows_owned_unresolved_choices(self):
        for row in self.data["records"]:
            row.update(applicability="applicable", rationale="Needs assessment",
                       owner="Architect", impact="Blocks dependent phase",
                       revisit="Before dependent Story")
        self.assertEqual(register.validate(self.data, "plan"), [])
        self.assertTrue(register.validate(self.data, "story", ["DS05"]))

    def test_cli_no_overwrite_and_no_vacuous_readiness(self):
        script = pathlib.Path(register.__file__)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "coverage.yml"
            def run(*args):
                return subprocess.run([sys.executable, str(script), *args],
                                      capture_output=True, text=True)
            self.assertEqual(run("init", str(path)).returncode, 0)
            original = path.read_bytes()
            self.assertNotEqual(run("init", str(path)).returncode, 0)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(run("check", str(path)).returncode, 0)
            self.assertNotEqual(run("check", str(path), "--stage", "story").returncode, 0)
            path.write_text("schema_version: 1\nschema_version: 1\nrecords: []\n")
            self.assertNotEqual(run("check", str(path)).returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
