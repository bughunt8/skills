"""Static package regression checks; not a live setup/integration test."""
import pathlib
import re
import sys
import unittest

import yaml

ROOT = (pathlib.Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1
        else pathlib.Path(__file__).resolve().parents[1])


class SetupSkillPackage(unittest.TestCase):
    def text(self, name):
        return (ROOT / name).read_text()

    def test_frontmatter_and_routing_budget(self):
        text = self.text("SKILL.md")
        frontmatter = yaml.safe_load(text.split("---", 2)[1])
        self.assertEqual(frontmatter["name"], ROOT.name)
        self.assertLessEqual(len(frontmatter["description"].split()), 50)
        self.assertLess(len(text), 4300)
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
        hub = self.text("SKILL.md")
        for directory in ("references", "templates"):
            for path in (ROOT / directory).iterdir():
                self.assertIn(str(path.relative_to(ROOT)), hub)

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
                       "to-spec", "draft first", "CONTEXT.md"):
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


unittest.main(verbosity=2)
