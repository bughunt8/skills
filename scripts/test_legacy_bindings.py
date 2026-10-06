#!/usr/bin/env python3
"""Isolated temp-fixture tests. No real repository writes or provider execution."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

import check_legacy_bindings as c


MODEL = "skills/engineering/skills/api-design-reviewer/SKILL.md"
AGENT = "skills/engineering/karpathy-coder/agents/karpathy-reviewer.md"
DOCUMENT = "skills/business-operations/CLAUDE.md"
USER = "skills/engineering/manual-review/SKILL.md"
PASSIVE = "skills/marketing-skill/skills/content-production/SKILL.md"
UNSET = object()


class BindingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="legacy-bindings-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write(MODEL, self.fm("api-design-reviewer"))
        self.write(c.GRILLING, self.fm("grilling"))
        self.write(c.DOMAIN, self.fm("domain-modeling"))
        self.write(USER, self.fm("manual-review", "disable-model-invocation: true\n"))
        self.write(AGENT, self.fm("karpathy-reviewer", "model: sonnet\n"))
        self.write(DOCUMENT, "# Contract\nOrdinary passive document.\n")
        self.write(PASSIVE, self.fm("content-production"))
        self.write_codex(c.GRILLING, True)
        for caller, skill in c.CONSUMERS.items():
            self.write(skill, self.fm(caller) +
                       "[workflow](references/workflow.md)\n"
                       "[forcing](references/forcing_questions.md)\n"
                       "[composition](references/composition_map.md)\n")
            base = str(Path(skill).parent)
            self.write(base + "/references/workflow.md",
                       "# Moved workflow\nImportant instructions retained.\n")
            self.write(base + "/references/forcing_questions.md",
                       "# Intake\nOne question per turn.\n")
            self.write(base + "/references/composition_map.md", self.map(caller))
        self.write(c.PM["command_path"], self.command())
        self.write(c.PM["provider_path"], self.fm("scrum-master"))
        self.write(c.PM["router_path"], self.router())
        self.registry = {"schema_version": 1, "providers": ["native-field-untouched"],
                         "legacy_bindings": c.build_records(self.root)}
        self.write(c.REGISTRY_PATH, json.dumps(self.registry))

    @staticmethod
    def fm(name, extra=""):
        return f"---\nname: {name}\ndescription: Fixture\n{extra}---\n\n# {name}\n"

    @staticmethod
    def router(path="project-management/skills/scrum-master"):
        return ("SIGNALS = {'SPRINT': {'skill': 'scrum-master', "
                f"'path': {path!r}, 'keywords': ['sprint', 'retrospective', 'action item']"
                "}, 'HEALTH': {'skill': 'senior-pm', 'path': "
                "'project-management/skills/senior-pm', 'keywords': ['portfolio']}}\n"
                "# This would be dangerous to import; the verifier only reads AST.\n"
                "raise RuntimeError('must never execute router')\n")

    @staticmethod
    def command():
        return ("---\ndescription: PM router\n---\n# /cs:pm\n"
                "pm-skills routes $ARGUMENTS through the exact script.\n"
                "```bash\npython3 skills/project-management/skills/pm-skills/"
                "scripts/pm_goal_router.py --repo-root . "
                '--text "$ARGUMENTS" --output json\n```\n')

    @staticmethod
    def map(caller):
        own = "cs-" + caller.removeprefix("senior-") + "-engineer"
        return (
            "# Composition\n"
            f"`{own}` is BLOCKED, absent. `cs-grill-master` is BLOCKED, absent.\n\n"
            "`cs-cto-advisor`, `cs-content-creator`, and `ra-qm-team` are BLOCKED. "
            "No single ra-qm-team entrypoint. Manual selection required.\n\n"
            "Explicit preflight [grilling](../../../../productivity/grilling/SKILL.md).\n"
            "Separate task after approval [domain-modeling]"
            "(../../../../engineering/domain-modeling/SKILL.md).\n"
            "| Review | [api-design-reviewer]"
            "(../../../../engineering/skills/api-design-reviewer/SKILL.md) |\n"
            "| Pre-commit | [karpathy-reviewer agent]"
            "(../../../../engineering/karpathy-coder/agents/karpathy-reviewer.md) |\n"
            "Independent human only [manual-review]"
            "(../../../../engineering/manual-review/SKILL.md).\n"
            "Ordinary human handoff, passive selection guidance only [successor]"
            "(../../../../marketing-skill/skills/content-production/SKILL.md).\n"
            "Passive read [contract](../../../../business-operations/CLAUDE.md).\n"
            "Read [forcing questions](forcing_questions.md).\n"
        )

    def write(self, path, text):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")

    def write_codex(self, skill, implicit):
        path = str(Path(skill).parent / "agents/openai.yaml")
        value = "true" if implicit else "false"
        self.write(path, "interface:\n  display_name: Fixture\n"
                   "  short_description: Fixture provider\npolicy:\n"
                   f"  allow_implicit_invocation: {value}\n")
        return path

    def update(self):
        self.registry["legacy_bindings"] = c.build_records(self.root)

    def consumer(self):
        return self.registry["legacy_bindings"]["consumers"][0]

    def route(self, path):
        return next(r for r in self.consumer()["routes"] if r["provider"]["path"] == path)

    def assertInvalid(self, registry=UNSET):
        errors = c.validate(self.root, self.registry if registry is UNSET else registry)
        self.assertTrue(errors, "unsafe or stale binding unexpectedly passed")
        return errors

    def test_positive_full_inventory_read_only_and_exact_resolution(self):
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.root.rglob("*") if p.is_file()}
        with patch("subprocess.run", side_effect=AssertionError("no execution")):
            self.assertEqual(c.validate(self.root, self.registry), [])
            self.assertEqual(c.build_records(self.root), self.registry["legacy_bindings"])
            for caller in c.CONSUMERS:
                for path in (MODEL, c.GRILLING, c.DOMAIN):
                    self.assertEqual(c.resolve_consumer(
                        self.root, self.registry, caller, path, "model"), path)
        after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(len(self.registry["legacy_bindings"]["consumers"]), 3)
        self.assertEqual(len(self.consumer()["routes"]), 8)
        self.assertEqual(len(self.consumer()["files"]), 4)
        self.assertEqual(c.read_registry(self.root), self.registry)

    def test_missing_central_field_and_malformed_type(self):
        for value in ({}, None, {"legacy_bindings": None}, {"legacy_bindings": []},
                      {"legacy_bindings": {1: {}, "wrong": {}}}):
            with self.subTest(value=value):
                self.assertInvalid(value)

    def test_removed_consumer_or_target_declaration(self):
        for removed in ("consumer", "route", "blocked", "file"):
            with self.subTest(removed=removed):
                registry = copy.deepcopy(self.registry)
                consumers = registry["legacy_bindings"]["consumers"]
                if removed == "consumer":
                    consumers.pop()
                else:
                    consumers[0][{"route": "routes", "blocked": "blocked",
                                  "file": "files"}[removed]].pop()
                self.assertInvalid(registry)

    def test_removed_map_route_even_with_forged_map_hash(self):
        path = self.consumer()["map_path"]
        old = (self.root / path).read_text()
        self.write(path, "\n".join(line for line in old.splitlines()
                                  if "api-design-reviewer" not in line))
        # Updating a hash alone cannot delete a registered route unnoticed.
        for f in self.consumer()["files"]:
            if f["path"] == path:
                f["sha256"] = c._file(self.root, path)["sha256"]
        self.assertInvalid()

    def test_extra_route_added_to_docs_requires_declaration(self):
        path = self.consumer()["map_path"]
        self.write("skills/engineering/new-review/SKILL.md", self.fm("new-review"))
        self.write(path, (self.root / path).read_text() +
                   "[new-review](../../../../engineering/new-review/SKILL.md)\n")
        self.assertInvalid()
        self.update()
        self.assertEqual(c.validate(self.root, self.registry), [])

    def test_every_link_including_resource_and_escalation_is_covered(self):
        for target in (DOCUMENT, AGENT, PASSIVE, MODEL):
            with self.subTest(target=target):
                file = self.root / target
                original = file.read_text()
                self.write(target, original + "\nChanged\n")
                self.assertInvalid()
                self.write(target, original)

    def test_moved_workflow_and_forcing_instruction_hash_drift(self):
        for f in self.consumer()["files"]:
            if f["path"].endswith(("workflow.md", "forcing_questions.md")):
                original = (self.root / f["path"]).read_text()
                self.write(f["path"], original + "Altered instruction\n")
                self.assertInvalid()
                self.write(f["path"], original)

    def test_duplicate_ids_and_phantom_alias(self):
        for key in ("consumers",):
            registry = copy.deepcopy(self.registry)
            registry["legacy_bindings"][key].append(copy.deepcopy(self.consumer()))
            self.assertInvalid(registry)
        self.consumer()["routes"].append(copy.deepcopy(self.route(MODEL)))
        self.assertInvalid()
        self.update()
        self.registry["legacy_bindings"]["aliases"] = {"cs-grill-master": c.GRILLING}
        self.assertInvalid()

    def test_forged_invocation_and_kind_fail_closed(self):
        for path, fields in ((USER, {"invocation": "model_or_user"}),
                             (AGENT, {"kind": "skill", "invocation": "model_or_user"}),
                             (DOCUMENT, {"kind": "skill"}),
                             (MODEL, {"canonical_name": "phantom-alias"}),
                             (MODEL, {"namespace": "matt"})):
            with self.subTest(path=path, fields=fields):
                self.update()
                self.route(path)["provider"].update(fields)
                self.route(path)["action"] = "declared_model_route"
                self.assertInvalid()

    def test_wrong_provider_path_namespace_and_identity(self):
        self.route(MODEL)["provider"]["path"] = c.PM["provider_path"]
        self.assertInvalid()
        self.update()
        self.write(MODEL, self.fm("scrum-master"))
        self.assertInvalid()
        with self.assertRaises(ValueError):
            c.build_records(self.root)

    def test_user_only_agent_resource_and_passive_never_skill_loaded(self):
        self.assertEqual(self.route(AGENT)["provider"]["kind"], "agent_definition")
        self.assertTrue(self.route(AGENT)["host_registration_required"])
        for target in (AGENT, USER, DOCUMENT, PASSIVE, "api-design-reviewer",
                       "cs-grill-master", "cs-backend-engineer"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                c.resolve_consumer(self.root, self.registry,
                                   "senior-backend", target, "model")
        for caller, invoker in (("senior-backend", "user"), ("phantom", "model")):
            with self.assertRaises(ValueError):
                c.resolve_consumer(self.root, self.registry, caller, MODEL, invoker)

    def test_ordinary_human_handoff_never_claims_runtime_closure(self):
        self.assertEqual(self.route(USER)["action"], "independent_human_handoff")
        self.assertEqual(self.route(PASSIVE)["action"], "manual_selection")
        self.assertFalse(self.consumer()["runtime_closure_claimed"])
        self.assertTrue(all(not r["runtime_closure_claimed"]
                            for r in self.consumer()["routes"]))
        self.consumer()["runtime_closure_claimed"] = True
        self.assertInvalid()

    def test_top_nested_flags_boolean_conflict_and_codex_disagreement(self):
        bad = [
            "disable-model-invocation: 'false'\n",
            "disable-model-invocation: false\nmetadata:\n"
            "  disable-model-invocation: true\n",
            "metadata: bad\n",
        ]
        for extra in bad:
            with self.subTest(extra=extra):
                self.write(MODEL, self.fm("api-design-reviewer", extra))
                self.assertInvalid()
        self.write(MODEL, self.fm("api-design-reviewer"))
        codex = self.write_codex(MODEL, False)
        self.assertInvalid()
        self.write(codex, "interface: []\npolicy: broken\n")
        self.assertInvalid()
        self.write(codex, "interface: {display_name: Test, short_description: Test}\n"
                   "policy: {allow_implicit_invocation: 'true'}\n")
        self.assertInvalid()

    def test_nested_user_only_metadata_positive(self):
        self.write(USER, self.fm("manual-review",
                                "metadata:\n  disable-model-invocation: true\n"))
        self.write_codex(USER, False)
        self.update()
        self.assertEqual(c.validate(self.root, self.registry), [])
        self.assertEqual(self.route(USER)["provider"]["invocation"], "user_only")
        with self.assertRaises(ValueError):
            c.resolve_consumer(self.root, self.registry, "senior-backend", USER, "model")

    def test_human_grill_wrapper_never_auto_invoked_even_from_user_senior(self):
        wrapper = "skills/productivity/grill-me/SKILL.md"
        self.write(wrapper, self.fm("grill-me", "disable-model-invocation: true\n"))
        path = self.consumer()["map_path"]
        self.write(path, (self.root / path).read_text() +
                   "Independent human [grill-me]"
                   "(../../../../productivity/grill-me/SKILL.md).\n")
        self.update()
        self.assertEqual(c.validate(self.root, self.registry), [])
        for invoker in ("model", "user"):
            with self.assertRaises(ValueError):
                c.resolve_consumer(self.root, self.registry,
                                   "senior-backend", wrapper, invoker)
        # Even forged frontmatter permitting model use cannot create a wrapper
        # edge from these consumers after a fresh proposed build.
        self.write(wrapper, self.fm("grill-me"))
        self.assertInvalid()
        with self.assertRaises(ValueError):
            c.build_records(self.root)

    def test_required_grilling_cannot_become_user_only_on_fresh_build(self):
        self.write(c.GRILLING, self.fm("grilling", "disable-model-invocation: true\n"))
        self.write_codex(c.GRILLING, False)
        self.assertInvalid()
        with self.assertRaises(ValueError):
            c.build_records(self.root)

    def test_codex_policy_hash_drift_and_malformed_yaml(self):
        path = str(Path(c.GRILLING).parent / "agents/openai.yaml")
        original = (self.root / path).read_text()
        self.write(path, original + "# drift\n")
        self.assertInvalid()
        for text in ("policy: [", "interface: {}\ninterface: {}\n",
                     "!!python/object/apply:os.system ['echo forbidden']\n"):
            with self.subTest(text=text):
                self.write(path, text)
                self.assertInvalid()

    def test_duplicate_or_malformed_frontmatter(self):
        for text in ("---\nname: bad\nname: bad\n---\n",
                     "---\nname: [\n---\n", "---\nname: api-design-reviewer\n",
                     "---\n[foo, bar]\n---\n"):
            with self.subTest(text=text):
                self.write(MODEL, text)
                self.assertInvalid()

    def test_missing_files_and_symlink_targets(self):
        file = self.root / DOCUMENT
        original = file.read_text()
        file.unlink()
        self.assertInvalid()
        self.write(DOCUMENT, original)
        file.unlink()
        file.symlink_to(self.root / MODEL)
        self.assertInvalid()

    def test_unsafe_registry_paths(self):
        for unsafe in ("/tmp/SKILL.md", "../skills/SKILL.md",
                       "skills/../skills/SKILL.md", "skills//foo/SKILL.md",
                       "skills\\foo\\SKILL.md", ".agents/skill-dependencies.json"):
            with self.subTest(path=unsafe):
                registry = copy.deepcopy(self.registry)
                registry["legacy_bindings"]["consumers"][0]["skill_path"] = unsafe
                self.assertInvalid(registry)
                with self.assertRaises(ValueError):
                    c.checked_path(self.root, unsafe)

    def test_unsafe_map_links(self):
        path = self.consumer()["map_path"]
        original = (self.root / path).read_text()
        for href in ("/tmp/SKILL.md", "../../../../../../etc/passwd",
                     "https://example.com/SKILL.md",
                     "%2e%2e/forcing_questions.md", "forcing_questions.md?evil=1",
                     "../../../../engineering/skills/", "a\\b.md"):
            with self.subTest(href=href):
                self.write(path, original + f"[target]({href})\n")
                self.assertInvalid()
        self.write(path, original + "[bad](forcing_questions.md \"title\")\n")
        self.assertInvalid()

    def test_reference_links_supported_and_missing_duplicate_ids_rejected(self):
        path = self.consumer()["map_path"]
        original = (self.root / path).read_text()
        self.write(path, original + "[contract again][contract]\n"
                   "[contract]: ../../../../business-operations/CLAUDE.md\n")
        self.update()
        self.assertEqual(c.validate(self.root, self.registry), [])
        self.write(path, original + "[contract again][missing]\n")
        self.assertInvalid()
        self.write(path, original + "[x]: forcing_questions.md\n"
                   "[x]: forcing_questions.md\n")
        self.assertInvalid()

    def test_missing_explicit_boundaries_and_fake_phantom_label(self):
        path = self.consumer()["map_path"]
        original = (self.root / path).read_text()
        self.write(path, original.replace("BLOCKED, absent", "registered"))
        self.assertInvalid()
        self.write(path, original + "[cs-grill-master]"
                   "(../../../../productivity/grilling/SKILL.md)\n")
        self.assertInvalid()
        self.write(path, original.replace("Separate task after approval", "Auto-call"))
        self.assertInvalid()

    def test_pm_exact_record_and_three_hashes(self):
        pm = self.registry["legacy_bindings"]["pm_retrospective"]
        # Independent literals catch accidental changes to the production
        # constants; this is not an assertion of runtime command execution.
        self.assertEqual({k: pm[k] for k in ("command", "arguments", "command_path",
                                            "provider_path", "router_path",
                                            "canonical_name", "namespace")}, {
            "command": "/cs:pm",
            "arguments": "sprint retrospective action items",
            "command_path": "skills/project-management/commands/cs-pm.md",
            "provider_path": "skills/project-management/skills/scrum-master/SKILL.md",
            "router_path": "skills/project-management/skills/pm-skills/scripts/pm_goal_router.py",
            "canonical_name": "scrum-master",
            "namespace": "project-management",
        })
        for key, value in c.PM.items():
            self.assertEqual(pm[key], value)
        self.assertEqual([f["path"] for f in pm["files"]],
                         [c.PM[k] for k in ("command_path", "provider_path", "router_path")])
        for field, value in (("namespace", "matt"), ("command", "/retro"),
                             ("provider_path", MODEL), ("invocation", "model"),
                             ("independent_human_command_required", False)):
            registry = copy.deepcopy(self.registry)
            registry["legacy_bindings"]["pm_retrospective"][field] = value
            self.assertInvalid(registry)

    def test_pm_actual_command_target_router_metadata_not_executed(self):
        path = c.PM["router_path"]
        self.write(path, self.router("engineering/retro"))
        self.assertInvalid()
        with self.assertRaises(ValueError):
            c.build_records(self.root)
        self.write(path, "SIGNALS = get_dynamic_signals()\n")
        self.assertInvalid()
        self.write(path, self.router())
        self.write(c.PM["command_path"], "---\ndescription: fake\n---\n# /retro\n")
        self.assertInvalid()

    def test_pm_missing_router_wrong_actual_identity_and_hash_drift(self):
        path = c.PM["router_path"]
        original = (self.root / path).read_text()
        self.write(path, original + "# changed\n")
        self.assertInvalid()
        self.write(path, original)
        self.write(c.PM["provider_path"], self.fm("retro"))
        self.assertInvalid()

    def test_pm_wrong_actual_command_argv_cannot_hide_in_correct_prose(self):
        for old, new in (
                ("# /cs:pm\n", "# /cs:pm-loop\n"),
                ("python3 skills/", "python3 "),
                ('--text "$ARGUMENTS"', '--text "unrelated inquiry"'),
                ("--repo-root .", "--repo-root /different"),
                ("--output json", "--output json; echo forbidden"),
                ("--output json", "--output json --output json"),
                ("```bash", "```text")):
            with self.subTest(replacement=new):
                self.write(c.PM["command_path"], self.command().replace(old, new))
                self.assertInvalid()
                with self.assertRaises(ValueError):
                    c.build_records(self.root)

    def test_agent_directory_cannot_masquerade_as_skill(self):
        phantom = "skills/engineering/agents/phantom/SKILL.md"
        self.write(phantom, self.fm("phantom"))
        with self.assertRaises(ValueError):
            c._provider(self.root, phantom)

    def test_central_registry_duplicate_json_and_no_fallback(self):
        self.write(c.REGISTRY_PATH, '{"legacy_bindings": {}, "legacy_bindings": {}}')
        with self.assertRaises(ValueError):
            c.read_registry(self.root)
        (self.root / c.REGISTRY_PATH).unlink()
        with self.assertRaises(ValueError):
            c.read_registry(self.root)


class ActualPostimageTests(unittest.TestCase):
    def test_bounded_actual_postimage_in_temp_root(self):
        """Copy only the three consumers and explicitly referenced targets.

        No native repository executable is invoked. CI checks the installed
        postimage; explicit roots also support candidate overlays.
        """
        source = Path(os.environ.get(
            "LEGACY_SOURCE_ROOT", str(Path(__file__).resolve().parents[1]))).resolve()
        overlay = Path(os.environ.get(
            "LEGACY_CONSUMER_OVERLAY_ROOT",
            str(source / "skills/engineering-team/skills"))).resolve()
        with tempfile.TemporaryDirectory(prefix="legacy-actual-postimage-") as td:
            root = Path(td)
            for name, skill in c.CONSUMERS.items():
                destination = root / Path(skill).parent
                shutil.copytree(overlay / name, destination)
                # Inspect links in the consumer documents, not entire provider
                # trees. Canonicalization is tested by build_records afterwards.
                for doc in destination.rglob("*.md"):
                    for href in re.findall(r"(?<!!)\[[^\]]+\]\(([^()\s]+)\)",
                                           doc.read_text(encoding="utf-8")):
                        if href.startswith("#"):
                            continue
                        canonical = (doc.parent / href.split("#", 1)[0]).resolve()
                        relative = canonical.relative_to(root)
                        if canonical.exists():
                            continue
                        src = source / relative
                        canonical.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, canonical)
                        metadata = src.parent / "agents/openai.yaml"
                        if src.name == "SKILL.md" and metadata.exists():
                            out = canonical.parent / "agents/openai.yaml"
                            out.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(metadata, out)
            for key in ("command_path", "provider_path", "router_path"):
                destination = root / c.PM[key]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / c.PM[key], destination)
            records = c.build_records(root)
            registry = {"legacy_bindings": records}
            self.assertEqual(c.validate(root, registry), [])
            providers = {r["provider"]["path"]: r["provider"]
                         for consumer in records["consumers"]
                         for r in consumer["routes"]}
            self.assertEqual(sum(p["kind"] == "agent_definition"
                                 for p in providers.values()), 4)
            for consumer in records["consumers"]:
                for path in (c.GRILLING, c.DOMAIN):
                    self.assertEqual(c.resolve_consumer(
                        root, registry, consumer["id"], path, "model"), path)
                self.assertTrue(all(any(f["path"].endswith("/" + name)
                                        for f in consumer["files"])
                                    for name in ("workflow.md", "forcing_questions.md")))
                for route in consumer["routes"]:
                    provider = route["provider"]
                    if provider.get("canonical_name") in ("content-creator",
                                                          "content-production"):
                        self.assertEqual(route["action"], "manual_selection")
                        with self.assertRaises(ValueError):
                            c.resolve_consumer(root, registry, consumer["id"],
                                               provider["path"], "model")
                    if provider.get("canonical_name") == "seo-audit":
                        self.assertEqual(route["condition"],
                                         "optional_installed_authorized_and_Q5_SEO_dependent")
            pm = records["pm_retrospective"]
            self.assertEqual(pm["command"], "/cs:pm")
            self.assertEqual(pm["provider_path"], c.PM["provider_path"])
            print("Actual postimage inventory:",
                  json.dumps({consumer["id"]: {
                      "consumer_files": len(consumer["files"]),
                      "map_link_occurrences": len(consumer["routes"]),
                      "blocked_declarations": len(consumer["blocked"])}
                      for consumer in records["consumers"]}, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
