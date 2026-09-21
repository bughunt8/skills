---
name: github-repository-setup
description: "Audit and configure GitHub repository governance, CI, security, and agentic development through Issues and PRs, integrating setup-matt-pocock-skills. Use for repository setup or standardization, including requests for setup-github-repository. For a new bundled project skeleton, use start-github-repo instead."
metadata:
  disable-model-invocation: true
  argument-hint: "[plan | checklist | agentic | preset | search query]"
---

# GitHub repository setup

Adapted from [domelic/github-repository-setup](https://github.com/domelic/github-repository-setup).
Preserve [ATTRIBUTION.md](ATTRIBUTION.md) and [LICENSE](LICENSE).
Treat `setup-github-repository` as request wording, not a second skill.

## Modes and resources

- No argument or `plan`: inspect and draft the final repository plan first.
- `checklist`: report gaps and settings evidence without writing.
- `agentic`: configure GitHub Issues as tickets and PRs as delivery records.
- `<preset>` or `search <query>`: use the upstream catalog.

Read [references/planning.md](references/planning.md) first. Complex setup
stops at the consolidated REPOSITORY-PLAN.md until approved.
Before designing the tree, read [references/repository-structure.md](references/repository-structure.md).
Draft the plan with [templates/repository-plan.md](templates/repository-plan.md).
Read [references/catalog-setup.md](references/catalog-setup.md) for catalog
presets, search, checksums, approvals and validation. For agentic setup, read
[references/agentic-development.md](references/agentic-development.md) and
[references/document-contract.md](references/document-contract.md) before
planning documents and Epic/Feature/Story tickets. Before selecting MCP, LSP
or skills, read [references/tooling.md](references/tooling.md). For unresolved
setup decisions, use its conditional `grilling` process.
Read [references/research.md](references/research.md) when comparing source
behavior with this profile's safeguards.

## Setup sequence

1. Inspect remote, branches, instructions, docs, workflows, settings, installed
   skills and actual test commands. Reuse existing document equivalents.
2. Resolve scope. Keep GitHub Issues authoritative in the agentic profile.
   Do not add Plane.so, tracker mirrors, sync credentials, or mandatory
   GitHub Projects. Preserve existing branch and release conventions.
3. Consolidate the final repository design and phased setup in REPOSITORY-PLAN.md.
   Confirm changes; reuse approval for that exact scope, not unresolved choices.
   `checklist` and `search` remain read-only.
4. For agentic setup, run the installed `setup-matt-pocock-skills` first.
   Apply the AGENTS.md-only override, preserve triage mappings, and follow the
   missing-seed fallback. Do not duplicate its `## Agent skills` block.
5. Apply documentation, issue/PR contracts, checks, and approved settings in
   dependency order. Use [templates/agent-task.yml](templates/agent-task.yml)
   for an agent issue form, [templates/pull-request.md](templates/pull-request.md)
   for the PR contract, and [templates/agent-docs.md](templates/agent-docs.md)
   for agent configuration. Merge existing files and resolve template values.
   Create the Agent.md roles contract and Agent-Protocol.md execution entry.
   Do not create Claude instruction files or configure Claude integrations.
   For CodeGraph setup, read [references/codegraph.md](references/codegraph.md);
   verify its pinned install, exclusions, freshness and client queries.
6. Validate using [references/validation.md](references/validation.md).
   Before copying templates, run `python3 scripts/test_bundle.py` from this
   skill directory with PyYAML installed to check the package.
   Record commands, results and checked commit; distinguish local and live tests.
7. Hand off files, issue/PR URLs, effective settings, checks, deferred work,
   and remaining approvals. Written policy is not proof of enforcement.

## Example

"Set up this repo like AI-CMO, without Plane" produces a consolidated plan,
then an approved setup PR. No Claude configuration, tracker mirror, agent
runtime or production deployment is implicitly enabled.
