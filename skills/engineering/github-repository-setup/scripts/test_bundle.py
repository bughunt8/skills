"""Static package regression checks; not a live setup/integration test."""
import pathlib
import re
import sys
import subprocess
import unittest

import yaml

ROOT = (pathlib.Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1
        else pathlib.Path(__file__).resolve().parents[1])


def governance_errors(files):
    """Inspect complete instruction postimage; mutations stay in memory."""
    joined = " ".join(" ".join(text.split()) for text in files.values())
    errors = []
    forbidden = (
        r"run the installed `setup-matt-pocock-skills` first",
        r"(?:Call|call) the Skill tool with [`\"]setup-matt-pocock-skills",
        r"(?:Call|call) (?:the )?(?:runtime's )?(?:native )?Skill loader with [`\"]setup-matt-pocock-skills",
        r"\.agent/invocation\.md",
        r"\.agents/GRAMMAR\.md",
        r"(?:Create|create|Generate|generate) (?:a )?(?:root )?`?GRAMMAR\.md",
        r"root `CONTEXT\.md`",
        r"`CONTEXT-MAP\.md` mapping domains",
        r"skip tests for production",
        r"no tests for (?:normal|production) implementation",
    )
    for pattern in forbidden:
        if re.search(pattern, joined):
            errors.append(f"forbidden regression: {pattern}")
    required = {
        "SKILL.md": ("Never auto-call", "approved native templates"),
        "references/matt-governance.md": (
            "not a hard dependency", "All five seeds exist in v1.3.1",
            "old and new authorities coexist", "stop for the user's canonical-source choice",
            "Do not bulk-rename unrelated CONTEXT files",
            "Tests may be skipped only within that approved throwaway scope",
            "Normal implementation still requires TDD",
            "A prototype is not a production substitute",
            "no automatic local/global", "one approved integration branch",
            "ready frontier", "integrated SHA", "never automatic setup execution",
            "Preserve unfinished work", "exact destructive or publication action",
            "grill-me-with-docs", "do not rename the vendor",
        ),
        "templates/invocation.md": (
            ".agents/invocation.md", ".agents/skill-dependencies.json",
            "one skill name per call", "explicit human command",
            "it alone neither grants nor enforces permissions",
            "REPLACE_WITH_CHECKED_BEHAVIOR_OR_GAP",
        ),
        "templates/agent-docs.md": (
            "root `GLOSSARY.md`", "`GLOSSARY-MAP.md`",
            "existing values", "No automatic commits",
        ),
        "templates/pull-request.md": (
            "## Summary", "## Evidence", "## Merge Danger",
            "Before", "After", "Door", "Blast Radius",
            "## Acceptance and traceability", "Refs", "default-branch",
        ),
    }
    for path, phrases in required.items():
        normalized = " ".join(files.get(path, "").split())
        for phrase in phrases:
            if phrase not in normalized:
                errors.append(f"{path}: missing {phrase}")
    governance = files.get("references/matt-governance.md", "")
    for name in ("pr", "implement-spec", "retro", "prototype", "grill-me",
                 "grill-with-docs", "grilling", "domain-modeling", "tdd",
                 "code-review", "writing-for-agents", "codebase-design", "research"):
        if f"`{name}`" not in governance:
            errors.append(f"missing entry point/dependency: {name}")
    return errors


class SetupSkillPackage(unittest.TestCase):
    def text(self, name):
        return (ROOT / name).read_text()

    def test_frontmatter_and_routing_budget(self):
        text = self.text("SKILL.md")
        frontmatter = yaml.safe_load(text.split("---", 2)[1])
        self.assertEqual(frontmatter["name"], ROOT.name)
        self.assertIs(frontmatter["disable-model-invocation"], True)
        self.assertNotIn("disable-model-invocation", frontmatter.get("metadata", {}))
        self.assertEqual(frontmatter["argument-hint"],
                         "[plan | checklist | agentic | preset | search query]")
        policy = yaml.safe_load(self.text("agents/openai.yaml"))
        self.assertIs(policy["policy"]["allow_implicit_invocation"], False)
        self.assertLessEqual(len(frontmatter["description"].split()), 50)
        self.assertLessEqual(len(text), 4000)
        for wording in ("setup-github-repository", "agentic", "Issues", "PRs"):
            self.assertIn(wording, text)

    def test_all_local_markdown_links(self):
        count = 0
        for path in ROOT.rglob("*.md"):
            for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)\s]+)\)", path.read_text()):
                if target.startswith(("https://", "http://", "#")):
                    continue
                count += 1
                self.assertTrue((path.parent / target.split("#")[0]).exists(),
                                f"{path}: {target}")
        self.assertGreater(count, 10)

    def test_hub_routes_every_runtime_resource(self):
        # Progressive disclosure: every resource must be reachable from the hub.
        visited = set()
        pending = [ROOT / "SKILL.md"]
        while pending:
            path = pending.pop().resolve()
            if path in visited:
                continue
            visited.add(path)
            if path.suffix != ".md":
                continue
            for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", path.read_text()):
                if not target.startswith(("https://", "http://", "#")):
                    pending.append(path.parent / target.split("#")[0])
        for directory in ("references", "templates"):
            for path in (ROOT / directory).iterdir():
                self.assertIn(path.resolve(), visited, str(path))

    def test_architecture_register_behavior(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/test_architecture_register.py")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_original_attribution_and_license(self):
        self.assertIn("Damir Omelic", self.text("ATTRIBUTION.md"))
        self.assertIn("MIT License", self.text("LICENSE"))
        catalog = self.text("references/catalog-setup.md")
        for section in ("Search mode", "Checklist mode", "Retrieve and review templates"):
            self.assertIn(section, catalog)

    def test_issue_form_schema(self):
        form = yaml.safe_load(self.text("templates/agent-task.yml"))
        self.assertIsInstance(form["name"], str)
        self.assertIsInstance(form["description"], str)
        ids = [item["id"] for item in form["body"] if "id" in item]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn("ready-for-agent", form.get("labels", []))
        fields = {item["id"]: item for item in form["body"] if "id" in item}
        for key in ("goal", "traceability", "scope", "relationships",
                    "acceptance", "verification", "risk", "handoff"):
            self.assertTrue(fields[key]["validations"]["required"], key)
        for item in form["body"]:
            self.assertIn(item["type"], ("markdown", "textarea", "dropdown"))
            self.assertIsInstance(item["attributes"], dict)

    def test_document_and_adm_contract(self):
        text = self.text("references/document-contract.md")
        for name in ("PRD.md", "TRD.md", "TDD.md", "TOGAF-ADM.md", "DESIGN.md",
                     "DESIGN-SYSTEM.md", "UI-UX.md", "WIREFRAME.md", "AGENTS.md",
                     "Agent.md", "Agent-Protocol.md"):
            self.assertIn(name, text)
        for phase in ("Preliminary", "A:", "B:", "C:", "D:", "E:", "F:", "G:",
                      "H:", "Requirements Management"):
            self.assertIn(phase, text)
        for level in ("Epic", "Feature", "Story"):
            self.assertIn(level, text)

    def test_safety_and_lifecycle_contract(self):
        text = " ".join((self.text("references/agentic-development.md")
                         + self.text("SKILL.md")).split())
        for phrase in ("not an atomic lock", "default-branch",
                       "must not", "self-merge", "Plane",
                       "AGENTS.md", "does not use Claude",
                       "preserve", "staging"):
            self.assertIn(phrase.lower(), text.lower())
        self.assertNotIn("existing `CLAUDE.md` first", text)

    def test_protocol_and_no_claude_scaffolding(self):
        text = " ".join(self.text("templates/agent-docs.md").split())
        self.assertIn("## Agent.md", text)
        self.assertIn("## Agent-Protocol.md", text)
        self.assertIn("do not create circular pointers", text)
        self.assertIn("Do not create CLAUDE.md or Claude.md", text)
        for path in ROOT.rglob("*"):
            self.assertNotEqual(path.name.lower(), "claude.md")
        self.assertIn("Triage labels subsection if `triage` is absent", text)

    def test_codegraph_contract(self):
        text = self.text("references/codegraph.md")
        for phrase in ("EXACT_VERSION", "--print-config", "codegraph init",
                       "codegraph status", "codegraph sync", "exclude",
                       "worktree", "pending", "full", "MCP", "no-Claude"):
            self.assertIn(phrase, text)
        self.assertIn("snippets returned over", text)

    def test_tooling_and_grilling_contract(self):
        text = self.text("references/tooling.md")
        for phrase in ("LSP", "GitHub MCP", "Penpot", "userToken", "grilling",
                       "decision frontier", "no-Claude/no-Plane",
                       "to-spec", "draft first", "GLOSSARY.md"):
            self.assertIn(phrase, text)
        self.assertIn("not an MCP server", text)

    def test_complex_setup_is_plan_first(self):
        text = " ".join(self.text("references/planning.md").split())
        for phrase in ("REPOSITORY-PLAN.md", "stop and request approval",
                       "Do not", "install tools", "create live backlog",
                       "Final target tree", "authorized phases"):
            self.assertIn(phrase, text)

    def test_repository_structure_baseline(self):
        text = " ".join(self.text("references/repository-structure.md").split())
        for item in (".editorconfig", ".gitattributes", ".gitignore", ".env.example",
                     "CONTRIBUTING.md", "SECURITY.md", "CODEOWNERS", "CHANGELOG.md",
                     "dependabot.yml", "getting-started/", "guides/", "reference/",
                     "runbooks/", "config.yml", "generated", "not applicable"):
            self.assertIn(item, text)
        self.assertIn("Existing equivalent files satisfy", text)
        self.assertIn("No placeholder URLs", text)

    def test_template_adoption_safety(self):
        text = " ".join(self.text("references/repository-structure.md").split())
        for rule in ("disabled by default", "continue-on-error", "read-only checks",
                     "not a security boundary", "does not auto-commit",
                     "do not generate npm, pnpm and Yarn locks",
                     "never replace authorship", "synthetic detector fixtures",
                     "does not vendor"):
            self.assertIn(rule.lower(), text.lower())

    def test_repository_plan_template(self):
        text = " ".join(self.text("templates/repository-plan.md").split())
        for item in ("Status: draft", "Final target structure", "Phased setup",
                     "Epic", "Feature", "Story", "TOGAF", "TDD", "UI-UX.md",
                     "Agent-Protocol.md", "CodeGraph", "Penpot", "Rollback",
                     "Secret", "Approval record", "stop here", "delta approval"):
            self.assertIn(item.lower(), text.lower())
        self.assertIn("no CLAUDE.md/Claude.md".lower(), text.lower())
        self.assertIn("No Plane.so", text)

    def instruction_files(self):
        return {str(path.relative_to(ROOT)): path.read_text()
                for path in ROOT.rglob("*.md")}

    def test_v131_governance_complete_postimage(self):
        self.assertEqual(governance_errors(self.instruction_files()), [])
        for path in ROOT.rglob("*"):
            self.assertNotEqual(path.name, "GRAMMAR.md")
            self.assertNotEqual(path.name, ".agent")

    def test_governance_negative_fixtures(self):
        originals = self.instruction_files()
        cases = (
            ("SKILL.md", "Never auto-call",
             "run the installed `setup-matt-pocock-skills` first"),
            ("SKILL.md", "Never auto-call",
             'Call the native Skill loader with "setup-matt-pocock-skills"'),
            ("templates/invocation.md", ".agents/invocation.md", ".agent/invocation.md"),
            ("templates/invocation.md", ".agents/invocation.md", ".agents/GRAMMAR.md"),
            ("templates/invocation.md", ".agents/invocation.md", "Create GRAMMAR.md"),
            ("templates/agent-docs.md", "root `GLOSSARY.md`", "root `CONTEXT.md`"),
            ("references/matt-governance.md",
             "Tests may be skipped only within that approved throwaway scope",
             "skip tests for production"),
            ("references/matt-governance.md", "not a hard dependency",
             "running setup-matt is mandatory even with existing config"),
            ("references/matt-governance.md", "`implement-spec`", "`missing-command`"),
            ("references/matt-governance.md", "`pr`", "`missing-command`"),
            ("references/matt-governance.md", "`writing-for-agents`", "`missing-command`"),
        )
        for path, before, after in cases:
            with self.subTest(path=path, regression=after):
                self.assertIn(before, " ".join(originals[path].split()))
                mutated = dict(originals)
                mutated[path] = " ".join(originals[path].split()).replace(before, after)
                self.assertTrue(governance_errors(mutated), after)

    def test_description_request_shapes(self):
        # Human/loader discovery probes, not an LLM semantic-routing claim.
        description = yaml.safe_load(self.text("SKILL.md").split("---", 2)[1])["description"]
        probes = {
            "Standardize the GitHub repo's CI and agent issue/PR workflow": ("GitHub", "CI", "agentic"),
            "Upgrade my setup-github-repository governance": ("upgrades", "setup-github-repository"),
            "Generate a new bundled project skeleton": ("start-github-repo", "instead"),
        }
        for request, cues in probes.items():
            with self.subTest(request=request):
                for cue in cues:
                    self.assertIn(cue, description)

    def test_human_only_client_metadata_mutations(self):
        frontmatter = yaml.safe_load(self.text("SKILL.md").split("---", 2)[1])
        policy = yaml.safe_load(self.text("agents/openai.yaml"))
        def client_user_only(fm, codex):
            return (fm.get("disable-model-invocation") is True
                    and codex.get("policy", {}).get("allow_implicit_invocation") is False)
        self.assertTrue(client_user_only(frontmatter, policy))
        nested = dict(frontmatter)
        nested.pop("disable-model-invocation")
        nested["metadata"] = {"disable-model-invocation": True}
        self.assertFalse(client_user_only(nested, policy))
        self.assertFalse(client_user_only(frontmatter, {"interface": policy["interface"]}))
        self.assertFalse(client_user_only(frontmatter, {"policy": {"allow_implicit_invocation": True}}))


unittest.main(verbosity=2)
