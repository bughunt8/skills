"""Offline regression suite; writes only fixtures beneath HARNESS_TEST_TMPDIR."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/agent-harness/scripts"
sys.path.insert(0, str(SCRIPTS))
import provider_bindings as bindings
import harness_manifest_builder as builder
import loop_controller as controller


def assert_schema(test, value, node, schema):
    """Check the vocabulary used by this manifest schema, not arbitrary JSON Schema."""
    if "$ref" in node:
        node = schema["$defs"][node["$ref"].rsplit("/", 1)[1]]
    kinds = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool}
    if "type" in node:
        test.assertIs(type(value), kinds[node["type"]])
    if "const" in node:
        test.assertEqual(value, node["const"])
    if "enum" in node:
        test.assertIn(value, node["enum"])
    if "pattern" in node:
        test.assertRegex(value, node["pattern"])
    if "minimum" in node:
        test.assertGreaterEqual(value, node["minimum"])
    if "minItems" in node:
        test.assertGreaterEqual(len(value), node["minItems"])
    if "maxLength" in node:
        test.assertLessEqual(len(value), node["maxLength"])
    if isinstance(value, dict):
        test.assertTrue(set(node.get("required", [])) <= set(value))
        props = node.get("properties", {})
        if node.get("additionalProperties") is False:
            test.assertTrue(set(value) <= set(props))
        for key, child in value.items():
            if key in props:
                assert_schema(test, child, props[key], schema)
            elif isinstance(node.get("additionalProperties"), dict):
                assert_schema(test, child, node["additionalProperties"], schema)
    if isinstance(value, list) and "items" in node:
        for child in value:
            assert_schema(test, child, node["items"], schema)


class ProviderTests(unittest.TestCase):
    def setUp(self):
        fixture_dir = os.environ.get("HARNESS_TEST_TMPDIR")
        if os.environ.get("HARNESS_KEEP_TEST_FIXTURES") == "1":
            self.root = Path(tempfile.mkdtemp(dir=fixture_dir))
        else:
            temporary = tempfile.TemporaryDirectory(dir=fixture_dir)
            self.addCleanup(temporary.cleanup)
            self.root = Path(temporary.name)
        (self.root / "AGENTS.md").write_text("# Test checkout\n")
        (self.root / "skills/engineering").mkdir(parents=True)

    def provider(self, name="tdd", domain="engineering", prefix="", policy="",
                 codex=None, identity=None):
        path = self.root / "skills" / domain / prefix / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "SKILL.md").write_text(
            "---\nname: %s\ndescription: \"Audit payments service reliability budget tests.\"\n%s---\n"
            % (identity or name, policy))
        if codex is not None:
            (path / "agents").mkdir(exist_ok=True)
            (path / "agents/openai.yaml").write_text(codex)
        return path

    def manifest(self, domain="engineering"):
        return builder.build_manifest(self.root / "skills" / domain, self.root, timestamp=False)

    def write(self, name, obj):
        p = self.root / name
        p.write_text(json.dumps(obj))
        return p

    def cli(self, script, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *map(str, args)],
            cwd=self.root, capture_output=True, text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(self.root)})

    def compile(self, manifest=None, *extra):
        path = self.write("manifest.json", manifest or self.manifest())
        out = self.root / "plan.json"
        proc = self.cli("goal_compiler.py", "--goal",
                        "audit payments service reliability budget tests",
                        "--manifest", path, "--out", out, *extra)
        return proc, out

    def plan(self, provider=None):
        provider = provider or self.provider()
        rel = provider.relative_to(self.root).as_posix()
        binding = bindings.live_binding(self.root, rel)
        return {"schema": bindings.PLAN_SCHEMA, "goal": "test", "domain": "engineering",
                "tasks": [{"id": "T1", "skill": binding["name"], "skill_path": rel,
                           "provider_binding": binding, "objective": "test",
                           "verification": [{"cmd": "true", "kind": "smoke", "expect_exit": 0}],
                           "max_attempts": 3}], "loop": {"max_loop_iterations": 12}}

    def init(self, plan=None, filename="state.json"):
        plan = self.write("input-plan.json", plan or self.plan())
        state = self.root / filename
        proc = self.cli("loop_controller.py", "init", "--plan", plan, "--state", state)
        return proc, state

    def state_command(self, cmd, state, *args):
        return self.cli("loop_controller.py", cmd, "--state", state, *args)

    def test_yaml_quoted_commented_anchor_identity(self):
        for identity in ('"tdd" # comment', "'tdd'", "&provider tdd"):
            path = self.provider(identity=identity)
            binding = bindings.live_binding(self.root, path.relative_to(self.root).as_posix())
            self.assertEqual(binding["name"], "tdd")
        text = ('---\nidentity: &provider tdd\nname: *provider\n'
                'description: >-\n  Audit payments service\n  reliability budget tests.\n---\n')
        (path / "SKILL.md").write_text(text)
        self.assertEqual(self.manifest()["skills"][0]["name"], "tdd")

    def test_nested_false_and_absent_flags_are_model_allowed(self):
        for policy in ("", "metadata:\n  disable-model-invocation: false\n",
                       "disable-model-invocation: false\n"):
            p = self.provider(policy=policy)
            self.assertEqual(bindings.live_binding(
                self.root, p.relative_to(self.root).as_posix())["invocation"], "model_or_user")

    def test_top_and_nested_true_are_user_only(self):
        for policy in ("disable-model-invocation: true\n",
                       "metadata:\n  disable-model-invocation: true\n",
                       "disable-model-invocation: &disabled true\nmetadata:\n  disable-model-invocation: *disabled\n"):
            p = self.provider(policy=policy)
            self.assertEqual(bindings.live_binding(
                self.root, p.relative_to(self.root).as_posix())["invocation"], "user_only")

    def test_invalid_invocation_and_conflicts_fail_closed(self):
        for policy in ('disable-model-invocation: "true"\n',
                       "disable-model-invocation: null\n", "metadata: unknown\n",
                       "disable-model-invocation: false\nmetadata:\n  disable-model-invocation: true\n",
                       "disable-model-invocation: true\ndisable-model-invocation: false\n"):
            p = self.provider(policy=policy)
            with self.assertRaises(bindings.BindingError):
                bindings.live_binding(self.root, p.relative_to(self.root).as_posix())

    def test_codex_pair_disagreement_and_non_boolean(self):
        for policy, codex in [
            ("", "policy:\n  allow_implicit_invocation: false\n"),
            ("disable-model-invocation: true\n", "policy: {}\n"),
            ("", 'policy:\n  allow_implicit_invocation: "true"\n'),
            ("", "policy: unknown\n"),
        ]:
            p = self.provider(policy=policy, codex=codex)
            with self.assertRaises(bindings.BindingError):
                bindings.live_binding(self.root, p.relative_to(self.root).as_posix())

    def test_codex_consistent_pair_and_hash(self):
        p = self.provider(policy="disable-model-invocation: true\n",
                          codex="policy:\n  allow_implicit_invocation: false\n")
        b = bindings.live_binding(self.root, p.relative_to(self.root).as_posix())
        self.assertEqual(b["invocation"], "user_only")
        self.assertIn("codex_invocation_metadata", [f["role"] for f in b["files"]])

    def test_wrong_yaml_identity_refused(self):
        p = self.provider(identity='"other"')
        with self.assertRaisesRegex(bindings.BindingError, "identity"):
            bindings.live_binding(self.root, p.relative_to(self.root).as_posix())

    def test_malformed_description_refused_without_metadata_repair(self):
        p = self.provider()
        (p / "SKILL.md").write_text(
            "---\nname: tdd\ndescription: Audit payments: reliability tests.\n---\n")
        proc = self.cli("harness_manifest_builder.py", "--domain", "engineering", "--json")
        self.assertEqual(proc.returncode, 7, proc.stdout + proc.stderr)
        self.assertIn("mapping values are not allowed", proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_paths_traversal_absolute_rootless(self):
        self.provider()
        for rel in ("skills/../outside", "/etc/passwd", "skills//engineering",
                    "skills/./engineering/tdd", "skills\\engineering", "engineering/tdd"):
            with self.subTest(path=rel), self.assertRaises(bindings.BindingError):
                bindings.live_binding(self.root, rel)
        with self.assertRaises(bindings.BindingError):
            bindings.checkout_root(self.root / "skills")

    def test_symlink_file_directory_and_root(self):
        p = self.provider()
        (p / "link").symlink_to(p / "SKILL.md")
        with self.assertRaisesRegex(bindings.BindingError, "symlink"):
            self.manifest()
        other = self.root / "linked-checkout"
        other.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(bindings.BindingError):
            bindings.checkout_root(other)
        (self.root / "skills/engineering/linked-provider").symlink_to(p, target_is_directory=True)
        with self.assertRaises(bindings.BindingError):
            bindings.checked_path(self.root, "skills/engineering/linked-provider", directory=True)

    def test_exact_tool_reference_paths_and_hashes(self):
        p = self.provider()
        (p / "scripts").mkdir()
        (p / "scripts/check.py").write_text('print("help") # --sample\n')
        (p / "references").mkdir()
        (p / "references/rules.md").write_text("rules\n")
        sk = self.manifest()["skills"][0]
        self.assertEqual(sk["tools"][0]["script"], "skills/engineering/tdd/scripts/check.py")
        self.assertEqual(sk["references"], ["skills/engineering/tdd/references/rules.md"])
        self.assertEqual(sk["tools"][0]["sha256"], bindings.sha256(p / "scripts/check.py"))
        self.assertIn("python3 skills/", sk["tools"][0]["verification"][0]["cmd"])

    def test_live_body_tool_reference_and_codex_hash_drift(self):
        p = self.provider(codex="policy: {}\n")
        (p / "scripts").mkdir()
        (p / "scripts/check.py").write_text("print('ok')\n")
        (p / "references").mkdir()
        (p / "references/rules.md").write_text("rules\n")
        rel = p.relative_to(self.root).as_posix()
        for resource in ("SKILL.md", "scripts/check.py", "references/rules.md", "agents/openai.yaml"):
            b = bindings.live_binding(self.root, rel)
            f = p / resource
            f.write_text(f.read_text() + "\n# changed\n")
            with self.assertRaisesRegex(bindings.BindingError, "drift"):
                bindings.validate_binding(self.root, b)

    def test_missing_bound_resource_refused(self):
        p = self.provider()
        (p / "references").mkdir()
        f = p / "references/rules.md"
        f.write_text("rules")
        b = bindings.live_binding(self.root, p.relative_to(self.root).as_posix())
        # Move it away to simulate a missing file without deleting evidence.
        f.rename(self.root / "moved-rules.md")
        with self.assertRaises(bindings.BindingError):
            bindings.validate_binding(self.root, b)

    def test_missing_registered_resource_blocks_builder(self):
        p = self.provider()
        (self.root / ".agents").mkdir()
        self.write(".agents/skill-dependencies.json", {"providers": [{
            "path": "skills/engineering/tdd/SKILL.md", "name": "tdd",
            "invocation": "model_or_user", "files": [
                {"path": "skills/engineering/tdd/references/missing.md", "sha256": "0" * 64}]}]})
        with self.assertRaisesRegex(bindings.BindingError, "missing file/resource"):
            self.manifest()

    def test_model_compiler_allowed_and_persists_binding(self):
        self.provider(policy="metadata:\n  disable-model-invocation: false\n")
        proc, out = self.compile()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        task = json.loads(out.read_text())["tasks"][0]
        self.assertEqual(task["skill_path"], "skills/engineering/tdd")
        self.assertEqual(task["provider_binding"]["invocation"], "model_or_user")

    def test_compiler_human_top_match_no_fallback_no_output(self):
        self.provider(name="grill-me", policy="disable-model-invocation: true\n")
        # A model fallback scores less but remains eligible.
        p = self.provider(name="tdd")
        (p / "SKILL.md").write_text(
            '---\nname: tdd\ndescription: "Audit payments."\n---\n')
        proc, out = self.compile(None, "--max-tasks", "1")
        self.assertEqual(proc.returncode, 8, proc.stdout + proc.stderr)
        self.assertIn("HUMAN-COMMAND-REQUIRED", proc.stdout)
        self.assertFalse(out.exists())

    def test_compiler_human_refusal_preserves_existing_output(self):
        self.provider(policy="metadata:\n  disable-model-invocation: true\n")
        out = self.root / "plan.json"
        out.write_text("preserved user data")
        proc, _ = self.compile()
        self.assertEqual(proc.returncode, 8)
        self.assertEqual(out.read_text(), "preserved user data")

    def test_human_top_score_tie_outside_max_tasks_never_falls_through(self):
        self.provider(name="tdd")
        self.provider(name="wayfinder", policy="disable-model-invocation: true\n")
        proc, out = self.compile(None, "--max-tasks", 1)
        self.assertEqual(proc.returncode, 8, proc.stdout)
        self.assertFalse(out.exists())

    def test_runtime_user_only_and_forged_model_role_blocked(self):
        p = self.provider(policy="disable-model-invocation: true\n")
        plan = self.plan(p)
        proc, state = self.init(plan)
        self.assertEqual(proc.returncode, 7)
        self.assertIn("HUMAN-COMMAND-REQUIRED", proc.stdout)
        self.assertFalse(state.exists())
        plan["tasks"][0]["provider_binding"]["invocation"] = "model_or_user"
        proc, state = self.init(plan)
        self.assertEqual(proc.returncode, 7)
        self.assertIn("forged", proc.stdout)
        self.assertFalse(state.exists())

    def test_same_name_requires_and_accepts_exact_qualified_paths(self):
        self.provider(prefix="first")
        second = self.provider(prefix="second")
        proc, out = self.compile()
        self.assertEqual(proc.returncode, 7)
        self.assertIn("AMBIGUOUS", proc.stdout)
        self.assertFalse(out.exists())
        proc, out = self.compile(None, "--provider-path", second.relative_to(self.root).as_posix())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(out.read_text())["tasks"][0]["skill_path"],
                         "skills/engineering/second/tdd")

    def test_fresh_session_skill_path_persistence(self):
        proc, state = self.init()
        self.assertEqual(proc.returncode, 0, proc.stdout)
        proc = self.state_command("next", state)
        d = json.loads(proc.stdout)
        self.assertEqual(d["skill_path"], "skills/engineering/tdd")
        self.assertEqual(d["skill_file"], d["skill_path"] + "/SKILL.md")
        self.assertEqual(d["provider_binding"],
                         json.loads(state.read_text())["tasks"][0]["provider_binding"])

    def test_drift_refused_before_next_record_verify_close_without_state_change(self):
        p = self.provider()
        proc, state = self.init(self.plan(p))
        self.assertEqual(proc.returncode, 0)
        before = state.read_bytes()
        (p / "SKILL.md").write_text((p / "SKILL.md").read_text() + "\nchanged\n")
        for cmd, extra in [
            ("next", []), ("record", ["--task", "T1", "--phase", "execute", "--exit-code", "0"]),
            ("verify", ["--task", "T1"]), ("close", []), ("status", []),
        ]:
            proc = self.state_command(cmd, state, *extra)
            self.assertEqual(proc.returncode, 7, proc.stdout)
            self.assertEqual(state.read_bytes(), before)

    def test_drift_prevents_verification_subprocess_side_effect(self):
        p = self.provider()
        plan = self.plan(p)
        plan["tasks"][0]["verification"][0]["cmd"] = "touch should-not-run"
        _, state = self.init(plan)
        proc = self.state_command("record", state, "--task", "T1", "--phase", "execute", "--exit-code", 0)
        self.assertEqual(proc.returncode, 0)
        (p / "SKILL.md").write_text((p / "SKILL.md").read_text() + "\nchanged\n")
        proc = self.state_command("verify", state, "--task", "T1")
        self.assertEqual(proc.returncode, 7)
        self.assertFalse((self.root / "should-not-run").exists())

    def test_fake_state_role_or_task_path_refused(self):
        self.provider()
        _, state = self.init()
        obj = json.loads(state.read_text())
        for field, value in (("invocation", "user_only"), ("skill_path", "skills/engineering/fake")):
            forged = copy.deepcopy(obj)
            forged["tasks"][0]["provider_binding"][field] = value
            f = self.write("forged-state.json", forged)
            proc = self.state_command("next", f)
            self.assertEqual(proc.returncode, 7)
        obj["tasks"][0]["skill_path"] = "skills/engineering/fake"
        proc = self.state_command("next", self.write("wrong-task.json", obj))
        self.assertEqual(proc.returncode, 7)

    def test_legacy_manifest_plan_state_require_regeneration_not_reset(self):
        self.provider()
        m = self.manifest()
        m["schema"] = "agent-harness/manifest.v1"
        proc, out = self.compile(m)
        self.assertEqual(proc.returncode, 7)
        self.assertIn("regenerate", proc.stdout)
        self.assertFalse(out.exists())
        plan = self.plan()
        plan["schema"] = "agent-harness/plan.v1"
        proc, state = self.init(plan)
        self.assertEqual(proc.returncode, 7)
        self.assertFalse(state.exists())
        old = self.write("old-state.json", {"schema": "agent-harness/state.v1", "user": "keep"})
        before = old.read_bytes()
        proc = self.state_command("next", old)
        self.assertEqual(proc.returncode, 7)
        self.assertIn("never reset", proc.stdout)
        proc, _ = self.init(filename="old-state.json")
        self.assertEqual(proc.returncode, 7)
        self.assertEqual(old.read_bytes(), before)

    def test_new_schema_with_missing_binding_refused(self):
        plan = self.plan()
        del plan["tasks"][0]["provider_binding"]
        proc, state = self.init(plan)
        self.assertEqual(proc.returncode, 7)
        self.assertFalse(state.exists())
        obj = {"schema": bindings.STATE_SCHEMA, "tasks": plan["tasks"]}
        proc = self.state_command("next", self.write("bad-state.json", obj))
        self.assertEqual(proc.returncode, 7)

    def test_existing_verify_record_close_semantics(self):
        _, state = self.init()
        self.assertEqual(self.state_command("close", state).returncode, 4)
        self.assertEqual(self.state_command(
            "record", state, "--task", "T1", "--phase", "verify", "--exit-code", "0",
            "--evidence", "observed").returncode, 6)
        self.assertEqual(self.state_command(
            "record", state, "--task", "T1", "--phase", "execute", "--exit-code", "0").returncode, 0)
        self.assertEqual(self.state_command(
            "record", state, "--task", "T1", "--phase", "verify", "--exit-code", "0").returncode, 6)
        self.assertEqual(self.state_command("verify", state, "--task", "T1").returncode, 0)
        self.assertEqual(self.state_command("close", state).returncode, 0)
        self.assertEqual(json.loads(state.read_text())["tasks"][0]["status"], "verified")

    def test_builder_all_exact18_check_determinism_and_drift(self):
        for domain in bindings.TARGETS:
            self.provider(domain=domain)
        out = self.root / "skills/engineering/agent-harness/skills/agent-harness/assets/harnesses"
        proc = self.cli("harness_manifest_builder.py", "--all", "--out-dir", out, "--no-timestamp")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        files = sorted(out.glob("*.json"))
        self.assertEqual({p.stem for p in files}, set(bindings.TARGETS))
        before = {p.name: p.read_bytes() for p in files}
        proc = self.cli("harness_manifest_builder.py", "--check")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = self.cli("harness_manifest_builder.py", "--all", "--out-dir", out, "--no-timestamp")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(before, {p.name: p.read_bytes() for p in files})
        file = out / "engineering.json"
        file.write_text(file.read_text() + " ")
        proc = self.cli("harness_manifest_builder.py", "--check")
        self.assertEqual(proc.returncode, 7)
        self.assertIn("drift", proc.stderr)
        self.assertTrue(file.read_text().endswith(" "))

    def test_self_generated_assets_excluded_but_schema_hashed(self):
        p = self.root / "skills/engineering/agent-harness/skills/agent-harness"
        p.mkdir(parents=True)
        (p / "SKILL.md").write_text('---\nname: agent-harness\ndescription: "Test."\n---\n')
        (p / "assets/harnesses").mkdir(parents=True)
        (p / "assets/harness_manifest.schema.json").write_text("{}")
        (p / "assets/harnesses/engineering.json").write_text("generated")
        (p / "scripts").mkdir()
        (p / "scripts/provider_bindings.py").write_text("# internal module\n")
        b = bindings.live_binding(self.root, p.relative_to(self.root).as_posix())
        self.assertEqual(len(b["files"]), 3)
        manifest = self.manifest()
        sk = next(sk for sk in manifest["skills"] if sk["name"] == "agent-harness")
        self.assertEqual(sk["tools"], [])
        (p / "assets/harnesses/engineering.json").write_text("regenerated")
        bindings.validate_binding(self.root, b)
        (p / "assets/harness_manifest.schema.json").write_text('{"changed": true}')
        with self.assertRaises(bindings.BindingError):
            bindings.validate_binding(self.root, b)

    def test_inventory_schema(self):
        p = self.provider()
        (p / "scripts").mkdir()
        (p / "scripts/check.py").write_text("print('ok') # --sample\n")
        schema = json.loads((SCRIPTS.parent / "assets/harness_manifest.schema.json").read_text())
        assert_schema(self, self.manifest(), schema, schema)

    def test_cli_samples_and_help(self):
        schema = json.loads((SCRIPTS.parent / "assets/harness_manifest.schema.json").read_text())
        for script in ("harness_manifest_builder.py", "goal_compiler.py", "loop_controller.py"):
            proc = self.cli(script, "--help")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            proc = self.cli(script, "--sample")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            if script != "loop_controller.py":
                sample = json.loads(proc.stdout)
                self.assertIs(sample["example_only"], True)
                if script == "harness_manifest_builder.py":
                    assert_schema(self, sample, schema, schema)

    def test_vague_goal_refusal(self):
        self.provider()
        m = self.write("manifest.json", self.manifest())
        out = self.root / "vague-plan.json"
        proc = self.cli("goal_compiler.py", "--goal", "make it better",
                        "--manifest", m, "--out", out)
        self.assertEqual(proc.returncode, 3)
        self.assertIn("forcing_questions", proc.stdout)
        self.assertFalse(out.exists())

    def test_all_registered_human_only_providers_runtime_and_compiler_blocked(self):
        source = os.environ.get("HARNESS_SOURCE_ROOT")
        if not source:
            self.skipTest("set HARNESS_SOURCE_ROOT for all registered human-only providers")
        root = bindings.checkout_root(source)
        registry = json.loads((root / ".agents/skill-dependencies.json").read_text())
        human = [e for e in registry["providers"] if e["invocation"] == "user_only"]
        self.assertEqual(len(human), 16)
        manifests = {}
        for entry in human:
            rel = str(Path(entry["path"]).parent)
            b = bindings.live_binding(root, rel)
            with self.assertRaisesRegex(bindings.BindingError, "HUMAN-COMMAND-REQUIRED"):
                bindings.validate_binding(root, b, model=True)
            domain = rel.split("/")[1]
            if domain not in manifests:
                manifests[domain] = builder.build_manifest(root / "skills" / domain, root, timestamp=False)
            m = manifests[domain]
            sk = next(sk for sk in m["skills"] if sk["path"] == rel)
            f = self.write(entry["name"] + "-manifest.json", m)
            out = self.root / (entry["name"] + "-plan.json")
            proc = self.cli("goal_compiler.py", "--goal", sk["description"], "--manifest", f,
                            "--out", out, "--repo-root", root, "--provider-path", rel,
                            "--max-tasks", 1, "--min-score", 1)
            self.assertEqual(proc.returncode, 8, proc.stdout + proc.stderr)
            self.assertFalse(out.exists())

    def test_genuine_repository_model_and_user_only_providers(self):
        source = os.environ.get("HARNESS_SOURCE_ROOT")
        if not source:
            self.skipTest("set HARNESS_SOURCE_ROOT to exercise the read-only pristine checkout")
        root = bindings.checkout_root(source)
        model = bindings.live_binding(root, "skills/engineering/tdd")
        bindings.validate_binding(root, model, model=True)
        nested = bindings.live_binding(root, "skills/start-github-repo")
        self.assertEqual(nested["invocation"], "model_or_user")
        for rel in ("skills/productivity/grill-me", "skills/productivity/handoff"):
            b = bindings.live_binding(root, rel)
            with self.assertRaisesRegex(bindings.BindingError, "HUMAN-COMMAND-REQUIRED"):
                bindings.validate_binding(root, b, model=True)

    def test_genuine_repository_compiler_and_runtime_policy(self):
        source = os.environ.get("HARNESS_SOURCE_ROOT")
        if not source:
            self.skipTest("set HARNESS_SOURCE_ROOT for genuine provider CLI tests")
        root = bindings.checkout_root(source)
        manifest = builder.build_manifest(root / "skills/engineering", root, timestamp=False)
        f = self.write("genuine-engineering.json", manifest)
        out = self.root / "genuine-plan.json"
        proc = self.cli("goal_compiler.py", "--goal", "test driven development red green refactor",
                        "--manifest", f, "--out", out, "--repo-root", root,
                        "--provider-path", "skills/engineering/tdd", "--max-tasks", 1)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self.root / "genuine-state.json"
        proc = self.cli("loop_controller.py", "init", "--plan", out, "--state", state,
                        "--repo-root", root)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        manifest = builder.build_manifest(root / "skills/productivity", root, timestamp=False)
        f = self.write("genuine-productivity.json", manifest)
        for rel in ("skills/productivity/grill-me", "skills/productivity/handoff"):
            b = bindings.live_binding(root, rel)
            sk = next(s for s in manifest["skills"] if s["path"] == rel)
            blocked_out = self.root / (b["name"] + "-blocked-plan.json")
            proc = self.cli("goal_compiler.py", "--goal", sk["description"],
                            "--manifest", f, "--out", blocked_out, "--repo-root", root,
                            "--provider-path", rel, "--max-tasks", 1, "--min-score", 1)
            self.assertEqual(proc.returncode, 8, proc.stdout + proc.stderr)
            self.assertFalse(blocked_out.exists())
            forged_state = json.loads(state.read_text())
            task = forged_state["tasks"][0]
            task.update(skill=b["name"], skill_path=rel, provider_binding=b)
            fstate = self.write(b["name"] + "-forged-state.json", forged_state)
            before = fstate.read_bytes()
            for cmd, extra in [("next", []), ("close", []),
                               ("record", ["--task", "T1", "--phase", "execute", "--exit-code", "0"]),
                               ("verify", ["--task", "T1"])]:
                proc = self.state_command(cmd, fstate, "--repo-root", root, *extra)
                self.assertEqual(proc.returncode, 7, proc.stdout)
                self.assertIn("HUMAN-COMMAND-REQUIRED", proc.stdout)
                self.assertEqual(fstate.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
