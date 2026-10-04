# Conditional architecture patterns

Read triggered rows while designing the plan; record selection, alternatives,
tradeoffs and NFR/ADR/test references. Do not scaffold all patterns or promote
a distributed architecture merely because it appears in the catalog.

| Trigger | Decision and simpler alternative | Required failure evidence |
| --- | --- | --- |
| Database write plus external event | Transactional outbox/inbox and idempotent consumers; compare one transaction/no event | Crash between commit and publish, duplicate delivery, poison event/redrive |
| Bursts or slow consumers | Bounded queues, backpressure, admission control/load shedding; compare synchronous bounded work | Saturation, queue expiry, fairness and recovery without retry storm |
| Dependency failure crosses boundaries | Bulkheads, timeout budgets, circuit breakers and graceful degradation | Hanging/down dependency, bounded retries with jitter, recovery probes |
| Long-running or interruptible work | Durable workflow/state machine; compare a simple transactional job | Crash/restart, cancellation, duplicate step, stuck-state recovery |
| Cross-service business transaction | Saga with explicit compensation; compare co-located transaction | Partial success, failed compensation, irreversibility and manual repair |
| Repeated expensive reads | Cache placement, keys, TTL/invalidation, stampede protection; compare direct reads | Stale data, tenant-key collision, cold start and cache outage |
| Schema/app rolling changes | Expand/contract, backfill, mixed-version compatibility | Old/new client coexistence, interrupted backfill and rollback limit |
| Risky runtime change | Feature flag/kill switch, canary or blue-green with measurable abort | Failed cohort, rollback, stale flag and dependency/schema compatibility |
| Legacy boundary migration | Strangler/anti-corruption boundary; compare in-place refactor | Routing rollback, data reconciliation and duplicate side effects |
| Concurrent state updates | Constraints/optimistic concurrency before distributed lock/consensus | Conflicting writes, expired lease, fencing and partition behavior |
| Read/write models differ | CQRS independently of event sourcing; compare single model | Projection lag, replay/schema evolution, reconciliation |
| Multi-tenant contention or sensitive data | Isolation boundary and quotas; compare explicit single-tenant design | Cross-tenant access/search/cache/AI leakage and noisy-neighbor load |

Document protocol choice (REST/GraphQL/gRPC), serialization/schema evolution,
DNS/TLS ownership, WebSocket reconnect/authentication and TCP/UDP constraints
in interfaces. Document store choice, durability, indexing, connection limits,
replicas and sharding triggers in data/platform decisions. Replication is not
a tested backup; SQL/NoSQL, cache/search/vector stores are independent choices.

For AI product workloads, decide model routing/fallback, retrieval provenance
and freshness, embedding version/reindex strategy, tenant-aware semantic cache,
evaluation thresholds and untrusted-tool-output handling. Enforce tool allowlists,
least privilege, confirmation boundaries and bounded autonomy. Developer
CodeGraph or GitHub MCP does not make AI01-AI08 or X13-X14 applicable.

Outbox decisions must include duplicate delivery and idempotent consumers,
as explained in [AWS transactional outbox guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html).
Require tested recovery objectives rather than backup configuration alone,
following [AWS disaster recovery guidance](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/plan-for-disaster-recovery-dr.html).
