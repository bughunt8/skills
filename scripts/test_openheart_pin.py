#!/usr/bin/env python3
"""Regression tests for immutable upstream commit pins. No network required."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "sync_vendor_openheart_pin", Path(__file__).with_name("sync_vendor.py")
)
vendor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vendor)


class OpenHeartPinTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="openheart-pin-tests-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.upstream = self.base / "upstream"
        self.upstream.mkdir()
        self.git("init", "-q", "-b", "main")
        (self.upstream / "LICENSE").write_text("MIT fixture licence\n", encoding="utf-8")
        (self.upstream / "payload").mkdir()
        (self.upstream / "payload" / "reference.txt").write_text("first revision\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "first fixture")
        self.first_sha = self.git("rev-parse", "HEAD")
        (self.upstream / "payload" / "reference.txt").write_text("second revision\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "second fixture")
        self.head_sha = self.git("rev-parse", "HEAD")

    def git(self, *args, cwd=None, check=True):
        result = subprocess.run(
            [
                "git",
                "-C",
                str(cwd or self.upstream),
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.test",
                *args,
            ],
            check=check,
            capture_output=True,
            text=True,
        )
        return result if not check else result.stdout.strip()

    def source(self, ref):
        return {
            "id": "fixture",
            "name": "Fixture",
            "repo": str(self.upstream),
            "ref": ref,
            "author": "Fixture author",
            "license": "MIT",
            "license_path": "LICENSE",
            "dest": "skills/fixture",
            "pinned_commit": self.first_sha,
            "pinned_at": vendor._dt.date.today().isoformat(),
            "paths": [{"from": "payload", "to": "source", "kind": vendor.SUPPORT}],
        }

    def test_full_sha_fetches_exact_detached_commit(self):
        with tempfile.TemporaryDirectory(prefix="immutable-fetch-") as raw:
            checkout, sha = vendor.fetch_upstream(self.source(self.first_sha), Path(raw))
            self.assertEqual(sha, self.first_sha)
            self.assertEqual((checkout / "payload" / "reference.txt").read_text(), "first revision\n")
            detached = self.git("symbolic-ref", "-q", "HEAD", cwd=checkout, check=False)
            self.assertNotEqual(detached.returncode, 0)

    def test_branch_fetch_keeps_clone_branch_behavior(self):
        with tempfile.TemporaryDirectory(prefix="branch-fetch-") as raw:
            checkout, sha = vendor.fetch_upstream(self.source("main"), Path(raw))
            self.assertEqual(sha, self.head_sha)
            self.assertEqual(self.git("symbolic-ref", "--short", "HEAD", cwd=checkout), "main")

    def test_immutable_cadence_text_is_only_rendered_for_sha_refs(self):
        immutable = self.source(self.first_sha)
        branch = self.source("main")
        immutable_provenance = vendor.provenance_text(
            immutable, "payload", self.base / "local", self.first_sha, "support files"
        )
        branch_provenance = vendor.provenance_text(
            branch, "payload", self.base / "local", self.first_sha, "support files"
        )
        immutable_attribution = vendor.attribution_text(immutable, self.first_sha, immutable["paths"])
        branch_attribution = vendor.attribution_text(branch, self.first_sha, branch["paths"])

        self.assertIn("Immutable commit; no automatic refresh", immutable_provenance)
        self.assertIn("immutable commit; no automatic refresh", immutable_attribution)
        self.assertNotIn("At least every two weeks", immutable_provenance)
        self.assertIn("At least every two weeks", branch_provenance)
        self.assertIn("run at least every two weeks", branch_attribution)
        self.assertNotIn("immutable commit; no automatic refresh", branch_attribution)

    def test_check_detects_generated_attribution_and_provenance_mutations(self):
        repo = self.base / "consumer"
        (repo / "skills").mkdir(parents=True)
        (repo / "docs").mkdir()
        (repo / "docs" / "third-party-inventory.json").write_text('{"legacy": []}\n')
        source = self.source(self.first_sha)
        manifest = {"schema": 2, "sources": [source]}
        (repo / "skills" / "vendor.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        saved = vendor.REPO_ROOT, vendor.MANIFEST_PATH, vendor.NOTICES_PATH, vendor.INVENTORY_PATH
        vendor.REPO_ROOT = repo
        vendor.MANIFEST_PATH = repo / "skills" / "vendor.manifest.json"
        vendor.NOTICES_PATH = repo / "THIRD_PARTY_NOTICES.md"
        vendor.INVENTORY_PATH = repo / "docs" / "third-party-inventory.json"
        self.addCleanup(self.restore_globals, saved)

        self.assertEqual(self.run_cli(["--sync", "--source", "fixture"])[0], 0)
        self.assertEqual(self.run_cli(["--check", "--source", "fixture"])[0], 0)

        attribution = repo / "skills" / "fixture" / "ATTRIBUTION.md"
        original_attribution = attribution.read_text(encoding="utf-8")
        attribution.write_text("changed generated attribution\n", encoding="utf-8")
        code, report = self.run_cli(["--check", "--source", "fixture", "--output", "json"])
        self.assertEqual(code, 1)
        self.assertIn("ATTRIBUTION.md (generated metadata)", report["sources"][0]["changed"])
        attribution.write_text(original_attribution, encoding="utf-8")

        provenance = repo / "skills" / "fixture" / "source" / "PROVENANCE.md"
        provenance.write_text("changed generated provenance\n", encoding="utf-8")
        code, report = self.run_cli(["--check", "--source", "fixture", "--output", "json"])
        self.assertEqual(code, 1)
        self.assertIn("source/PROVENANCE.md (generated metadata)", report["sources"][0]["changed"])

    @staticmethod
    def restore_globals(saved):
        vendor.REPO_ROOT, vendor.MANIFEST_PATH, vendor.NOTICES_PATH, vendor.INVENTORY_PATH = saved

    @staticmethod
    def run_cli(argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = vendor.main(argv)
        if err.getvalue():
            raise AssertionError(err.getvalue())
        if "--output" in argv:
            return code, json.loads(out.getvalue())
        return code, out.getvalue()


if __name__ == "__main__":
    unittest.main()
