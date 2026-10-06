#!/usr/bin/env python3
"""Local-only regression tests. Real temporary git repositories, no remote writes."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("sync_vendor_candidate", Path(__file__).with_name("sync_vendor.py"))
vendor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vendor)


class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="adoption-tests-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "repo"
        self.upstream = self.base / "upstream"
        self.upstream.mkdir()
        for sid in ("a", "b"):
            root = self.upstream / "published" / sid
            (root / "empty").mkdir(parents=True)
            (root / "SKILL.md").write_text(f"---\nname: {sid}\n---\nnew {sid}\n")
            (root / "run.sh").write_text("#!/bin/sh\nexit 0\n")
            (root / "run.sh").chmod(0o755)
        (self.upstream / "LICENSE").write_text("MIT fixture licence\n")
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-qm", "local fixture")
        self.sha = self.git("rev-parse", "HEAD")
        (self.repo / "skills").mkdir(parents=True)
        (self.repo / "docs" / "migrations" / "legacy").mkdir(parents=True)
        (self.repo / "docs" / "third-party-inventory.json").write_text('{"legacy":[]}\n')
        self.sources = []
        for sid in ("a", "b"):
            dest = self.repo / "skills" / sid
            (dest / "old-empty").mkdir(parents=True)
            (dest / ".git").mkdir()
            (dest / ".git" / "config").write_text("historical metadata\n")
            (dest / "SKILL.md").write_text(f"old skill {sid}\n")
            (dest / "PROVENANCE.md").write_text("old generated provenance\n")
            (dest / "local.txt").write_text("not upstream\n")
            (dest / "run.sh").write_text("#!/bin/sh\nold\n")
            (dest / "run.sh").chmod(0o751)
            (dest / "old-empty").chmod(0o711)
            dest.chmod(0o750)
            self.sources.append({
                "id": sid, "name": sid, "repo": str(self.upstream), "ref": "main",
                "author": "Test author", "license": "MIT", "license_path": "LICENSE",
                "dest": f"skills/{sid}", "expected_commit": self.sha,
                "paths": [{"from": f"published/{sid}", "to": "", "kind": vendor.SUPPORT}],
                "adoption": {"expected_tree_sha256": vendor.exact_tree_digest(dest),
                             "archive_path": f"docs/migrations/legacy/{sid}"},
            })
        self.manifest = {"sources": self.sources}
        self.write_manifest()
        self.saved = (vendor.REPO_ROOT, vendor.MANIFEST_PATH, vendor.NOTICES_PATH, vendor.INVENTORY_PATH)
        vendor.REPO_ROOT = self.repo
        vendor.MANIFEST_PATH = self.repo / "skills" / "vendor.manifest.json"
        vendor.NOTICES_PATH = self.repo / "THIRD_PARTY_NOTICES.md"
        vendor.INVENTORY_PATH = self.repo / "docs" / "third-party-inventory.json"
        self.addCleanup(self.restore_globals)

    def restore_globals(self):
        vendor.REPO_ROOT, vendor.MANIFEST_PATH, vendor.NOTICES_PATH, vendor.INVENTORY_PATH = self.saved

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.upstream), "-c", "user.name=Fixture",
                               "-c", "user.email=fixture@test", *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def write_manifest(self):
        (self.repo / "skills" / "vendor.manifest.json").write_text(json.dumps(self.manifest))

    def dest(self, sid="a"):
        return self.repo / "skills" / sid

    def archive(self, sid="a"):
        return self.repo / "docs" / "migrations" / "legacy" / sid

    def run_cli(self, argv=None):
        argv = argv or ["--sync", "--adopt-existing", "--source", "a"]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = vendor.main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def reject_unchanged(self, argv=None, text=None):
        self.write_manifest()
        before = vendor.exact_tree_digest(self.repo)
        code, out, err = self.run_cli(argv)
        self.assertEqual(code, 2, (out, err))
        self.assertEqual(vendor.exact_tree_digest(self.repo), before)
        if text:
            self.assertIn(text, err)
        return err

    def both(self):
        return ["--sync", "--adopt-existing", "--source", "a", "--source", "b"]

    def test_adopts_complete_old_tree_and_imports_native_root(self):
        expected = self.sources[0]["adoption"]["expected_tree_sha256"]
        code, out, err = self.run_cli()
        self.assertEqual(code, 0, err)
        self.assertEqual(vendor.exact_tree_digest(self.archive()), expected)
        self.assertEqual((self.archive() / "PROVENANCE.md").read_text(), "old generated provenance\n")
        self.assertTrue((self.archive() / ".git" / "config").exists())
        self.assertTrue((self.archive() / "old-empty").is_dir())
        self.assertEqual((self.archive() / "run.sh").stat().st_mode & 0o7777, 0o751)
        self.assertEqual(self.archive().stat().st_mode & 0o7777, 0o750)
        self.assertIn("new a", (self.dest() / "SKILL.md").read_text())
        self.assertFalse((self.dest() / "local.txt").exists())
        self.assertFalse((self.dest() / "a").exists())
        record = json.loads((self.dest() / vendor.OWNERSHIP_FILE).read_text())
        self.assertEqual(record["paths"], [""])
        self.assertEqual(record["source"], "a")
        manifest = json.loads(vendor.MANIFEST_PATH.read_text())
        self.assertEqual(manifest["sources"][0]["pinned_commit"], self.sha)
        self.assertEqual(self.run_cli(["--sync", "--source", "a"])[0], 0)
        self.assertEqual(vendor.exact_tree_digest(self.archive()), expected)

    def test_exact_digest_includes_generated_files_git_and_all_modes(self):
        root = self.dest()
        original = vendor.exact_tree_digest(root)
        old_normal = vendor.tree_digest(root)
        path = root / "PROVENANCE.md"
        saved = path.read_text()
        path.write_text("changed generated file\n")
        self.assertNotEqual(vendor.exact_tree_digest(root), original)
        self.assertEqual(vendor.tree_digest(root), old_normal)
        path.write_text(saved)
        record = root / vendor.OWNERSHIP_FILE
        record.write_text('{"paths":[]}\n')
        self.assertNotEqual(vendor.exact_tree_digest(root), original)
        self.assertEqual(vendor.tree_digest(root), old_normal)
        record.unlink()
        for path in (root, root / "old-empty", root / "run.sh"):
            with self.subTest(path=path.name):
                mode = path.stat().st_mode & 0o7777
                path.chmod(mode ^ 0o020)
                self.assertNotEqual(vendor.exact_tree_digest(root), original)
                path.chmod(mode)
        (root / "another-empty").mkdir()
        self.assertNotEqual(vendor.exact_tree_digest(root), original)
        (root / "another-empty").rmdir()
        (root / ".git" / "config").write_text("changed git metadata")
        self.assertNotEqual(vendor.exact_tree_digest(root), original)

    def test_exact_digest_deterministic(self):
        duplicate = self.base / "duplicate"
        shutil.copytree(self.dest(), duplicate)
        self.assertEqual(vendor.exact_tree_digest(duplicate), vendor.exact_tree_digest(self.dest()))

    def test_root_support_refresh_and_check_do_not_report_generated_metadata_drift(self):
        self.assertEqual(self.run_cli()[0], 0)
        # Existing importer renders attribution before first pinned_at is recorded.
        # Its first ordinary refresh records that date in attribution; it must
        # still report no upstream drift, and later refreshes must be stable.
        code, out, err = self.run_cli(["--sync", "--source", "a", "--output", "json"])
        self.assertEqual(code, 0, err)
        self.assertFalse(json.loads(out)["drift"])
        before = vendor.exact_tree_digest(self.dest())
        for argv in (["--check", "--source", "a", "--output", "json"],
                     ["--sync", "--source", "a", "--output", "json"],
                     ["--check", "--source", "a", "--output", "json"]):
            code, out, err = self.run_cli(argv)
            self.assertEqual(code, 0, err)
            report = json.loads(out)
            self.assertFalse(report["drift"], report)
            self.assertEqual(report["sources"][0]["changed"], [])
            self.assertEqual(report["sources"][0]["skills"], 0)
        self.assertEqual(vendor.exact_tree_digest(self.dest()), before)

    def test_drift_digest_ignores_only_root_generated_names(self):
        root = self.base / "digest-root"
        root.mkdir()
        initial = vendor.tree_digest(root)
        for name in vendor.GENERATED_ROOT_NAMES:
            (root / name).write_text("root importer metadata")
        self.assertEqual(vendor.tree_digest(root), initial)
        (root / "nested").mkdir()
        baseline = vendor.tree_digest(root)
        for name in vendor.GENERATED_ROOT_NAMES:
            path = root / "nested" / name
            path.write_text("legitimate upstream content")
            changed = vendor.tree_digest(root)
            self.assertNotEqual(changed, baseline)
            baseline = changed
            path.write_text("changed legitimate upstream content")
            self.assertNotEqual(vendor.tree_digest(root), baseline)
            baseline = vendor.tree_digest(root)

    def test_filtered_root_support_refresh_and_check_have_no_false_drift(self):
        self.sources[0]["paths"][0]["file_include"] = ["SKILL.md", "run.sh"]
        self.sources[1]["paths"][0].update({"from": "", "file_include": ["LICENSE"]})
        self.write_manifest()
        self.assertEqual(self.run_cli(self.both())[0], 0)
        self.assertFalse((self.dest() / "empty").exists())
        self.assertEqual(sorted(p.name for p in self.dest("b").iterdir()),
                         sorted(["LICENSE", "PROVENANCE.md", "LICENSE.upstream",
                                 "ATTRIBUTION.md", vendor.OWNERSHIP_FILE]))
        for mode in ("--check", "--sync", "--check"):
            code, out, err = self.run_cli([mode, "--source", "a", "--source", "b", "--output", "json"])
            self.assertEqual(code, 0, err)
            report = json.loads(out)
            self.assertFalse(report["drift"], report)
            self.assertTrue(all(s["changed"] == [] and s["skills"] == 0 for s in report["sources"]))

    def test_filtered_support_included_file_change_reports_drift(self):
        self.sources[0]["paths"][0]["file_include"] = ["SKILL.md"]
        self.write_manifest()
        self.assertEqual(self.run_cli()[0], 0)
        (self.upstream / "published" / "a" / "SKILL.md").write_text("included change\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "included content change")
        self.manifest = json.loads(vendor.MANIFEST_PATH.read_text())
        self.manifest["sources"][0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.write_manifest()
        before = vendor.exact_tree_digest(self.repo)
        code, out, err = self.run_cli(["--check", "--source", "a", "--output", "json"])
        self.assertEqual(code, 1, err)
        self.assertTrue(json.loads(out)["sources"][0]["changed"])
        self.assertEqual(vendor.exact_tree_digest(self.repo), before)
        self.assertEqual(self.run_cli(["--sync", "--source", "a"])[0], 0)
        self.assertEqual((self.dest() / "SKILL.md").read_text(), "included change\n")
        self.assertEqual(self.run_cli(["--check", "--source", "a"])[0], 0)

    def test_filtered_support_excluded_file_change_has_no_content_drift(self):
        self.sources[0]["paths"][0]["file_include"] = ["SKILL.md"]
        self.write_manifest()
        self.assertEqual(self.run_cli()[0], 0)
        (self.upstream / "published" / "a" / "run.sh").write_text("excluded change\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "excluded content change")
        self.manifest = json.loads(vendor.MANIFEST_PATH.read_text())
        self.manifest["sources"][0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.write_manifest()
        before = vendor.exact_tree_digest(self.repo)
        code, out, err = self.run_cli(["--check", "--source", "a", "--output", "json"])
        # A moved commit is still reported, but excluded bytes cause no tree drift.
        self.assertEqual(code, 1, err)
        result = json.loads(out)["sources"][0]
        self.assertTrue(result["commit_moved"])
        self.assertEqual(result["changed"], [])
        self.assertEqual(vendor.exact_tree_digest(self.repo), before)
        self.assertEqual(self.run_cli(["--sync", "--source", "a"])[0], 0)
        self.assertFalse((self.dest() / "run.sh").exists())
        self.assertEqual(self.run_cli(["--check", "--source", "a"])[0], 0)

    def test_empty_support_file_filter_has_no_false_drift(self):
        self.sources[0]["paths"][0]["file_include"] = []
        self.write_manifest()
        self.assertEqual(self.run_cli()[0], 0)
        self.assertFalse((self.dest() / "SKILL.md").exists())
        self.assertEqual(self.run_cli(["--check", "--source", "a"])[0], 0)

    def test_root_metadata_collisions_fail_before_any_archive_or_import(self):
        root = self.upstream / "published" / "b"
        for kind in (vendor.SKILL, vendor.SUPPORT):
            for name in sorted(vendor.GENERATED_ROOT_NAMES):
                with self.subTest(kind=kind, name=name):
                    path = root / name
                    path.write_text("legitimate upstream root content\n")
                    self.git("add", "-A")
                    self.git("commit", "-qm", f"root collision {kind} {name}")
                    sha = self.git("rev-parse", "HEAD")
                    for source in self.sources:
                        source["expected_commit"] = sha
                    self.sources[1]["paths"][0]["kind"] = kind
                    self.reject_unchanged(self.both(), "conflicts with generated metadata")
                    path.unlink()

    def test_filtered_selected_root_metadata_collision_is_preflighted(self):
        (self.upstream / "published" / "a" / "ATTRIBUTION.md").write_text("upstream credit\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "selected root metadata")
        self.sources[0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.sources[0]["paths"][0]["file_include"] = ["ATTRIBUTION.md"]
        self.reject_unchanged(text="conflicts with generated metadata")

    def test_filtered_reserved_root_directory_collision_is_preflighted(self):
        root = self.upstream / "published" / "a" / "PROVENANCE.md"
        root.mkdir()
        (root / "selected.txt").write_text("upstream directory content\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "reserved root directory")
        self.sources[0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.sources[0]["paths"][0]["file_include"] = ["*.txt"]
        self.reject_unchanged(text="conflicts with generated metadata")

    def test_filtered_excluded_root_metadata_is_allowed_and_nested_names_preserved(self):
        root = self.upstream / "published" / "a"
        (root / "nested").mkdir()
        for name in vendor.GENERATED_ROOT_NAMES:
            (root / name).write_text(f"excluded root {name}\n")
            (root / "nested" / name).write_text(f"legitimate nested {name}\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "excluded root metadata and included nested content")
        self.sources[0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.sources[0]["paths"][0]["file_include"] = ["SKILL.md", "nested/*"]
        self.write_manifest()
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(self.run_cli(["--check", "--source", "a"])[0], 0)
        for name in vendor.GENERATED_ROOT_NAMES:
            self.assertEqual((self.dest() / "nested" / name).read_text(), f"legitimate nested {name}\n")
        (self.dest() / "nested" / "ATTRIBUTION.md").write_text("changed nested content\n")
        code, out, err = self.run_cli(["--check", "--source", "a", "--output", "json"])
        self.assertEqual(code, 1, err)
        self.assertTrue(json.loads(out)["sources"][0]["changed"])

    def test_unfiltered_single_skill_preserves_and_hashes_nested_metadata_names(self):
        root = self.upstream / "published" / "a" / "nested"
        root.mkdir()
        for name in vendor.GENERATED_ROOT_NAMES:
            (root / name).write_text(f"legitimate nested {name}\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "nested content names")
        self.sources[0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.sources[0]["paths"][0]["kind"] = vendor.SKILL
        self.write_manifest()
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(self.run_cli(["--check", "--source", "a"])[0], 0)
        for name in vendor.GENERATED_ROOT_NAMES:
            self.assertEqual((self.dest() / "nested" / name).read_text(), f"legitimate nested {name}\n")
        (self.dest() / "nested" / "PROVENANCE.md").write_text("changed nested content\n")
        code, out, err = self.run_cli(["--check", "--source", "a", "--output", "json"])
        self.assertEqual(code, 1, err)
        self.assertTrue(json.loads(out)["sources"][0]["changed"])

    def test_nonempty_mapped_support_provenance_collision_is_preflighted(self):
        (self.upstream / "published" / "a" / "PROVENANCE.md").write_text("upstream provenance\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "mapped support provenance collision")
        self.sources[0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.sources[0]["paths"][0]["to"] = "source"
        self.reject_unchanged(text="conflicts with generated metadata")

    def test_nonempty_mapped_support_preserves_names_not_generated_there(self):
        root = self.upstream / "published" / "a"
        for name in vendor.GENERATED_ROOT_NAMES - {"PROVENANCE.md"}:
            (root / name).write_text(f"legitimate mapped content {name}\n")
        (root / "nested").mkdir()
        (root / "nested" / "PROVENANCE.md").write_text("legitimate nested provenance\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "legitimate mapped metadata names")
        self.sources[0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.sources[0]["paths"][0]["to"] = "source"
        self.write_manifest()
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(self.run_cli(["--check", "--source", "a"])[0], 0)
        for name in vendor.GENERATED_ROOT_NAMES - {"PROVENANCE.md"}:
            self.assertEqual((self.dest() / "source" / name).read_text(),
                             f"legitimate mapped content {name}\n")
        credit = self.dest() / "source" / "ATTRIBUTION.md"
        saved_credit = credit.read_text()
        credit.write_text("changed legitimate mapped credit\n")
        code, out, err = self.run_cli(["--check", "--source", "a", "--output", "json"])
        self.assertEqual(code, 1, err)
        self.assertTrue(json.loads(out)["sources"][0]["changed"])
        credit.write_text(saved_credit)
        path = self.dest() / "source" / "nested" / "PROVENANCE.md"
        self.assertEqual(path.read_text(), "legitimate nested provenance\n")
        path.write_text("changed nested provenance\n")
        code, out, err = self.run_cli(["--check", "--source", "a", "--output", "json"])
        self.assertEqual(code, 1, err)
        self.assertTrue(json.loads(out)["sources"][0]["changed"])

    def test_collection_child_provenance_collision_is_preflighted(self):
        (self.upstream / "published" / "b" / "PROVENANCE.md").write_text("upstream provenance\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "collection child provenance collision")
        self.sources[0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.sources[0]["paths"] = [{"from": "published", "to": "source",
                                    "kind": vendor.SKILL_COLLECTION, "include": ["a", "b"]}]
        self.reject_unchanged(text="collection child `b`")

    def test_collection_child_nested_provenance_is_preserved_and_hashed(self):
        root = self.upstream / "published" / "a" / "nested"
        root.mkdir()
        (root / "PROVENANCE.md").write_text("legitimate nested provenance\n")
        (root.parent / "ATTRIBUTION.md").write_text("legitimate child credit\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "collection nested provenance")
        self.sources[0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.sources[0]["paths"] = [{"from": "published", "to": "source",
                                    "kind": vendor.SKILL_COLLECTION, "include": ["a", "b"]}]
        self.write_manifest()
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(self.run_cli(["--check", "--source", "a"])[0], 0)
        credit = self.dest() / "source" / "a" / "ATTRIBUTION.md"
        self.assertEqual(credit.read_text(), "legitimate child credit\n")
        credit.write_text("changed legitimate child credit\n")
        code, out, err = self.run_cli(["--check", "--source", "a", "--output", "json"])
        self.assertEqual(code, 1, err)
        self.assertTrue(json.loads(out)["sources"][0]["changed"])
        credit.write_text("legitimate child credit\n")
        path = self.dest() / "source" / "a" / "nested" / "PROVENANCE.md"
        self.assertEqual(path.read_text(), "legitimate nested provenance\n")
        path.write_text("changed nested provenance\n")
        code, out, err = self.run_cli(["--check", "--source", "a", "--output", "json"])
        self.assertEqual(code, 1, err)
        self.assertTrue(json.loads(out)["sources"][0]["changed"])

    def test_exact_digest_rejects_links_and_special_files(self):
        root = self.base / "unsafe"
        root.mkdir()
        (root / "link").symlink_to(self.dest() / "SKILL.md")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            vendor.exact_tree_digest(root)
        (root / "link").unlink()
        os.mkfifo(root / "fifo")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            vendor.exact_tree_digest(root)

    def test_cli_requires_sync_and_explicit_source(self):
        for argv in (["--sync", "--adopt-existing"],
                     ["--check", "--source", "a", "--adopt-existing"],
                     ["--validate-manifest", "--source", "a", "--adopt-existing"],
                     ["--self-test", "--source", "a", "--adopt-existing"]):
            with self.subTest(argv=argv):
                self.reject_unchanged(argv, "requires --sync")

    def test_no_blanket_force_option(self):
        self.reject_unchanged(["--sync", "--source", "a", "--force"], "unrecognized arguments")

    def test_unknown_scope_does_not_partially_select(self):
        self.reject_unchanged(self.both() + ["--source", "typo"], "no manifest source")

    def test_normal_sync_refuses_missing_record_without_writes(self):
        self.reject_unchanged(["--sync", "--source", "a"], "ownership record")

    def test_normal_sync_refuses_later_missing_record_without_writes(self):
        shutil.rmtree(self.dest())
        self.reject_unchanged(["--sync", "--source", "a", "--source", "b"], "ownership record")
        self.assertFalse(self.dest().exists())

    def test_normal_and_adoption_refuse_corrupt_records(self):
        for record in ('{"paths": [', '{"paths":"bad"}', '{"paths":[7]}',
                       '{"source":"wrong","paths":[""]}'):
            for adopt in (False, True):
                with self.subTest(record=record, adopt=adopt):
                    (self.dest() / vendor.OWNERSHIP_FILE).write_text(record)
                    self.sources[0]["adoption"]["expected_tree_sha256"] = vendor.exact_tree_digest(self.dest())
                    argv = ["--sync", "--source", "a"] + (["--adopt-existing"] if adopt else [])
                    self.reject_unchanged(argv, "ownership record")

    def test_managed_destination_is_not_rebootstrapped(self):
        (self.dest() / vendor.OWNERSHIP_FILE).write_text('{"source":"a","paths":[""]}')
        self.sources[0]["adoption"]["expected_tree_sha256"] = vendor.exact_tree_digest(self.dest())
        self.reject_unchanged(text="already managed")

    def test_missing_adoption_metadata_in_later_source_is_global_preflight(self):
        del self.sources[1]["adoption"]
        self.reject_unchanged(self.both(), "adoption metadata")

    def test_missing_or_malformed_hash(self):
        for bad in (None, "", "1" * 63, "G" * 64, 12):
            with self.subTest(bad=bad):
                self.sources[0]["adoption"]["expected_tree_sha256"] = bad
                self.reject_unchanged(text="full lowercase SHA-256")

    def test_hash_mismatch_later_source_is_global_preflight(self):
        self.sources[1]["adoption"]["expected_tree_sha256"] = "0" * 64
        self.reject_unchanged(self.both(), "tree hash mismatch")

    def test_generated_file_change_prevents_adoption(self):
        (self.dest() / "PROVENANCE.md").write_text("changed since hash\n")
        self.reject_unchanged(text="tree hash mismatch")

    def test_mode_change_prevents_adoption(self):
        (self.dest() / "run.sh").chmod(0o750)
        self.reject_unchanged(text="tree hash mismatch")

    def test_empty_directory_change_prevents_adoption(self):
        (self.dest() / "new-empty").mkdir()
        self.reject_unchanged(text="tree hash mismatch")

    def test_existing_later_archive_never_overwritten(self):
        self.archive("b").mkdir()
        (self.archive("b") / "keep").write_text("existing backup")
        self.reject_unchanged(self.both(), "archive already exists")

    def test_archive_outside_migrations_and_path_escapes(self):
        for bad in ("docs/legacy/a", "docs/migrations", "../backup", "/tmp/backup",
                    "docs/migrations/../../skills/a", "C:\\backup"):
            with self.subTest(bad=bad):
                self.sources[0]["adoption"]["archive_path"] = bad
                self.reject_unchanged()

    def test_empty_and_missing_destinations_cannot_be_adopted(self):
        shutil.rmtree(self.dest())
        self.reject_unchanged(text="requires a populated")
        self.dest().mkdir()
        self.reject_unchanged(text="requires a populated")

    def test_destination_cannot_overlap_importer_metadata(self):
        self.sources[0]["dest"] = "skills"
        self.reject_unchanged(text="overlaps importer metadata")

    def test_notices_directory_is_global_preflight_failure(self):
        vendor.NOTICES_PATH.mkdir()
        self.reject_unchanged(text="notices is not a file")

    def test_overlapping_destinations(self):
        self.sources[1]["dest"] = "skills/a/nested"
        self.reject_unchanged(self.both(), "dest overlaps")

    def test_overlapping_archives(self):
        self.sources[1]["adoption"]["archive_path"] = "docs/migrations/legacy/a/nested"
        self.reject_unchanged(self.both(), "archive overlaps")

    def test_archive_overlaps_any_manifest_destination(self):
        self.sources[1]["dest"] = "docs/migrations/legacy/a/nested"
        self.reject_unchanged(text="archive overlaps")

    def test_archive_and_destination_symlink_components(self):
        for label in ("archive", "dest"):
            with self.subTest(label=label):
                external = self.base / f"external-{label}"
                external.mkdir()
                (external / "keep").write_text("external content\n")
                if label == "archive":
                    link = self.repo / "docs" / "migrations" / "linked"
                    self.sources[0]["adoption"]["archive_path"] = "docs/migrations/linked/a"
                else:
                    link = self.repo / "skills" / "linked"
                    self.sources[0]["dest"] = "skills/linked/a"
                link.symlink_to(external, target_is_directory=True)
                self.write_manifest()
                code, out, err = self.run_cli()
                self.assertEqual(code, 2, (out, err))
                self.assertIn("symlink component", err)
                self.assertEqual((external / "keep").read_text(), "external content\n")
                self.assertEqual(list(external.iterdir()), [external / "keep"])
                self.assertFalse(self.archive().exists())
                link.unlink()
                self.sources[0]["dest"] = "skills/a"
                self.sources[0]["adoption"]["archive_path"] = "docs/migrations/legacy/a"

    def test_source_tree_symlink_is_rejected(self):
        (self.dest() / "local-link").symlink_to(self.base / "missing")
        self.write_manifest()
        before = (self.dest() / "SKILL.md").read_bytes()
        code, _, err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("symlink", err)
        self.assertEqual((self.dest() / "SKILL.md").read_bytes(), before)
        self.assertTrue((self.dest() / "local-link").is_symlink())
        self.assertFalse(self.archive().exists())

    def test_symlink_in_upstream_mapping_ancestor_is_rejected(self):
        (self.upstream / "alias").symlink_to("published", target_is_directory=True)
        self.git("add", "alias")
        self.git("commit", "-qm", "unsafe alias")
        self.sources[0]["paths"][0]["from"] = "alias/a"
        self.sources[0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.reject_unchanged(text="symlink component")

    def test_upstream_tree_symlink_is_rejected(self):
        (self.upstream / "published" / "b" / "link").symlink_to("../../LICENSE")
        self.git("add", "-A")
        self.git("commit", "-qm", "unsafe tree")
        sha = self.git("rev-parse", "HEAD")
        for source in self.sources:
            source["expected_commit"] = sha
        self.reject_unchanged(self.both(), "contains a symlink")

    def test_fetched_commit_mismatch_later_cached_source_prevents_all_writes(self):
        self.sources[1]["expected_commit"] = "1" * 40
        with mock.patch.object(vendor, "fetch_upstream", wraps=vendor.fetch_upstream) as fetch:
            self.reject_unchanged(self.both(), "differs from fetched commit")
            self.assertEqual(fetch.call_count, 1)

    def test_normal_sync_expected_commit_mismatch_is_read_only(self):
        shutil.rmtree(self.dest())
        self.sources[0]["expected_commit"] = "1" * 40
        self.reject_unchanged(["--sync", "--source", "a"], "differs from fetched commit")

    def test_malformed_expected_commit(self):
        for bad in (None, "", "a" * 12, "A" * 40, 42):
            with self.subTest(bad=bad):
                self.sources[0]["expected_commit"] = bad
                self.reject_unchanged(text="expected_commit must")

    def test_expected_commit_is_optional(self):
        del self.sources[0]["expected_commit"]
        self.write_manifest()
        self.assertEqual(self.run_cli()[0], 0)

    def test_missing_later_mapping_is_global_preflight(self):
        self.sources[1]["paths"][0]["from"] = "does-not-exist"
        self.reject_unchanged(self.both(), "upstream path not found")

    def test_mapping_path_escape_is_rejected(self):
        self.sources[0]["paths"][0]["from"] = "../upstream"
        self.reject_unchanged(text="may not contain")

    def test_missing_later_license_is_global_preflight(self):
        self.sources[1]["license_path"] = "MISSING"
        self.reject_unchanged(self.both(), "license_path")

    def test_license_path_escape_is_rejected(self):
        self.sources[1]["license_path"] = "../outside"
        self.reject_unchanged(self.both(), "may not contain")

    def test_license_symlink_is_rejected(self):
        (self.upstream / "COPYING").symlink_to("LICENSE")
        self.git("add", "-A")
        self.git("commit", "-qm", "licence link")
        self.sources[0]["license_path"] = "COPYING"
        self.sources[0]["expected_commit"] = self.git("rev-parse", "HEAD")
        self.reject_unchanged(text="symlink component")

    def test_additional_license_paths_are_preflighted(self):
        for upstream, target in (("../outside", "COPYING"), ("MISSING", "COPYING"),
                                 ("LICENSE", "../outside"), ("LICENSE", vendor.OWNERSHIP_FILE)):
            with self.subTest(upstream=upstream, target=target):
                self.sources[1]["additional_licenses"] = [{
                    "upstream_license_file": upstream, "license_file": target,
                    "license": "MIT", "path": "*",
                }]
                self.reject_unchanged(self.both())

    def test_additional_nested_license_is_copied(self):
        self.sources[0]["additional_licenses"] = [{
            "upstream_license_file": "LICENSE", "license_file": "legal/OTHER-LICENSE",
            "license": "MIT", "path": "*",
        }]
        self.write_manifest()
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual((self.dest() / "legal" / "OTHER-LICENSE").read_text(), "MIT fixture licence\n")

    def test_ownership_record_path_escape_and_file_claim_are_refused(self):
        for owned in ("../escape", "SKILL.md"):
            with self.subTest(owned=owned):
                (self.dest() / vendor.OWNERSHIP_FILE).write_text(json.dumps({"paths": [owned]}))
                self.reject_unchanged(["--sync", "--source", "a"])

    def test_mandatory_missing_is_preflighted(self):
        self.sources[1]["mandatory"] = ["not-selected"]
        self.write_manifest()
        before = vendor.exact_tree_digest(self.repo)
        code, _, err = self.run_cli(self.both())
        self.assertEqual(code, 1, err)
        self.assertEqual(vendor.exact_tree_digest(self.repo), before)

    def test_bad_inventory_is_preflighted(self):
        vendor.INVENTORY_PATH.unlink()
        self.reject_unchanged(text="missing third-party inventory")

    def test_copy_failure_restores_original_and_removes_controlled_archive(self):
        before = vendor.exact_tree_digest(self.dest())
        def broken_copy(src, dst, **kwargs):
            (dst / "partial").write_text("partial copy")
            raise OSError("injected copy failure")
        with mock.patch.object(vendor.shutil, "copytree", side_effect=broken_copy):
            with self.assertRaisesRegex(OSError, "injected copy failure"):
                self.run_cli()
        self.assertEqual(vendor.exact_tree_digest(self.dest()), before)
        self.assertFalse(self.archive().exists())
        self.assertFalse(list(self.dest().parent.glob(".vendor-adoption-*")))

    def test_archive_verification_failure_preserves_original(self):
        before = vendor.exact_tree_digest(self.dest())
        real_copy = shutil.copytree
        def damaged_copy(src, dst, *args, **kwargs):
            result = real_copy(src, dst, *args, **kwargs)
            if Path(dst) == self.archive():
                (Path(dst) / "local.txt").write_text("damaged copy")
            return result
        with mock.patch.object(vendor.shutil, "copytree", side_effect=damaged_copy):
            code, _, err = self.run_cli()
        self.assertEqual(code, 2, err)
        self.assertIn("archive verification failed", err)
        self.assertEqual(vendor.exact_tree_digest(self.dest()), before)
        self.assertFalse(self.archive().exists())

    def test_import_failure_after_actual_writes_rolls_back(self):
        before = vendor.exact_tree_digest(self.dest())
        real_process = vendor.process_source
        def broken_import(source, checkout, sha, apply):
            result = real_process(source, checkout, sha, apply)
            if apply:
                raise OSError("injected import failure")
            return result
        with mock.patch.object(vendor, "process_source", side_effect=broken_import):
            with self.assertRaisesRegex(OSError, "injected import failure"):
                self.run_cli()
        self.assertEqual(vendor.exact_tree_digest(self.dest()), before)
        self.assertFalse((self.dest() / vendor.OWNERSHIP_FILE).exists())
        self.assertFalse(self.archive().exists())
        self.assertFalse(list(self.dest().parent.glob(".vendor-adoption-*")))

    def test_system_exit_during_import_rolls_back(self):
        before = vendor.exact_tree_digest(self.dest())
        def abort(source, checkout, sha, apply):
            self.dest().mkdir()
            (self.dest() / "partial").write_text("partial")
            raise SystemExit(2)
        with mock.patch.object(vendor, "process_source", side_effect=abort):
            self.assertEqual(self.run_cli()[0], 2)
        self.assertEqual(vendor.exact_tree_digest(self.dest()), before)
        self.assertFalse(self.archive().exists())

    def test_per_source_rollback_keeps_earlier_success(self):
        before_b = vendor.exact_tree_digest(self.dest("b"))
        old_a = vendor.exact_tree_digest(self.dest())
        real_process = vendor.process_source
        def fail_second(source, checkout, sha, apply):
            result = real_process(source, checkout, sha, apply)
            if apply and source["id"] == "b":
                raise OSError("second import failure")
            return result
        with mock.patch.object(vendor, "process_source", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "second import failure"):
                self.run_cli(self.both())
        self.assertEqual(vendor.exact_tree_digest(self.archive()), old_a)
        self.assertTrue((self.dest() / vendor.OWNERSHIP_FILE).is_file())
        self.assertEqual(vendor.exact_tree_digest(self.dest("b")), before_b)
        self.assertFalse(self.archive("b").exists())

    def test_same_repo_ref_clones_once_and_checkout_stays_unmodified(self):
        real_process = vendor.process_source
        digests = {}
        def observe_checkout(source, checkout, sha, apply):
            before = vendor.exact_tree_digest(checkout)
            digests[source["id"]] = (checkout, before)
            result = real_process(source, checkout, sha, apply)
            self.assertEqual(vendor.exact_tree_digest(checkout), before)
            return result
        with mock.patch.object(vendor, "fetch_upstream", wraps=vendor.fetch_upstream) as fetch:
            with mock.patch.object(vendor, "process_source", side_effect=observe_checkout):
                self.assertEqual(self.run_cli(self.both())[0], 0)
            self.assertEqual(fetch.call_count, 1)
        self.assertEqual(digests["a"], digests["b"])
        self.assertEqual(digests["a"][0].name, "a")

    def test_distinct_refs_fetch_separately(self):
        self.git("tag", "fixture-tag")
        self.sources[1]["ref"] = "fixture-tag"
        self.write_manifest()
        with mock.patch.object(vendor, "fetch_upstream", wraps=vendor.fetch_upstream) as fetch:
            self.assertEqual(self.run_cli(self.both())[0], 0)
            self.assertEqual(fetch.call_count, 2)

    def test_cache_is_per_invocation_not_persistent(self):
        self.write_manifest()
        with mock.patch.object(vendor, "fetch_upstream", wraps=vendor.fetch_upstream) as fetch:
            self.assertEqual(self.run_cli()[0], 0)
            self.assertEqual(self.run_cli(["--sync", "--source", "a"])[0], 0)
            self.assertEqual(fetch.call_count, 2)

    def test_readoption_cannot_replace_backup(self):
        self.assertEqual(self.run_cli()[0], 0)
        self.manifest = json.loads(vendor.MANIFEST_PATH.read_text())
        self.sources = self.manifest["sources"]
        self.reject_unchanged(text="already managed")

    def test_offline_validate_checks_recorded_expected_pin_without_fetch(self):
        self.assertEqual(self.run_cli()[0], 0)
        self.manifest = json.loads(vendor.MANIFEST_PATH.read_text())
        self.sources = self.manifest["sources"]
        self.sources[0]["expected_commit"] = "1" * 40
        self.write_manifest()
        before = vendor.exact_tree_digest(self.repo)
        # Restrict this fixture's manifest to the managed source for offline validation.
        manifest = copy.deepcopy(self.manifest)
        manifest["sources"] = manifest["sources"][:1]
        with mock.patch.object(vendor, "fetch_upstream", side_effect=AssertionError("no fetch")):
            problems = vendor.validate_manifest(manifest)
        self.assertTrue(any("recorded pinned_commit differs from expected_commit" in p for p in problems))
        self.assertEqual(vendor.exact_tree_digest(self.repo), before)

    def test_offline_validate_rejects_malformed_expected_pin(self):
        self.assertEqual(self.run_cli()[0], 0)
        manifest = json.loads(vendor.MANIFEST_PATH.read_text())
        manifest["sources"] = manifest["sources"][:1]
        manifest["sources"][0]["expected_commit"] = "short"
        self.assertTrue(any("expected_commit must" in p for p in vendor.validate_manifest(manifest)))

    def test_original_self_tests_unchanged(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vendor.self_test()
        self.assertEqual(code, 0, out.getvalue())
        self.assertEqual(out.getvalue().count("PASS  "), 13)

    def test_single_skill_root_import_reports_one_and_support_stays_zero(self):
        self.sources[0]["paths"][0]["kind"] = vendor.SKILL
        self.sources[0]["mandatory"] = ["a"]
        self.write_manifest()
        code, out, err = self.run_cli(self.both() + ["--output", "json"])
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual(report["sources"][0]["skills"], 1)
        self.assertEqual(report["sources"][0]["selected_directories"], 1)
        self.assertEqual(report["sources"][0]["missing_mandatory"], [])
        self.assertEqual(report["sources"][1]["skills"], 0)
        self.assertIn("| Content kind | skill |", (self.dest() / "PROVENANCE.md").read_text())
        self.assertTrue((self.dest() / "run.sh").exists())
        self.assertFalse((self.dest() / "a").exists())
        manifest = json.loads(vendor.MANIFEST_PATH.read_text())
        self.assertEqual(vendor.validate_manifest(manifest), [])

    def test_single_skill_requires_skill_file_in_global_preflight(self):
        self.sources[1]["paths"][0]["kind"] = vendor.SKILL
        self.git("rm", "-q", "published/b/SKILL.md")
        self.git("commit", "-qm", "missing skill")
        sha = self.git("rev-parse", "HEAD")
        for source in self.sources:
            source["expected_commit"] = sha
        self.reject_unchanged(self.both(), "single skill path has no SKILL.md")

    def test_single_skill_refuses_all_filter_fields(self):
        self.sources[0]["paths"][0]["kind"] = vendor.SKILL
        for key, value in (("include", ["*"]), ("exclude", []), ("file_include", None)):
            with self.subTest(key=key):
                self.sources[0]["paths"][0][key] = value
                self.reject_unchanged(text="complete tree without filters")
                del self.sources[0]["paths"][0][key]

    def test_single_skill_repo_root_name_is_cache_independent(self):
        (self.upstream / "SKILL.md").write_text("root skill\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "root skill")
        sha = self.git("rev-parse", "HEAD")
        for source in self.sources:
            source["expected_commit"] = sha
        self.sources[1]["paths"][0].update({"kind": vendor.SKILL, "from": ""})
        self.sources[1]["mandatory"] = ["upstream"]
        self.write_manifest()
        code, out, err = self.run_cli(self.both() + ["--output", "json"])
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["sources"][1]["skills"], 1)
        manifest = json.loads(vendor.MANIFEST_PATH.read_text())
        self.assertEqual(vendor.validate_manifest(manifest), [])

    def test_offline_single_skill_validation_requires_skill_file_and_provenance(self):
        self.sources[0]["paths"][0]["kind"] = vendor.SKILL
        self.sources[0]["mandatory"] = ["a"]
        self.write_manifest()
        self.assertEqual(self.run_cli()[0], 0)
        manifest = json.loads(vendor.MANIFEST_PATH.read_text())
        manifest["sources"] = manifest["sources"][:1]
        (self.dest() / "SKILL.md").unlink()
        (self.dest() / "PROVENANCE.md").unlink()
        problems = vendor.validate_manifest(manifest)
        self.assertTrue(any("has no SKILL.md" in p for p in problems))
        self.assertTrue(any("has no PROVENANCE.md" in p for p in problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
