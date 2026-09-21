# Documents and Epic, Feature, Story traceability

Read this before generating the document plan or backlog. These are required
contracts, not a list of empty files. Reuse established equivalent paths and
record the mapping in README and the traceability document.

Apply [system-design.md](system-design.md) to architecture coverage. Require the
81-topic plus 16-domain register and workload/NFR worksheet, using TRD sections
or proportionate linked architecture files. Each affected Story/PR maps decision
IDs to requirements, hierarchy, tests and revision-specific evidence. Names of
folders or accepted decisions alone do not establish implementation readiness.

## Required document set

| Artifact | Minimum useful content | Acceptance check |
| --- | --- | --- |
| REPOSITORY-PLAN.md | Final target structure, document/tool/agent contracts, phased setup, draft tickets, gates and approval record | Complex setup stops here until the consolidated plan is approved |
| INTENT.md | Problem, outcomes, scope, non-goals, stakeholders, architecture principles | Named decision owner; unresolved choices identified |
| AGENTS.md | Read order, real commands, safety rules, document map, no-Claude policy | Canonical agent instructions; links to Agent.md and Agent-Protocol.md resolve |
| Agent.md | Roles, issue ownership, dispatcher, implementer/reviewer separation, permissions, escalation and release authority | No role self-grants readiness, review approval, or production authority |
| Agent-Protocol.md | Issue pickup, claim, worktree, recon, TDD, PR, review, verification, handoff and closure | One authoritative protocol; compatibility paths point to it, or it points to the existing protocol |
| docs/agents/tooling.md | Required/optional MCP, LSP and skill inventory, pinned versions, permissions, clients, ownership, smoke tests and fallbacks | Each required capability verified or explicitly blocked; no secrets |
| PRD.md | Users, journeys, functional FR IDs, measurable NFR IDs, acceptance, risks, release scope, Epic/Feature/Story map | Every in-scope requirement has an owner and planned Story coverage |
| TRD.md | System/component boundaries, data model, APIs/events, trust boundaries, deployment, operations, failure modes, ADRs | Every proposed implementation maps to requirements and testable contracts |
| TOGAF-ADM.md | Tailored ADM phase records, inputs, outputs, decisions, gaps, owners, and gates | Every phase below addressed or explicitly deferred with reason and owner |
| TDD.md | Test layers, fixtures, commands, red/green/refactor protocol, negative cases, evidence and CI gates | Each Story acceptance criterion has a test or justified manual verification plan |
| DESIGN.md | Product visual direction, composition, responsive approach, rationale, references | Consistent with the approved UI/UX and design system; not a competing token source |
| DESIGN-SYSTEM.md | Semantic tokens, typography, spacing, layout, components, states, accessibility rules, implementation mapping | Components and tokens have canonical definitions and validation rules |
| UI-UX.md | Personas, journey/task flows, navigation, interaction rules, content, error/recovery, accessibility, responsive behavior | Each UI Story links its journey, component states, and acceptance expectations |
| WIREFRAME.md | Screen inventory, annotated layouts, screen IDs, transitions, breakpoints and state coverage | Each in-scope UI flow has traceable screens and unresolved decisions are flagged |
| docs/traceability.md | Requirement -> Epic -> Feature -> Story -> ADR/design/test -> PR -> evidence | No orphan in-scope Story or requirement; incomplete mappings block readiness |
| docs/adr/ | Decision, alternatives, rationale, consequences, status, owner | Architecture changes link an accepted or explicitly pending ADR |
| docs/architecture/SEAMS.md | Module responsibility, allowed dependencies, contracts, integration/test seams | Critical boundaries have executable checks where feasible |

Document-level status must distinguish draft, approved, superseded, and
not-applicable. Record owner, revision/date, and the related review/decision.
Do not fabricate approval or write speculative requirements as settled facts.

For a backend-only or documentation project, keep a mapped not-applicable
record for UI/UX, wireframes, and the design system, with scope-based rationale
confirmed in the setup plan. Missing files alone are not a waiver. For a UI
project, all design contracts are required before relevant Stories are ready.

## TOGAF ADM tailoring

Treat this as a proportionate project architecture process, not a certification
claim. Preserve the named phases even when several share one short record.

| Phase | Required project record |
| --- | --- |
| Preliminary | Architecture scope, roles, governance, principles, repository standards |
| A: Architecture Vision | Outcomes, stakeholders, scope, constraints, initial risks, approval boundary |
| B: Business Architecture | Capabilities, processes, actors, value/outcomes, Epic and Feature alignment |
| C: Information Systems Architectures | Data and application architecture, ownership, interfaces and contracts |
| D: Technology Architecture | Runtime, infrastructure, networking, security and operational constraints |
| E: Opportunities and Solutions | Solution options, gaps, work packages, dependencies and transition options |
| F: Migration Planning | Sequenced Features/Stories, releases, migration/rollback, risk and effort assumptions |
| G: Implementation Governance | Requirement/ADR compliance, review, architecture checks, evidence and exceptions |
| H: Architecture Change Management | Drift monitoring, change triggers, ADR updates, impact and reassessment |
| Requirements Management | Continuous requirement IDs, change history and traceability across every phase |

For each record, capture current and target state where meaningful, decisions,
open gaps, accountable owner, and the criterion to advance. Do not invent a
formal architecture board; use the project's actual approver. Changes to
requirements, business constraints, or architecture reopen affected decisions
and tickets, not the whole process by default.

## GitHub hierarchy

Use GitHub Issues as the sole ticket record:

```text
Epic EP-001: business outcome and success measure
  Feature FE-001: releasable capability and acceptance boundary
    Story ST-001: small user or system behavior with testable acceptance
      Task: optional implementation detail, never a replacement for the Story
```

These identifiers are examples, not preapproved backlog content. Preserve an
existing stable vocabulary with an explicit mapping. GitHub issue numbers are
links; logical IDs remain stable even if work moves between repositories.

Create native parent-child links when available. Use a parent checklist and
child `Part of #N` line otherwise. Add blocking dependencies separately.
Use native issue types if available, or `type:epic`, `type:feature`,
`type:story`, and optional `type:task` labels. Capability-check types and labels;
do not require organization-only settings for a personal repository.

| Level | Required content | Completion rule |
| --- | --- | --- |
| Epic | Outcome, measures, scope/non-goals, stakeholders, PRD requirements, Feature links | Features accepted and outcome evidence reviewed; children closing is not sufficient alone |
| Feature | Capability, journeys, FR/NFR IDs, TRD/ADR/design links, acceptance, Story links and dependencies | Stories accepted and capability/integration tests pass |
| Story | Parent Feature and Epic, behavior, FR/NFR IDs, design/ADR references, boundaries, acceptance criteria, test plan, blockers and risk | Reviewed PR, criterion-level evidence, and agreed integration/release gate satisfied |

Use the bundled agent-task form for executable Stories or Tasks, adapting the
title and parent fields. Draft Epic and Feature issue bodies from this table,
not from an implementation-only form. Approve backlog publication separately
from drafting documents. A setup request does not authorize creating hundreds
of speculative issues.

Example traceability row for an approved UI Story:

```text
FR-012 / NFR-004 -> EP-001 -> FE-003 -> ST-014 / #42
-> TRD section 4 / ADR-0007
-> UI-UX flow UX-03 / WIREFRAME screen WF-08
-> DESIGN-SYSTEM component FormField, semantic error token
-> tests ST-014-AC1 and ST-014-AC2 -> PR #51
-> CI run + tested SHA + staging evidence
```

The numbers illustrate the format only. Replace them with real identifiers;
never create dead links that resemble existing evidence.

## TDD and design gates

1. Before readiness, establish Story acceptance and failure cases, test seams,
   actual verification commands, and required architecture/design decisions.
   Block unresolved high-risk requirements rather than guessing.
2. During implementation, demonstrate the intended test failing for the right
   reason, implement the smallest passing change, then refactor with tests
   green. Capture the red and green results; do not simulate a red run.
3. Test critical refusal, boundary, authorization, migration, and recovery
   behavior where relevant. Document justified exceptions for prose-only or
   exploratory tasks with an alternative verification method.
4. For UI Stories, cover default, loading, empty, error, success, disabled,
   focus and keyboard states where applicable. Verify responsive layouts,
   accessible names, contrast and focus behavior against the project standard.
   Use interaction tests and visual evidence; snapshots alone are insufficient.
5. Keep tokens and component APIs in one authoritative design system. Map
   implementation components to it; record any approved deviation in the PR.
   Wireframes and design references must agree on screen IDs and flow changes.
6. At review, require a complete traceability row and actual checks at the
   relevant commit. Fail readiness or merge checks on broken required mappings,
   not merely on missing filenames. Update all affected documents in the PR.

## Research basis

The named ADM phases and continuous Requirements Management follow
[The Open Group's ADM overview](https://pubs.opengroup.org/pocket-guides/togaf-pocket-guide/main/chap06.html).
The document filenames, GitHub Epic/Feature/Story mapping, readiness gates, and
TDD/design evidence contract are this profile's tailored requirements, not a
claim that TOGAF mandates these repository filenames.
