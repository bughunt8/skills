#!/usr/bin/env python3
"""Offline regression fixtures in system temporary directories, never in a repo."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
import check_skill_dependencies as checker

BASE = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("SKILL_DEPENDENCY_SOURCE_ROOT", str(BASE)))
LOCAL = Path(os.environ.get("SKILL_DEPENDENCY_LOCAL_ROOT", str(BASE)))


class Dependencies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = checker.read_registry(BASE)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="skill-dependencies-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.r = copy.deepcopy(self.registry)
        for e in self.r["providers"]:
            for f in e["files"]:
                dest = self.root / f["path"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SOURCE / f["source_path"], dest)
        for e in self.r["auxiliary_providers"]:
            dest = self.root / e["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(LOCAL / e["path"], dest)
            if e.get("codex"):
                pair = self.root / e["codex"]["path"]
                pair.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(LOCAL / e["codex"]["path"], pair)

    def entry(self, name):
        return next(e for e in self.r["providers"] if e["name"] == name)

    def rehash(self, relative):
        # Trusted registry updates deliberately let tests reach deeper structural checks.
        f = next(f for e in self.r["providers"] for f in e["files"] if f["path"] == relative)
        f["sha256"] = hashlib.sha256((self.root / relative).read_bytes()).hexdigest()

    def mutate(self, relative, before, after, rehash=True):
        path = self.root / relative
        text = path.read_text()
        self.assertIn(before, text)
        path.write_text(text.replace(before, after))
        if rehash:
            self.rehash(relative)

    def assert_errors(self, fragment):
        self.assertTrue(any(fragment in e for e in checker.check(self.root, self.r)), checker.check(self.root, self.r))

    def refuse(self, fragment, name, invoker="model", caller=None):
        with self.assertRaisesRegex(checker.Invalid, fragment):
            checker.resolve(self.root, self.r, name, invoker, caller)

    def test_pristine_release(self):
        self.assertEqual(checker.check(self.root, self.r), [])
        self.assertEqual(len(self.r["providers"]), 27)
        self.assertEqual(sum(len(e["files"]) for e in self.r["providers"]), 79)
        self.assertEqual(sum(len(e["operative"]) for e in self.r["providers"]), 18)

    def test_exact_model_target(self):
        result = checker.resolve(self.root, self.r, "grilling", "model", "grill-me")
        self.assertEqual(result, self.root / "skills/productivity/grilling/SKILL.md")

    def test_duplicate_name_with_yaml_comment_is_refused(self):
        duplicate = self.root / "skills/shadow/tdd/SKILL.md"
        duplicate.parent.mkdir(parents=True)
        duplicate.write_text('---\nname: "tdd"   # valid YAML comment\ndescription: "Shadow"\n---\n')
        self.refuse("ambiguous provider identity", "tdd")

    def test_human_alias_expands_before_invocation(self):
        self.assertEqual(checker.resolve(self.root, self.r, "/grill-me-with-docs", "user"),
                         self.root / "skills/engineering/grill-with-docs/SKILL.md")
        self.assertFalse((self.root / "skills/engineering/grill-me-with-docs").exists())

    def test_setup_alias_requires_top_level_human_only_and_codex_pair(self):
        path = checker.resolve(self.root, self.r, "setup-github-repository", "user")
        self.assertEqual(path, self.root / "skills/engineering/github-repository-setup/SKILL.md")
        self.assertIs(checker.frontmatter(path)["disable-model-invocation"], True)
        self.assertIs(checker.codex(path.parent / "agents/openai.yaml")["policy"]["allow_implicit_invocation"], False)
        self.refuse("user-only", "github-repository-setup")
        self.refuse("human-only alias", "setup-github-repository")

    def test_human_alias_binds_exact_path_despite_duplicate_canonical_name(self):
        path = self.root / "skills/other/grill-with-docs/SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\nname: grill-with-docs\ndescription: alternate provider\n---\n")
        self.assertEqual(checker.resolve(self.root, self.r, "grill-me-with-docs", "user"),
                         self.root / checker.NATIVE["grill-with-docs"])
        self.refuse("ambiguous provider identity", "grill-with-docs", invoker="user")
        self.refuse("user-only", "grill-with-docs", invoker="model")

    def test_setup_missing_codex_metadata_refused(self):
        path = self.root / "skills/engineering/github-repository-setup/agents/openai.yaml"
        path.rename(path.with_suffix(".missing"))
        self.assert_errors("missing file/resource")

    def test_setup_nested_only_metadata_refused(self):
        e = next(x for x in self.r["auxiliary_providers"] if x["id"] == "github-repository-setup")
        p = self.root / e["path"]
        p.write_text(p.read_text().replace("disable-model-invocation: true", "metadata:\n  disable-model-invocation: true"))
        e["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        self.assert_errors("top-level human-only setup metadata required")

    def test_setup_codex_pair_mismatch_refused(self):
        e = next(x for x in self.r["auxiliary_providers"] if x["id"] == "github-repository-setup")
        p = self.root / e["codex"]["path"]
        p.write_text(p.read_text().replace("allow_implicit_invocation: false", "allow_implicit_invocation: true"))
        e["codex"]["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        self.assert_errors("auxiliary YAML/Codex pair mismatch")

    def test_model_refused_user_only(self):
        self.refuse("user-only", "grill-with-docs", caller="ask-matt")
        self.refuse("user-only", "implement-spec")
        self.refuse("user-only", "setup-matt-pocock-skills", caller="github-repository-setup")

    def test_model_refused_human_alias(self):
        self.refuse("human-only alias", "grill-me-with-docs", caller="grill-me")

    def test_research_ambiguous_without_caller(self):
        self.refuse("ambiguous research", "research")
        self.refuse("ambiguous research", "research", invoker="user")

    def test_research_scoped_to_exact_matt_provider(self):
        path = checker.resolve(self.root, self.r, "research", "model", "wayfinder")
        self.assertEqual(path, self.root / "skills/engineering/research/SKILL.md")
        self.assertNotEqual(path, self.root / "skills/research/research/skills/research/SKILL.md")

    def test_research_wrong_caller_refused(self):
        self.refuse("ambiguous research", "research", caller="github-repository-setup")

    def test_wrong_provider_graph_path_refused(self):
        edge = next(e for e in self.entry("wayfinder")["operative"] if e["target"] == "research")
        edge["provider_path"] = "skills/research/research/skills/research/SKILL.md"
        with self.assertRaisesRegex(checker.Invalid, "wrong graph provider"):
            checker.validate_registry(self.r)

    def test_wrong_native_provider_refused(self):
        self.entry("research")["path"] = "skills/research/research/skills/research/SKILL.md"
        with self.assertRaisesRegex(checker.Invalid, "wrong provider identity/path"):
            checker.validate_registry(self.r)

    def test_missing_resource_refused(self):
        relative = "skills/engineering/domain-modeling/GLOSSARY-FORMAT.md"
        (self.root / relative).rename(self.root / (relative + ".missing"))
        self.assert_errors("missing file/resource")
        self.refuse("dependency check failed", "domain-modeling")

    def test_resource_bytes_drift_refused(self):
        self.mutate("skills/engineering/pr/CREDITS.md", "show-me", "show-me-changed", rehash=False)
        self.assert_errors("file hash mismatch")

    def test_body_hash_drift_refused(self):
        self.mutate("skills/engineering/research/SKILL.md", "name: research", "name: fake", rehash=False)
        self.assert_errors("file hash mismatch")

    def test_provider_frontmatter_identity_refused(self):
        self.mutate("skills/engineering/research/SKILL.md", "name: research", "name: fake")
        self.assert_errors("wrong provider identity")

    def test_frontmatter_and_codex_pair_mismatch(self):
        path = "skills/engineering/grill-with-docs/agents/openai.yaml"
        self.mutate(path, "allow_implicit_invocation: false", "allow_implicit_invocation: true")
        self.assert_errors("invocation YAML/Codex pair mismatch")

    def test_yaml_boolean_string_not_accepted(self):
        path = "skills/engineering/grill-with-docs/SKILL.md"
        self.mutate(path, "disable-model-invocation: true", 'disable-model-invocation: "true"')
        self.assert_errors("must be a YAML boolean")

    def test_codex_boolean_string_not_accepted(self):
        path = "skills/engineering/grill-with-docs/agents/openai.yaml"
        self.mutate(path, "allow_implicit_invocation: false", 'allow_implicit_invocation: "false"')
        self.assert_errors("must be a YAML boolean")

    def test_duplicate_yaml_keys_refused(self):
        path = "skills/engineering/grill-with-docs/SKILL.md"
        self.mutate(path, "disable-model-invocation: true",
                    "disable-model-invocation: true\ndisable-model-invocation: false")
        self.assert_errors("duplicate YAML key")

    def test_graph_mismatch_missing_edge(self):
        self.entry("grill-me")["operative"] = []
        self.assert_errors("graph/body mismatch")

    def test_graph_mismatch_added_edge(self):
        self.entry("research")["operative"] = copy.deepcopy(self.entry("grill-me")["operative"])
        self.assert_errors("graph/body mismatch")

    def test_graph_cycle_refused(self):
        edge = copy.deepcopy(self.entry("tdd")["operative"][0])
        edge["target"], edge["provider_path"] = "tdd", checker.NATIVE["tdd"]
        self.entry("tdd")["operative"].append(edge)
        with self.assertRaisesRegex(checker.Invalid, "operative graph cycle"):
            checker.validate_registry(self.r)

    def test_graph_closure_missing_target(self):
        edge = self.entry("grill-me")["operative"][0]
        edge["target"] = "missing-target"
        with self.assertRaisesRegex(checker.Invalid, "graph target missing"):
            checker.validate_registry(self.r)

    def test_graph_user_only_target_refused(self):
        edge = self.entry("grill-me")["operative"][0]
        edge["target"], edge["provider_path"] = "grill-with-docs", checker.NATIVE["grill-with-docs"]
        with self.assertRaisesRegex(checker.Invalid, "model edge to user-only"):
            checker.validate_registry(self.r)

    def test_graph_evidence_line_mismatch(self):
        self.entry("grill-me")["operative"][0]["evidence_occurrences"][0]["line"] += 1
        self.assert_errors("graph evidence mismatch")

    def test_alias_cycles_refused(self):
        self.r["aliases"]["grill-me-with-docs"]["target"] = "setup-github-repository"
        self.r["aliases"]["setup-github-repository"]["target"] = "grill-me-with-docs"
        with self.assertRaisesRegex(checker.Invalid, "alias cycle"):
            checker.validate_registry(self.r)

    def test_alias_wrong_provider_refused(self):
        self.r["aliases"]["grill-me-with-docs"]["provider_path"] = checker.NATIVE["grill-me"]
        with self.assertRaisesRegex(checker.Invalid, "alias identity/path"):
            checker.validate_registry(self.r)

    def test_alias_wrapper_refused(self):
        path = self.root / "skills/local/grill-me-with-docs/SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\nname: grill-me-with-docs\ndescription: wrapper\n---\nCall grill-with-docs")
        self.refuse("alias cannot also be a wrapper", "grill-me-with-docs", invoker="user")

    def test_unapproved_caller_graph_refused(self):
        self.refuse("does not authorize", "pr", caller="grill-me")
        self.refuse("unregistered caller", "pr", caller="made-up-caller")

    def test_setup_model_pr_scope(self):
        self.assertEqual(checker.resolve(self.root, self.r, "pr", "model", "github-repository-setup"),
                         self.root / checker.NATIVE["pr"])

    def test_dynamic_notes_can_only_resolve_model_targets(self):
        self.assertEqual(checker.resolve(self.root, self.r, "pr", "model", "wayfinder"),
                         self.root / checker.NATIVE["pr"])
        self.refuse("user-only", "retro", caller="wayfinder")
        self.refuse("user-only", "wayfinder", caller="wayfinder")

    def test_symlink_resource_refused(self):
        path = self.root / "skills/engineering/domain-modeling/GLOSSARY-FORMAT.md"
        original = path.with_suffix(".saved")
        path.rename(original)
        path.symlink_to(original.name)
        self.assert_errors("symlink path refused")

    def test_unsafe_resource_path_refused(self):
        f = self.entry("research")["files"][0]
        f["path"] = "../escape"
        with self.assertRaises(checker.Invalid):
            checker.validate_registry(self.r)

    def test_prerequisite_and_suggestions_are_not_model_edges(self):
        self.assertEqual(self.entry("ask-matt")["operative"], [])
        self.assertIn("retro", self.entry("ask-matt")["router_suggestions"])
        self.assertIn("setup-matt-pocock-skills", self.entry("code-review")["human_prerequisites"])
        self.assertEqual(self.entry("handoff")["operative"], [])

    def test_registry_missing_owned_resource_refused(self):
        e = self.entry("prototype")
        e["resources"] = []
        with self.assertRaisesRegex(checker.Invalid, "resource inventory mismatch"):
            checker.validate_registry(self.r)

    def test_imported_provenance_missing_refused(self):
        e = self.entry("research")
        (self.root / e["source_path"] / ".vendor-owned.json").write_text('{"source":"mattpocock-research","paths":[""]}')
        self.assert_errors("missing file/resource")

    def add_provenance(self):
        for e in self.r["providers"]:
            base = self.root / e["source_path"]
            (base / "PROVENANCE.md").write_text(
                f"| Upstream path | `{e['source_path']}` |\n"
                f"| Pinned commit | [{checker.PIN}]({checker.REPO}/commit/{checker.PIN}) |\n"
                f"| Permalink | {checker.REPO}/tree/{checker.PIN}/{e['source_path']} |\n")
            license_path = SOURCE / "skills/engineering/research/LICENSE.upstream"
            license_bytes = (license_path if license_path.exists() else SOURCE / "LICENSE").read_bytes()
            prefix = (f"Vendored from {checker.REPO} at commit {checker.PIN}.\n"
                      f"Original licence text follows, unmodified.\n{'-' * 76}\n\n").encode()
            # Fixture input may be upstream or already imported. Normalize to the
            # original notice, then exercise the preface explicitly in its test.
            if license_bytes.startswith(prefix):
                license_bytes = license_bytes[len(prefix):]
            (base / "LICENSE.upstream").write_bytes(license_bytes)
            (base / "ATTRIBUTION.md").write_text(f"{checker.REPO} {checker.PIN}")
            (base / ".vendor-owned.json").write_text(json.dumps({"source": "mattpocock-" + e["name"], "paths": [""]}))

    def test_importer_source_paths_validated(self):
        self.add_provenance()
        self.assertEqual(checker.check(self.root, self.r), [])
        path = self.root / "skills/engineering/research/PROVENANCE.md"
        path.write_text(path.read_text().replace("`skills/engineering/research`", "`skills/research/research`"))
        self.assert_errors("provenance source path/pin mismatch")

    def test_importer_owner_source_validated(self):
        self.add_provenance()
        p = self.root / "skills/engineering/research/.vendor-owned.json"
        p.write_text('{"source":"matt-pocock-research","paths":[""]}')
        self.assert_errors("invalid importer ownership record")

    def test_importer_license_preface_supported(self):
        self.add_provenance()
        p = self.root / "skills/engineering/research/LICENSE.upstream"
        prefix = (f"Vendored from {checker.REPO} at commit {checker.PIN}.\n"
                  f"Original licence text follows, unmodified.\n{'-' * 76}\n\n")
        p.write_text(prefix + p.read_text())
        self.assertEqual(checker.check(self.root, self.r), [])

    def test_importer_license_notice_drift_refused(self):
        self.add_provenance()
        p = self.root / "skills/engineering/research/LICENSE.upstream"
        p.write_text(p.read_text() + "unreviewed change")
        self.assert_errors("upstream MIT notice/hash mismatch")

    def test_import_manifest_mapping_validated(self):
        self.add_provenance()
        sources = [dict(id="mattpocock-" + e["name"], repo=checker.REPO,
                        pinned_commit=checker.PIN, expected_commit=checker.PIN, ref="v1.3.1",
                        dest=e["source_path"], paths=[{"from": e["source_path"], "to": "", "kind": "skill"}])
                   for e in self.r["providers"]]
        path = self.root / "skills/vendor.manifest.json"
        path.write_text(json.dumps({"sources": sources}))
        self.assertEqual(checker.check(self.root, self.r), [])
        sources[0]["paths"][0]["from"] = "skills/engineering/research"
        path.write_text(json.dumps({"sources": sources}))
        self.assert_errors("import manifest source path/pin mismatch")

    def test_cli_root_and_exact_path(self):
        result = subprocess.run([sys.executable, str(BASE / "scripts/check_skill_dependencies.py"),
                                 "--root", str(self.root), "--resolve", "research",
                                 "--invoker", "model", "--caller", "wayfinder"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(self.root / checker.NATIVE["research"]))

    def test_cli_refusal_nonzero(self):
        result = subprocess.run([sys.executable, str(BASE / "scripts/check_skill_dependencies.py"),
                                 "--root", str(self.root), "--resolve", "implement-spec",
                                 "--invoker", "model"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("model invocation refused", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_static_check_read_only(self):
        before = {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(checker.check(self.root, self.r), [])
        checker.resolve(self.root, self.r, "grilling", "model", "grill-me")
        after = {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Dependencies)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"tests_run": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "successful": result.wasSuccessful(),
              "test_cases": unittest.defaultTestLoader.getTestCaseNames(Dependencies),
              "fixture_directory": "system temporary directories, automatically cleaned",
              "source_root": str(SOURCE), "local_root": str(LOCAL)}
    if os.environ.get("SKILL_DEPENDENCY_TEST_REPORT"):
        Path(os.environ["SKILL_DEPENDENCY_TEST_REPORT"]).write_text(json.dumps(report, indent=2) + "\n")
    sys.exit(not result.wasSuccessful())
