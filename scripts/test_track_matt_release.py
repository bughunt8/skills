#!/usr/bin/env python3
"""Offline tests for the Matt release tracker. No network, no real repository writes."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import track_matt_release as tracker

REPO = "https://github.com/mattpocock/skills"
PIN = "1" * 40


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class TrackerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="matt-tracker-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.upstream = self.base / "upstream"
        self.root = self.base / "root"
        (self.upstream / "skills/engineering/a/agents").mkdir(parents=True)
        (self.upstream / "skills/productivity/b/agents").mkdir(parents=True)
        for sub in ("skills/engineering/a", "skills/productivity/b"):
            (self.upstream / sub / "SKILL.md").write_text(
                f"---\nname: {Path(sub).name}\ndescription: fixture provider\n---\nbody\n"
            )
            (self.upstream / sub / "agents/openai.yaml").write_text(
                'interface:\n  display_name: "Fixture"\n  short_description: "fixture"\n'
            )
        (self.upstream / "LICENSE").write_text("MIT fixture licence\n")
        (self.upstream / ".claude-plugin").mkdir()
        (self.upstream / ".claude-plugin/plugin.json").write_text('{"version": "9.9.9"}')
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture release")
        self.pin = self.git("rev-parse", "HEAD")
        for tag in ("v1.0.0", "v1.1.0", "v1.2.0"):
            self.git("tag", tag)

        (self.root / "skills").mkdir(parents=True)
        (self.root / ".agents").mkdir()
        files = []
        for sub in ("skills/engineering/a", "skills/productivity/b"):
            for name in ("SKILL.md", "agents/openai.yaml"):
                rel = f"{sub}/{name}"
                files.append(
                    {
                        "path": rel,
                        "source_path": rel,
                        "sha256": "0" * 64,
                        "source_url": f"{REPO}/blob/{PIN}/{rel}",
                    }
                )
        self.registry = {
            "schema_version": 1,
            "upstream_repository": REPO,
            "upstream_commit": PIN,
            "release": "1.0.0",
            "release_ref": "v1.0.0",
            "provider_count": 2,
            "file_count": 4,
            "operative_count": 1,
            "untracked_scopes": ["skills/misc"],
            "legal_resource": {
                "source_path": "LICENSE",
                "sha256": "0" * 64,
                "source_url": f"{REPO}/blob/{PIN}/LICENSE",
            },
            "providers": [
                {
                    "name": "a",
                    "source_path": "skills/engineering/a",
                    "path": "skills/engineering/a/SKILL.md",
                    "upstream_commit": PIN,
                    "source_url": f"{REPO}/blob/{PIN}/skills/engineering/a/SKILL.md",
                    "invocation": "model_or_user",
                    "files": files[:2],
                    "resources": [],
                    "operative": [
                        {
                            "target": "b",
                            "type": "operative_tool_call",
                            "condition": "fixture step",
                            "provider_path": "skills/productivity/b/SKILL.md",
                            "evidence_occurrences": [
                                {
                                    "line": 5,
                                    "text": "body",
                                    "source_url": f"{REPO}/blob/{PIN}/skills/engineering/a/SKILL.md#L5",
                                }
                            ],
                        }
                    ],
                    "human_prerequisites": [],
                },
                {
                    "name": "b",
                    "source_path": "skills/productivity/b",
                    "path": "skills/productivity/b/SKILL.md",
                    "upstream_commit": PIN,
                    "source_url": f"{REPO}/blob/{PIN}/skills/productivity/b/SKILL.md",
                    "invocation": "model_or_user",
                    "files": files[2:],
                    "resources": [],
                    "operative": [],
                    "human_prerequisites": [],
                },
            ],
            "auxiliary_providers": [],
            "aliases": {},
            "caller_scopes": {},
            "legacy_bindings": {},
        }
        self.manifest = {
            "sources": [
                {
                    "id": "mattpocock-a",
                    "repo": REPO,
                    "ref": "v1.0.0",
                    "pinned_commit": PIN,
                    "expected_commit": PIN,
                    "dest": "skills/engineering/a",
                    "homepage": f"{REPO}/tree/{PIN}/skills/engineering/a",
                    "paths": [{"from": "skills/engineering/a", "to": "", "kind": "skill"}],
                },
                {
                    "id": "mattpocock-b",
                    "repo": REPO,
                    "ref": "v1.0.0",
                    "pinned_commit": PIN,
                    "expected_commit": PIN,
                    "dest": "skills/productivity/b",
                    "homepage": f"{REPO}/tree/{PIN}/skills/productivity/b",
                    "paths": [{"from": "skills/productivity/b", "to": "", "kind": "skill"}],
                },
            ]
        }
        (self.root / "skills/vendor.manifest.json").write_text(json.dumps(self.manifest))
        (self.root / ".agents/skill-dependencies.json").write_text(json.dumps(self.registry))
        self.git_root("init", "-q")
        self.git_root("add", "-A")
        self.git_root("commit", "-qm", "fixture checkout")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.upstream), "-c", "user.name=Fixture",
             "-c", "user.email=fixture@test", *args],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    def git_root(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=Fixture",
             "-c", "user.email=fixture@test", *args],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    def proposal(self):
        return tracker.build_proposal(
            self.upstream, self.pin, "v1.2.0", str(self.upstream), self.root
        )

    def test_latest_tag_and_resolve(self):
        self.assertEqual(tracker.latest_tag(self.upstream), "v1.2.0")
        ref, commit = tracker.resolve_target(self.upstream, None)
        self.assertEqual((ref, commit), ("v1.2.0", self.pin))

    def test_build_proposal_updates_pin_and_hashes(self):
        proposal = self.proposal()
        self.assertEqual(proposal["registry"]["upstream_commit"], self.pin)
        self.assertEqual(proposal["registry"]["release_ref"], "v1.2.0")
        self.assertEqual(proposal["registry"]["release"], "9.9.9")
        self.assertEqual(proposal["registry"]["legal_resource"]["sha256"],
                         sha((self.upstream / "LICENSE").read_bytes()))
        for provider in proposal["registry"]["providers"]:
            for f in provider["files"]:
                self.assertEqual(
                    f["sha256"], sha((self.upstream / f["path"]).read_bytes())
                )
                self.assertIn(f"{REPO}/blob/{self.pin}/", f["source_url"])
        for source in proposal["manifest"]["sources"]:
            self.assertEqual(source["ref"], "v1.2.0")
            self.assertEqual(source["pinned_commit"], self.pin)
            self.assertEqual(source["fetch_repo"], str(self.upstream))
            self.assertIn(f"{REPO}/tree/{self.pin}/", source["homepage"])

    def test_provider_set_change_is_refused(self):
        new = self.upstream / "skills/engineering/new"
        new.mkdir(parents=True)
        (new / "SKILL.md").write_text("---\nname: new\ndescription: new\n---\n")
        with self.assertRaisesRegex(tracker.Refusal, "provider set changed"):
            self.proposal()

    def test_untracked_scope_is_ignored(self):
        new = self.upstream / "skills/misc/experimental"
        new.mkdir(parents=True)
        (new / "SKILL.md").write_text("---\nname: experimental\ndescription: new\n---\n")
        proposal = self.proposal()
        self.assertEqual(proposal["registry"]["provider_count"], 2)

    def test_graph_evidence_change_is_refused(self):
        path = self.upstream / "skills/engineering/a/SKILL.md"
        path.write_text(path.read_text().replace("body", "changed body"))
        with self.assertRaisesRegex(tracker.Refusal, "graph evidence changed"):
            self.proposal()

    def test_graph_evidence_line_shift_is_relocated(self):
        path = self.upstream / "skills/engineering/a/SKILL.md"
        path.write_text(path.read_text().replace("\nbody\n", "\n\nbody\n"))
        proposal = self.proposal()
        evidence = proposal["registry"]["providers"][0]["operative"][0][
            "evidence_occurrences"
        ][0]
        self.assertEqual(evidence["line"], 6)
        self.assertIn("#L6", evidence["source_url"])

    def test_new_scope_is_refused(self):
        new = self.upstream / "skills/design/new"
        new.mkdir(parents=True)
        (new / "SKILL.md").write_text("---\nname: new\ndescription: new\n---\n")
        with self.assertRaisesRegex(tracker.Refusal, "new upstream scope"):
            self.proposal()

    def test_invocation_change_is_refused(self):
        path = self.upstream / "skills/engineering/a/SKILL.md"
        path.write_text(
            "---\nname: a\ndescription: fixture\ndisable-model-invocation: true\n---\n"
        )
        with self.assertRaisesRegex(tracker.Refusal, "invocation policy changed"):
            self.proposal()

    def test_temporary_clone_checks_out_the_resolved_tag(self):
        (self.upstream / "NEW.md").write_text("later\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "later")
        later = self.git("rev-parse", "HEAD")
        self.assertNotEqual(later, self.pin)
        upstream, _transport, cleanup, temporary = tracker.upstream_tree(
            None, str(self.upstream)
        )
        try:
            _ref, commit = tracker.resolve_target(upstream, "v1.2.0")
            self.assertEqual(commit, self.pin)
            tracker.prepare_upstream(upstream, commit, temporary)
            head = subprocess.run(
                ["git", "-C", str(upstream), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            self.assertEqual(head, self.pin)
        finally:
            cleanup()

    def test_caller_directory_must_match_the_resolved_commit(self):
        (self.upstream / "NEW.md").write_text("later\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "later")
        with self.assertRaisesRegex(tracker.Refusal, "upstream directory is at"):
            tracker.prepare_upstream(self.upstream, self.pin, False)

    def test_symlink_provider_is_refused(self):
        skill = self.upstream / "skills/engineering/a/SKILL.md"
        real = self.upstream / "fixture-skill.md"
        real.write_text(skill.read_text())
        skill.unlink()
        skill.symlink_to(real)
        with self.assertRaisesRegex(tracker.Refusal, "symlink"):
            self.proposal()

    def test_write_refuses_a_dirty_tree(self):
        (self.root / "scratch.txt").write_text("uncommitted\n")
        with self.assertRaisesRegex(tracker.Refusal, "working tree is not clean"):
            tracker.run_write(self.root, str(self.upstream), None, "v1.2.0")

    def test_missing_license_is_refused(self):
        (self.upstream / "LICENSE").unlink()
        with self.assertRaisesRegex(tracker.Refusal, "no LICENSE"):
            self.proposal()

    def test_library_size_updates_three_literals_and_drops_communities(self):
        (self.root / "site/tests").mkdir(parents=True)
        (self.root / "site/data.js").write_text(
            'window.SKILLDATA={"total": 10, "categories": 2, "solutions": 3, '
            '"agreement": {"communities": 4}};'
        )
        (self.root / "site/tests/library-size.mjs").write_text(
            "export const EXPECTED_TOTAL = 1;\n"
            "export const EXPECTED_CATEGORIES = 1;\n"
            "export const EXPECTED_COMMUNITIES = 1;\n"
            "export const EXPECTED_SOLUTIONS = 1;\n"
        )
        tracker._update_library_size(self.root)
        text = (self.root / "site/tests/library-size.mjs").read_text()
        self.assertIn("EXPECTED_TOTAL = 10", text)
        self.assertIn("EXPECTED_CATEGORIES = 2", text)
        self.assertIn("EXPECTED_SOLUTIONS = 3", text)
        self.assertNotIn("EXPECTED_COMMUNITIES", text)

    def test_docs_update_pins_not_historical_versions(self):
        proposal = self.proposal()
        (self.root / ".agents/skill-dependencies.json").write_text(
            json.dumps(proposal["registry"])
        )
        for relative in tracker.CURRENT_DOCS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f"old {PIN}. See [the v1.0.0 guide](docs/matt-pocock-v1.0.0.md), 1 stable.\n"
            )
        doc = self.root / tracker.TRACKING_DOC
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(
            "<!-- BEGIN MATT RELEASE -->\nold\n<!-- END MATT RELEASE -->\n"
        )
        tracker._update_docs(
            self.root, proposal, old=(PIN, "v1.0.0", 1)
        )
        for relative in tracker.CURRENT_DOCS:
            text = (self.root / relative).read_text()
            self.assertIn(self.pin, text)
            self.assertNotIn(PIN, text)
            self.assertIn("[the v1.0.0 guide](docs/matt-pocock-v1.0.0.md)", text)
            self.assertIn("2 stable", text)
        updated = doc.read_text()
        self.assertIn("v1.2.0", updated)
        self.assertIn(self.pin, updated)
        self.assertIn("| Providers | 2 |", updated)

    def test_workflow_contract(self):
        text = (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/sync-matt-release.yml"
        ).read_text()
        for required in (
            "base: staging",
            "track_matt_release.py --check",
            "track_matt_release.py --write",
            "scripts/check_skill_dependencies.py --include-legacy",
            "site/build.py --check",
            "npx playwright test",
        ):
            self.assertIn(required, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
