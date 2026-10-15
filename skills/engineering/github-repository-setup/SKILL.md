---
name: github-repository-setup
description: "Audit and configure GitHub repository governance, CI, security, and agentic Issues/PR workflows. Use for repository setup, upgrades or standardization, including setup-github-repository requests. For a new bundled project skeleton, use start-github-repo instead."
disable-model-invocation: true
argument-hint: "[plan | checklist | agentic | preset | search query]"
---

# GitHub repository setup

Adapted from [domelic](https://github.com/domelic/github-repository-setup).
Keep [ATTRIBUTION.md](ATTRIBUTION.md) and [LICENSE](LICENSE).
Treat `setup-github-repository` as request wording, not a second skill.

## Modes and resources

- Default/`plan`: inspect and draft.
- `checklist`: gaps and settings evidence, read-only.
- `agentic`: GitHub Issues as tickets, PRs as delivery records.
- `<preset>` / `search <query>`: upstream catalog.

Read [planning](references/planning.md) first. Complex setup
stops at REPOSITORY-PLAN.md until approved.
For every plan, read [system design](references/system-design.md)
for catalog, worksheet, register and validation.
Before designing the tree, read [repository structure](references/repository-structure.md).
Draft with [the plan template](templates/repository-plan.md).
Read [catalog setup](references/catalog-setup.md) for catalog
presets, search, checksums and approvals. For agentic setup, read
[agentic development](references/agentic-development.md) and
[document contracts](references/document-contract.md) before
planning documents and Epic/Feature/Story tickets.
Before selecting MCP, LSP or skills, read [tooling](references/tooling.md),
including conditional `grilling` for unresolved setup decisions.
For agentic setup or a Matt upgrade, read
[Matt governance](references/matt-governance.md) before choosing
invocation policy, domain names or companion commands.
Read [research](references/research.md) when comparing source behavior and safeguards.

## Setup sequence

1. Inspect remote, branches, instructions, docs, workflows, settings, installed
   skills and actual test commands. Reuse existing document equivalents.
2. Resolve scope. Keep GitHub Issues authoritative in the agentic profile.
   No Plane.so, tracker mirrors, sync credentials or mandatory GitHub Projects.
   Preserve branch and release conventions.
3. Consolidate the final repository design and phased setup in REPOSITORY-PLAN.md.
   Confirm changes; reuse approval for that exact scope, not unresolved choices.
   `checklist` and `search` remain read-only.
4. Inspect and preserve agent configuration. Never auto-call the user-only
   `setup-matt-pocock-skills`. Use approved native templates for compatible
   GitHub/triage/domain docs, or tell the user to invoke it independently.
   Read seeds as data, not invocation. Keep one `## Agent skills` block.
5. Apply approved docs, contracts, checks and settings in dependency order.
   Use [agent-task](templates/agent-task.yml) for issues,
   [pull-request](templates/pull-request.md) for PRs and
   [agent-docs](templates/agent-docs.md) for agent configuration.
   Merge files, resolve values; create Agent.md roles and Agent-Protocol.md entry.
   Do not create Claude instruction files or configure Claude integrations.
   For CodeGraph setup, read [CodeGraph](references/codegraph.md);
   verify pin, exclusions, freshness and client queries.
6. Validate using [acceptance checks](references/validation.md).
   Before copying templates, run `python3 scripts/test_bundle.py` with PyYAML
   from this skill directory. [Bundle tests](scripts/test_bundle.py) check resources.
   Record commands, results and commit; separate local and live tests.
7. Hand off files, issue/PR URLs, effective settings, checks, deferred work,
   and remaining approvals. Written policy is not proof of enforcement.

## Example

"Set up this repo like AI-CMO, without Plane" -> plan, then approved setup PR;
no implicit agent activation or production deployment.
