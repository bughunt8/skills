# Repository plan

Status: draft, not approved for implementation.
Repository: REPLACE_WITH_OWNER_AND_REPO
Plan revision: REPLACE_WITH_REVISION
Accountable owner: REPLACE_WITH_CONFIRMED_OWNER

Replace all template values from inspection and confirmed decisions. This is
the consolidated final repository plan, not permission to install or enable
its proposed components.

## Outcome and current state

- Problem, users, intended outcomes and success measures:
- In-scope work and non-goals:
- Current branch/default/integration/release model and checked SHA:
- Existing architecture, commands, documents and integrations to preserve:
- Constraints, risks and open decisions:

GitHub Issues are the ticket authority. No Plane.so or tracker mirror.
No CLAUDE.md/Claude.md, Claude configuration or Claude installation targets.

## Final target structure

Show the final target tree, then fill the inventory. Include required
document contracts and the applicable repository-structure baseline; do not
create empty directories just to fill the tree.

| Path or existing equivalent | Purpose and canonical authority | Retain/create/merge/defer/N/A | Owner | Validation | Rationale |
| --- | --- | --- | --- | --- | --- |
| REPLACE_WITH_PATH | REPLACE_WITH_PURPOSE | REPLACE_WITH_ACTION | REPLACE_WITH_OWNER | REPLACE_WITH_CHECK | REPLACE_WITH_REASON |

Cover editor/Git hygiene, safe environment examples, source/tests/scripts,
ownership, contributor intake, dependency maintenance, security, documentation
navigation, generated outputs and any approved infrastructure.

## Documents and traceability

Map PRD.md, TRD.md, TOGAF-ADM.md, TDD.md, DESIGN.md, DESIGN-SYSTEM.md,
UI-UX.md, WIREFRAME.md, INTENT.md, context, ADRs and seams to canonical paths.
Record draft/approved/N/A status and owners; UI exclusions require reasons.

Map requirement -> Epic -> Feature -> Story -> ADR/design/test -> PR -> evidence.
Tailor Preliminary and ADM A-H plus continuous Requirements Management.
Define Story readiness, real red/green evidence and documented test exceptions.

## Architecture coverage and quality decisions

Embed the [workload/NFR worksheet](workload-nfr.md) and the reviewed
[coverage register](architecture-register.md), covering all 81 original
considerations and 16 additional domains from the
[catalog](architecture-catalog.yml). Map existing TRD/ADRs instead of creating
duplicate authority. In the final project replace these template-relative links
with the canonical project paths.

Record applicability, rationale, alternatives, selected approach, owner,
approval, FR/NFR and Epic/Feature/Story links, tests, evidence, implementation
state and revisit conditions. Accepted is not implemented or verified.
Identify affected-work blockers and separately authorized discovery.
List triggered patterns and their simpler alternatives; do not install every
technology. Include operational, security, recovery and release evidence gates.

Before selecting tools, distinguish development agents from product AI.
CodeGraph/LSP/GitHub MCP alone do not require AI runtime architecture.

## Agent operating model

AGENTS.md is the instruction entry; Agent.md defines roles; Agent-Protocol.md
owns or points to the one canonical execution protocol.

Record dispatcher, implementer, independent reviewer and release owners,
claim serialization, worktree isolation, handoff, forbidden actions and
escalation. No self-approval, self-merge or implicit production authority.

## GitHub collaboration and completion

Define hierarchy IDs, parent/child links, blockers, triage mappings, bug,
feature, documentation and agent-task intake; verify support/security routes.
Record PR base branches, required checks, review rules and bypass owners.
Define integrated/staging-verified/released completion and explicit issue
closure behavior for non-default branches.

## Tooling and skills

| Capability | Required/conditional/optional | Selected tool/version | Client/configuration | Permission/secret reference | Owner | Smoke test and fallback |
| --- | --- | --- | --- | --- | --- | --- |
| REPLACE_WITH_CAPABILITY | REPLACE_WITH_NEED | REPLACE_WITH_TOOL | REPLACE_WITH_CLIENT | REFERENCE_NAME_ONLY | REPLACE_WITH_OWNER | REPLACE_WITH_TEST |

Resolve CodeGraph, language/LSP tooling, GitHub CLI or MCP, conditional
Penpot/browser tools, setup-matt-pocock-skills and any grilling dependencies.
Never record secret values or token-bearing URLs.

## Automation and maintenance decisions

For dependency updates, hooks, scanners, release, documentation publishing,
template sync, cache cleanup, stale closure and auto-merge, record selected,
deferred or rejected, with rationale and owner. Default auto-merge and stale
closure to disabled; template sync, releases and publishing need approval.
Name manual/generated file owners and prevent conflicting version writers.

## Phased setup and draft tickets

| Phase | Dependencies and scope | Deliverables | Draft Epic/Feature/Story | Acceptance and evidence | Rollback | Approval |
| --- | --- | --- | --- | --- | --- | --- |
| REPLACE_WITH_PHASE | REPLACE_WITH_SCOPE | REPLACE_WITH_FILES | DRAFT_IDS_ONLY | REPLACE_WITH_CHECKS | REPLACE_WITH_ROLLBACK | Pending |

Sequence decisions, documentation, collaboration, checks, tools, remote
settings and end-to-end verification. Draft tickets are not yet published.

## Validation and unresolved work

List actual commands, test fixtures, negative cases, client/remote checks and
sanitized evidence at a known revision. Separate static checks from live
settings and integration verification. Record blocked/deferred/N/A work with
owner and reason; do not label unrun tests passed.

## Approval record

Approver/date: pending.
Approved plan revision and phases: pending.
Excluded actions: no production promotion or agent activation by implication.

For complex setup, stop here until the consolidated plan is approved.
Material new permissions, services or architecture choices require plan
amendment and delta approval before the dependent phase continues.
