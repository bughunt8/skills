# Workload and quality worksheet

Embed this in the initial REPOSITORY-PLAN.md. After approval, move detailed
content to the canonical TRD or quality-attributes document and link it.
Do not invent benchmark results or assume a particular stack.

## Workload facts and assumptions

| Question | Fact / assumption / unknown | Evidence | Owner and resolution |
| --- | --- | --- | --- |
| Critical journeys, business invariants and failure consequences | | | |
| User types, tenancy, entitlements, service and client boundaries | | | |
| Normal/peak traffic, concurrency, burstiness and growth horizon | | | |
| Read/write mix, payload size, corpus/storage growth and retention | | | |
| Geography, residency, network/offline constraints and languages | | | |
| Data classification, privacy, legal obligations and threat actors | | | |
| Team, operational capacity, budget and delivery constraints | | | |
| Product AI need, autonomy level, model/data providers and permissions | | | |

## Measurable quality scenarios

For each applicable NFR, identify stimulus, environment/load, affected
component, expected response and threshold. Record units and measurement
window; distinguish target from observed result.

| NFR ID / journey | Scenario and load | Target / units / window | Measurement and failure test | Owner | Decision / Story IDs | Observed result / revision |
| --- | --- | --- | --- | --- | --- | --- |
| To resolve | | | | | | |

Consider p50/p95/p99 latency, throughput, concurrent users, queue lag,
availability, correctness/freshness, RTO/RPO, accessibility, compatibility,
capacity headroom, per-tenant quotas, cost per successful outcome and AI
quality/safety metrics. Select justified targets, not arbitrary universal
numbers. Define SLI numerator/denominator, SLO window, alert action and
error-budget response for critical user journeys.

## Cross-cutting decisions

- X01-X03: domain invariants, workload envelope, consistency/isolation,
  transaction boundaries, concurrent updates and atomic side effects.
- X04-X06: classification, residency, consent/retention/deletion including
  backups; tenant isolation across data/cache/search/AI; errors, pagination,
  webhook signatures/replay, compatibility and deprecation.
- X07-X09: ordering, deduplication, retries, DLQs/redrive/backpressure;
  threat/trust-boundary model including injection, SSRF/XSS and egress;
  SBOM, provenance, artifact verification, dependencies and credential scope.
- X10-X12: on-call and service owners, health/startup/shutdown, incident and
  restore exercises; config schemas, feature flags/kill switches and drift;
  expand/contract migrations, backfills, mixed versions and rollback limits.
- X13-X14: evaluation datasets, prompt/model/retrieval versions, regression
  and red-team tests; durable agent state, memory retention, per-action
  permissions, approval gates, iteration/token/cost limits and termination.
- X15-X16: offline/sync, accessibility, localization/time zones, consent,
  degraded states and upgrade compatibility; unit economics, egress/token
  budgets, resource utilization, vendor concentration and data export/exit.

## Decision frontier

List unresolved high-impact questions, alternatives, cost/security effects,
blocked phases, owner and revisit date/trigger. Use grilling for those
questions only. Discovery may be approved while dependent implementation
remains blocked. A guessed answer is not an approved decision.
