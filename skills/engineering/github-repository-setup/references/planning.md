# Initial repository plan before setup

The initial `setup-github-repository` request routes to this skill's planning
phase. The installed name remains `github-repository-setup`. Produce one
consolidated final-repository plan before implementation, not scattered tool
recommendations followed by immediate installation.

## When to stop at the plan

Treat setup as complex when it includes multiple packages or services,
cross-cutting architecture/design decisions, several MCP/runtime dependencies,
branch/environment migrations, external integrations, substantial existing
configuration to preserve, or unresolved authority/security choices.

Inspect first. Use conditional `grilling` to resolve consequential unknowns.
Then draft `REPOSITORY-PLAN.md` or update the existing equivalent setup-plan
document. This planning artifact is the only new repository document to write
before approval unless the user also authorizes supporting research drafts.
In read-only checklist/search mode, present the proposed plan without writing.

For complex setup, stop and request approval of the consolidated plan. Do not
scaffold project files, install tools, configure MCP, create live backlog
issues, change GitHub settings, launch agents, or enable CI/deployment first.
An instruction to "set up the repo" is not approval for choices the plan has
not yet exposed. If the user has already approved the exact complete plan,
execute its next authorized phase without requesting the same approval again.

For simple setup, still show a proportionate plan and changed-file/settings
list; existing scope approval can cover it. Do not turn routine inspection
into a large interview or demand enterprise documents full of filler.

## REPOSITORY-PLAN.md contract

Include all of the following, tailored to the actual repository:

1. Goal, scope/non-goals, project type, current-state findings and constraints.
   Record no Plane.so and no Claude files/configuration.
2. Final target tree with purpose, owner and status for every planned file
   group. Map existing paths to required contracts; show create, merge,
   retain, move or defer. No silent destructive replacements.
3. Document plan: PRD, TRD, TOGAF ADM, TDD, Epic/Feature/Story hierarchy,
   DESIGN.md, DESIGN-SYSTEM.md, UI-UX.md, WIREFRAME.md, ADRs and traceability.
   Record approved not-applicable entries with reasons, not omissions.
4. Agent operating model: AGENTS.md, Agent.md, Agent-Protocol.md, one canonical
   protocol, dispatcher/claim mechanism, roles, permissions and escalation.
5. GitHub workflow: logical IDs, parent/child/blocking relationships, labels,
   templates, integration/default/release branches, PR checks, independent
   review, completion boundary, promotion and rollback authority.
6. Tools and skills: CodeGraph, language/LSP support, GitHub CLI/MCP choice,
   conditional Penpot/browser/component tools and companion skills. Record
   versions to resolve, transport, scope, owner, secret reference names,
   installation/client changes, smoke tests and fallback. Never secret values.
7. Ordered setup work packages and dependencies, from approved decisions
   through documents, collaboration files, local gates, optional tools,
   remote settings and end-to-end verification. Give each phase a deliverable,
   acceptance test, rollback approach and approval boundary.
8. Draft setup Epics, Features and Stories with requirements and acceptance
   criteria. These are proposed tickets, not silently published GitHub issues.
9. Validation matrix: static checks, negative cases, live client/settings
   checks, required evidence and the final acceptance walkthrough.
10. Open decisions, blockers, risks, deferred items and accountable owners.
    Mark estimates and unverified capabilities as such.
11. Approval record: plan revision, agreed scope, exclusions, authorized
    phases and decisions. Leave approver/date pending until actually approved.

The plan describes the final repository, including setup work not performed
in the first phase. It is not a substitute for the eventual PRD/TRD or proof
that proposed tools are operational.

## Execution after approval

Translate approved setup work into GitHub tickets only when publication is
authorized. Apply one dependency-ordered phase at a time through a branch and
PR; update plan status and evidence as phases complete.

If installation reveals a material new permission, service, cost, migration
or architecture choice, amend the same plan and obtain approval for that delta
before continuing. Do not quietly turn setup into a different repository
design. Do not use an approved documentation phase as permission to activate
agents or deploy production.
