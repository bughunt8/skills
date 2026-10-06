"""PM route qualification tests; no provider, command or MCP invocation."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import check_legacy_bindings as legacy

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/project-management/skills/pm-skills/scripts/pm_goal_router.py"


class PMProviderBinding(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="pm-binding-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/check_skill_dependencies.py",
                        self.root / "scripts/check_skill_dependencies.py")
        shutil.copyfile(ROOT / "scripts/check_legacy_bindings.py",
                        self.root / "scripts/check_legacy_bindings.py")
        self.router = self.root / SCRIPT.relative_to(ROOT)
        self.router.parent.mkdir(parents=True)
        shutil.copyfile(SCRIPT, self.router)
        command = self.root / legacy.PM["command_path"]
        command.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / legacy.PM["command_path"], command)
        self.provider = self.root / "skills/project-management/skills/scrum-master/SKILL.md"
        self.provider.parent.mkdir(parents=True)
        self.provider.write_text('---\nname: scrum-master\ndescription: "Sprint workflow"\n---\n')
        (self.root / ".agents").mkdir()
        self.registry = self.root / ".agents/skill-dependencies.json"
        self.registry.write_text(json.dumps({
            "legacy_bindings": {"pm_retrospective": legacy._pm_record(self.root)}}))

    def route(self, root=None, text="sprint retrospective action items", script=None):
        script = script or (self.router if root == self.root else SCRIPT)
        args = [sys.executable, "-B", str(script), "--text", text]
        if root is not None:
            args += ["--repo-root", str(root)]
        result = subprocess.run(args, capture_output=True, text=True)
        return result, json.loads(result.stdout)

    def test_actual_repository_route_is_pm_not_matt(self):
        result, data = self.route(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data["route_to"], "scrum-master")
        self.assertTrue(data["binding_verified"])
        self.assertFalse(data["execution_allowed"])
        self.assertEqual(Path(data["qualified_provider_path"]),
                         ROOT / "skills/project-management/skills/scrum-master/SKILL.md")

    def test_no_root_is_unqualified_and_grants_no_authority(self):
        result, data = self.route()
        self.assertEqual(result.returncode, 0)
        self.assertFalse(data["binding_verified"])
        self.assertFalse(data["execution_allowed"])
        self.assertNotIn("qualified_provider_path", data)

    def test_missing_provider_blocks(self):
        self.provider.unlink()
        result, data = self.route(self.root)
        self.assertEqual(result.returncode, 4)
        self.assertEqual(data["decision"], "BLOCKED_PROVIDER")

    def test_wrong_identity_blocks(self):
        self.provider.write_text('---\nname: retro\ndescription: "Wrong namespace"\n---\n')
        result, data = self.route(self.root)
        self.assertEqual(result.returncode, 4)
        self.assertIn("identity", data["error"])

    def test_human_only_provider_blocks(self):
        self.provider.write_text('---\nname: scrum-master\ndescription: "Sprint"\n'
                                 'disable-model-invocation: true\n---\n')
        result, data = self.route(self.root)
        self.assertEqual(result.returncode, 4)
        self.assertIn("user-only", data["error"])

    def test_broken_yaml_blocks_without_traceback(self):
        self.provider.write_text('---\nname: scrum-master\ndescription: [unterminated\n---\n')
        result, data = self.route(self.root)
        self.assertEqual(result.returncode, 4)
        self.assertIn("malformed YAML", data["error"])
        self.assertNotIn("Traceback", result.stderr)

    def test_symlinked_provider_blocks(self):
        real = self.root / "outside.md"
        self.provider.rename(real)
        self.provider.symlink_to(real)
        result, data = self.route(self.root)
        self.assertEqual(result.returncode, 4)
        self.assertIn("symlink", data["error"])

    def test_caller_text_does_not_execute_shell(self):
        marker = self.root / "unexpected-write"
        result, data = self.route(
            self.root, f"sprint retrospective action items; touch {marker}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertFalse(data["execution_allowed"])

    def test_foreign_root_is_refused_before_code_import(self):
        marker = self.root / "foreign-code-executed"
        (self.root / "scripts/check_skill_dependencies.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n")
        result, data = self.route(self.root, script=SCRIPT)
        self.assertEqual(result.returncode, 4)
        self.assertIn("own trusted checkout", data["error"])
        self.assertFalse(marker.exists())

    def test_dangling_codex_symlink_is_refused(self):
        client = self.provider.parent / "agents/openai.yaml"
        client.parent.mkdir()
        client.symlink_to(self.root / "missing-client-policy")
        result, data = self.route(self.root)
        self.assertEqual(result.returncode, 4)
        self.assertIn("symlink", data["error"])

    def test_provider_hash_drift_is_refused(self):
        self.provider.write_text(self.provider.read_text() + "Changed instructions\n")
        result, data = self.route(self.root)
        self.assertEqual(result.returncode, 4)
        self.assertIn("stale", data["error"])

    def test_dangling_codex_directory_is_refused(self):
        (self.provider.parent / "agents").symlink_to(self.root / "missing-client-directory")
        result, data = self.route(self.root)
        self.assertEqual(result.returncode, 4)
        self.assertIn("symlink", data["error"])


if __name__ == "__main__":
    unittest.main()
