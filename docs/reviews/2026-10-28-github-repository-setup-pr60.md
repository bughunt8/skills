# Independent review: GitHub repository setup, PR 60

**Review date:** 2026-10-28
**Issue:** [#59](https://github.com/bughunt8/skills/issues/59), “Update repository setup for plan-first GitHub-native agentic development”
**Pull request:** [#60](https://github.com/bughunt8/skills/pull/60), merged into `staging`
**Scope:** PR change commit `5273a16c5a375bfb9db81bf902dc7d3e97d52db1`, its PR-head commit `136924f`, and merge commit `4086c1678ea05a79f02104e9a1e0c0e74f5e0f7d`; compare the PR result with merge first parent `7f1b4bf`.
**Boundary:** This is a retrospective review. The PR had already merged on 2026-10-04 when this review was written. Later integration commits are excluded; all code citations below refer to the `4086c16` merge snapshot.

## Verdict

**Checklist: MET.** The merged snapshot documents each checked requirement and adds the requested package regression test. PR 60 is demonstrably merged to `staging`, and this review supplies the outstanding independent review. The test passes, but it is primarily a static contract test: it checks document contents, links, and YAML structure, not whether the described setup process works against a live GitHub repository or agent client.

**Review quality finding:** The architecture coverage requirement is disproportionate for small repositories. `references/system-design.md:10-16` requires every plan to review all 81 supplied topics and 16 additional domains. `references/document-contract.md:7-11` and `references/planning.md:30-33` repeat that requirement, while the same profile says to keep small projects proportionate and avoid filler (`references/system-design.md:43-44`; `references/document-contract.md:46-47`). This is a meaningful adoption-cost risk, not a checklist failure: the issue requested architecture planning and TOGAF ADM, but did not require a universal 97-topic register. The skill should make the exhaustive register conditional on project scale/risk, or let a proportionate review justify exclusions without processing every topic.

## Acceptance review

Issue #59 contains nine criteria. The first eight were checked before review; the ninth asks for independent review and merge through staging. Verdicts assess the merged code, not the author's checklist marks.

| # | Acceptance criterion | Verdict | Evidence in merge snapshot |
| --- | --- | --- | --- |
| 1 | Complex setup starts with a consolidated `REPOSITORY-PLAN.md` and waits for approval. | **MET** | `references/planning.md:1-5, 15-28` defines the plan-first gate and says to stop for approval; `templates/repository-plan.md:117-125` leaves approval pending and repeats the stop condition. |
| 2 | Conditional `grilling` resolves consequential setup decisions. | **MET** | `references/tooling.md:133-163` triggers grilling only for unresolved consequential choices, researches facts first, and stops when the decision frontier is empty or deferred. `references/system-design.md:17-22` makes the same conditional distinction. |
| 3 | Require PRD, TRD, TOGAF ADM, TDD, Epic/Feature/Story traceability, design system, UI/UX and wireframes. | **MET** | `references/document-contract.md:13-33` enumerates the document set and traceability contract; `:44-60` specifies ADM phases; `:68-99` defines the GitHub hierarchy; `:115-135` sets TDD and design gates. UI documents may be recorded N/A only with a reason (`:39-42`). |
| 4 | Specify AGENTS.md, Agent.md and Agent-Protocol.md without duplicate authority. | **MET** | `references/agentic-development.md:54-80` identifies the three roles and canonical files; `:88-95` assigns one protocol authority and prohibits circular/full duplicate copies. `templates/agent-docs.md:74-84, 103-131` supplies the AGENTS entry, Agent roles, and protocol-pointer rules. |
| 5 | Integrate setup-matt-pocock-skills with no-Claude override and missing-seed fallback. | **MET** | `references/agentic-development.md:21-47` locates the exact skill, records absent seeds in the inspected snapshot, requires AGENTS-only override, and directs use of local fallback sections after approval. `templates/agent-docs.md:3-6, 74-84` supplies those fallback instructions and explicitly prohibits Claude files. |
| 6 | Document CodeGraph, language/LSP tooling, GitHub CLI/MCP and conditional Penpot MCP. | **MET** | `references/tooling.md:7-25` covers CodeGraph, LSP, GitHub and conditional Penpot capabilities; `:33-62` documents GitHub MCP and existing `gh` as sufficient; `:64-101` makes Penpot conditional and addresses token-bearing URLs. The CodeGraph install, freshness and verification contract is in `references/codegraph.md:1-19, 48-74`. |
| 7 | Define issue claims, worktrees, PR evidence, independent review, staging verification and closure semantics. | **MET** | `references/agentic-development.md:135-174` sets claim and worktree rules, evidence, independent review, merged-SHA staging verification, promotion and closure boundaries. The PR template asks for tested SHA and check output (`templates/pull-request.md:22-30`) and independent review (`:37-42`). |
| 8 | Add reusable issue, PR and agent-document templates plus package regression tests. | **MET** | The merge contains `templates/agent-task.yml`, `templates/pull-request.md`, `templates/agent-docs.md` and `scripts/test_bundle.py`. The workflow invokes the package test at `.github/workflows/a0-skills-checks.yml:60-61`. Test output is recorded below. |
| 9 | Review and merge the implementation PR through the repository's staging process. | **MET, RETROSPECTIVE** | Merge commit `4086c16` is titled “Merge pull request #60” and has first parent `7f1b4bf` on the staging line. The merge occurred 2026-10-04; this review is dated 2026-10-28. Thus the merge preceded the review, rather than following it. No claim is made that this document caused or gated the merge. |

## Findings

### Major: universal architecture inventory may make setup impractical

**Location:** `skills/engineering/github-repository-setup/references/system-design.md:10-16`; `references/document-contract.md:7-11`; `references/planning.md:30-33`.

The plan workflow requires an evidence-backed disposition for all 97 architecture topics before approval, including for projects otherwise described as small. The skill later allows linked TRD sections and proportionate records, but that changes document placement, not the universal coverage obligation. This can turn a narrow setup into a large questionnaire and encourage low-value “not applicable” paperwork. Make the full register conditional on scale, risk, or explicit user need, and define a proportionate alternative as satisfying the review requirement.

### No other merge-blocking defect found

I found no contradiction in the core plan-approval gate, AGENTS-only/no-Claude override, missing-seed fallback, GitHub Issues authority, separation of staging from release, or explicit distinction between written policy and enforcement. The package's links resolve and its test confirms that every reference/template resource is reachable from the skill hub. This is bounded evidence from static review and the named test, not proof of live GitHub configuration, agent dispatch, or client connectivity.

## Package regression

Ran the test from the exact `4086c16` tree extracted outside the worktree so later staging changes could not affect the result:

```text
python3 skills/engineering/github-repository-setup/scripts/test_bundle.py
test_all_local_markdown_links ... ok
test_architecture_register_behavior ... ok
test_codegraph_contract ... ok
test_complex_setup_is_plan_first ... ok
test_document_and_adm_contract ... ok
test_frontmatter_and_routing_budget ... ok
test_hub_routes_every_runtime_resource ... ok
test_issue_form_schema ... ok
test_original_attribution_and_license ... ok
test_protocol_and_no_claude_scaffolding ... ok
test_repository_plan_template ... ok
test_repository_structure_baseline ... ok
test_safety_and_lifecycle_contract ... ok
test_template_adoption_safety ... ok
test_tooling_and_grilling_contract ... ok

----------------------------------------------------------------------
Ran 15 tests in 1.130s

OK
```

The test checks string presence for many policy claims and validates some structure. It does not exercise installation, idempotent application to repositories, GitHub API behavior, permissions, or live MCP/LSP/CodeGraph/Penpot operation. That limitation is consistent with its docstring (`scripts/test_bundle.py:1`) and should not be read as an integration-test pass.

## What was not verified

- I did not run the setup against a live repository, alter GitHub settings, install a client or tool, create issues, or test MCP/LSP/CodeGraph/Penpot connectivity. Those actions are outside this retrospective static review.
- The test asserts that contracts appear in the package; it does not prove that a future agent follows them or that remote enforcement matches the written policy.
- The review is against the PR 60 merge snapshot only. It makes no claim about later revisions of this skill or the current state of `staging`.

## Closing result

Issue #59's checklist is met by the merged implementation and this review artifact: criteria 1-8 are present in the merged snapshot, criterion 9's merge is complete, and the independent review is now recorded. The proportionality finding above remains a recommended follow-up, not an unmet checkbox.
