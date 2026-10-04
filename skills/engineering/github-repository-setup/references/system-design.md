# System-design coverage and decisions

Use this process for every repository plan. Coverage means a topic was
considered, not that its technology must be installed. A directory, policy,
accepted decision, implementation and verified capability are different things.
Keep developer CodeGraph/LSP/MCP setup separate from product runtime AI.

## Ordered workflow

1. Inspect workload evidence before choosing architecture. Fill
   [the workload worksheet](../templates/workload-nfr.md) in the consolidated
   plan; identify facts, assumptions, unknowns and accountable owners.
2. Read [the coverage catalog](../templates/architecture-catalog.yml). Review
   all 81 user-supplied topics and 16 additional domains. Preserve stable IDs.
   For each, record applicable, not_applicable or pending, a reason, and the
   decision/evidence state. Alternatives are not cumulative requirements.
3. Follow [the register contract](../templates/architecture-register.md).
   During unapproved complex setup, embed the register or its reviewed summary
   in REPOSITORY-PLAN.md, not a separately scaffolded application tree.
   Use `grilling` only for material unknowns inspection cannot settle. Ask
   focused questions about tradeoffs and consequences; do not reopen no-Claude,
   no-Plane or other settled choices. Pending decisions name blocked phases.
4. Read [conditional patterns](architecture-patterns.md) for triggered domains.
   Put the selected approach, alternatives, risks and revisit triggers in the
   plan. Reuse canonical TRD/ADRs; do not duplicate prose into 97 documents.
5. Obtain plan approval before implementation. After approval, instantiate the
   register with the bundled `scripts/architecture_register.py init` command
   documented in the register contract. Its output is an unresolved draft,
   never approved architecture. Do not overwrite an existing register.
6. Before Story dispatch, review affected IDs, parent Epic/Feature, requirements,
   quantitative NFRs, ADRs, design references, tests and blockers. Use the
   register's `story` check for the explicitly reviewed impact set. Unrelated
   unresolved decisions do not block unrelated work. A deferred prerequisite
   does block dependent work; split discovery work from implementation rather
   than inventing a waiver.
7. At PR/release, validate evidence against the actual tested revision and
   deployment environment. The script checks record structure and selected
   state gates, not evidence truth, approval identity, impact completeness or
   architectural soundness. Independently review those before readiness.

## Proportionate document placement

For a small project, use linked TRD sections. For a larger project, use these
canonical equivalents under `docs/architecture/`, with owners and navigation:

| Document | Contents |
| --- | --- |
| coverage.md / coverage.yml | All topic IDs, applicability, decisions, owners, traceability and evidence |
| system.md | Context, domain boundaries, components, critical runtime flows and seams |
| quality-attributes.md | Workload scenarios, capacity, budgets, measurable quality attributes |
| interfaces.md | Protocols, API/event schemas, errors, versioning and compatibility |
| data.md | Stores, consistency, transactions, tenancy, lifecycle and migrations |
| platform.md | Network, traffic, scaling, environments, deployment and infrastructure |
| security.md | Assets, threats, trust boundaries, authorization and abuse controls |
| operations.md | SLOs, telemetry, alerts, incidents, restore and failover exercises |
| ai-runtime.md | Conditional product AI: evaluation, retrieval, autonomy and tool safety |

Keep existing `SEAMS.md`, ADRs, runbooks, traceability and evidence paths.
Create `contracts/`, `infra/`, `deploy/` or `observability/` only when they hold
real machine-readable artifacts; use meaningful unit, integration, contract,
end-to-end and resilience tests, not empty folder scaffolding.

## Readiness boundaries

- Plan: every topic has a reasoned applicability disposition; applicable
  unresolved/deferred choices have owners, impact and revisit triggers.
  Plan approval can authorize discovery while withholding dependent setup.
- Story: impacted implementation choices are accepted or reasonedly excluded;
  approval, FR/NFR and hierarchy mapping exist. NFR acceptance thresholds and
  relevant negative tests are explicit. No implied runtime activation.
- PR: attach real TDD red/green evidence or an approved exception, failure
  scenarios, architecture changes and reproducible results at the tested SHA.
  Changed architecture renews affected decisions and review.
- Production: applicable release-scope requirements need verified evidence.
  Require capacity/security checks, user-centric SLOs, operational owner and
  recovery exercise evidence where relevant; passing CI alone is insufficient.
  Approval for staging is not approval for release.

## Research basis

Use architecture views, cross-cutting concerns, quality scenarios and decisions
without duplicating authority, consistent with [arc42](https://arc42.org/overview).
Include cost and sustainability alongside reliability/security/performance,
as in [AWS Well-Architected](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html).
Select patterns by problem and tradeoffs, not fashion, using the
[Azure pattern catalog](https://learn.microsoft.com/en-us/azure/architecture/patterns/).
Define user-centered indicators and error-budget ownership following
[Google's SLO guidance](https://sre.google/workbook/implementing-slos/).
Map security requirements to verifiable controls using
[OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/);
review AI-specific threats using the
[OWASP GenAI risks](https://genai.owasp.org/llm-top-10/).
