# Backend Engineer — Composition Map

**Principle (Karpathy #2, Simplicity First):** do not reimplement scope that the POWERFUL-tier specialists already own. This skill is the *backend orchestrator*; the specialists are the *implementers*.

Use this routing table from the senior-backend skill. The advertised `cs-backend-engineer` agent and `/cs:backend-review` command are BLOCKED, absent. Do not emit an Agent call or slash invocation for them. The skill file is not an agent substitute.

## Dispatch boundaries

Resolve every linked provider against the repository root and require an authorized native host binding to that exact file. If the host accepts only ambiguous bare names, cannot register the required agent role, or lacks the required tools, mark that branch BLOCKED and ask the user to select or configure a provider. A document and an existing file do not prove host registration, agent execution, or downstream dependency closure.

Skill providers and agent files are different dispatch kinds. Call one model-invoked skill per loader operation. For agents, verify the exact file and role binding before dispatch. Use `context: fork` only when the authorized host supports it, not as an assumed capability. Return a ≤ 200-word digest with provider path, output artifact path, findings and unresolved checks. A required preflight or pre-commit branch that cannot run blocks stack locking, commit or launch, not just its digest.

Native [grilling](../../../../productivity/grilling/SKILL.md) is the explicit model preflight target. It asks frontier rounds and waits for shared-understanding confirmation. It is not an alias for missing `cs-grill-master` or human-only `grill-me` / `grill-with-docs`. Keep the local [forcing questions](forcing_questions.md) one-question-per-turn intake unchanged. Read those first when inputs are unknown. If domain boundaries need a separate approved modeling task, resolve and call [domain-modeling](../../../../engineering/domain-modeling/SKILL.md) independently after approval. Passive glossary reads do not invoke it. Never call either human wrapper from a model, even when this skill was user-invoked.

The `cs-grill-master` agent is BLOCKED, absent, and never auto-substituted. The table's native grilling route is an explicit skill-level behavior change, not evidence that the old role exists.


## Composition routing table

| User concern | Fork into | When to fork | Path |
|---|---|---|---|
| API contract / REST / GraphQL design / breaking-change risk | api-design-reviewer | After Q1–Q3 reveal API shape | [api-design-reviewer](../../../../engineering/skills/api-design-reviewer/SKILL.md) |
| Schema design / ERD / normalization / indexing | database-designer + database-schema-designer | After Q1 (read/write ratio) is known | [database-designer](../../../../engineering/skills/database-designer/SKILL.md) + [database-schema-designer](../../../../engineering/skills/database-schema-designer/SKILL.md) |
| Zero-downtime schema migrations | migration-architect | Before any production schema change | [migration-architect](../../../../engineering/skills/migration-architect/SKILL.md) |
| SLO + SLI + error-budget design | slo-architect | After Q7 (SLO) is set | [slo-architect](../../../../engineering/slo-architect/skills/slo-architect/SKILL.md) |
| Observability / golden signals / alert design | observability-designer | Concurrent with SLO design | [observability-designer](../../../../engineering/skills/observability-designer/SKILL.md) |
| MCP server build (tools-from-OpenAPI) | mcp-server-builder | When backend exposes tools to LLM agents | [mcp-server-builder](../../../../engineering/skills/mcp-server-builder/SKILL.md) |
| CI/CD pipeline for backend service | ci-cd-pipeline-builder | After Q2 (tenancy) and Q5 (pattern) are set | [ci-cd-pipeline-builder](../../../../engineering/skills/ci-cd-pipeline-builder/SKILL.md) |
| Dependency vulnerability + license risk | dependency-auditor | Before every release | [dependency-auditor](../../../../engineering/skills/dependency-auditor/SKILL.md) |
| API test suite + contract tests | api-test-suite-builder | After API contract is stable | [api-test-suite-builder](../../../../engineering/skills/api-test-suite-builder/SKILL.md) |
| Security hardening / threat model / authZ | senior-security + adversarial-reviewer | Before public launch; before handling PII/PHI/PCI | [senior-security](../../../../engineering-team/skills/senior-security/SKILL.md) + [adversarial-reviewer](../../../../engineering-team/skills/adversarial-reviewer/SKILL.md) |
| Cloud architecture (AWS / Azure / GCP) | aws-solution-architect + azure-cloud-architect + gcp-cloud-architect | When infrastructure choice is the bottleneck | [aws-solution-architect](../../../../engineering-team/skills/aws-solution-architect/SKILL.md) / [azure-cloud-architect](../../../../engineering-team/skills/azure-cloud-architect/SKILL.md) / [gcp-cloud-architect](../../../../engineering-team/skills/gcp-cloud-architect/SKILL.md) |
| Feature-flag investment + cleanup | feature-flags-architect | After Q5 (pattern) is set; before per-PR cadence | [feature-flags-architect](../../../../engineering/feature-flags-architect/skills/feature-flags-architect/SKILL.md) |
| Chaos engineering / failure-injection experiments | chaos-engineering | After SLO is in place + stable | [chaos-engineering](../../../../engineering/chaos-engineering/skills/chaos-engineering/SKILL.md) |
| Pre-commit Karpathy review | karpathy-reviewer agent, corrected from cs-karpathy-reviewer | Before EVERY commit | [karpathy-reviewer agent](../../../../engineering/karpathy-coder/agents/karpathy-reviewer.md) |
| Pre-flight architecture grill | grilling skill, explicit preflight rebinding | Before locking pattern or DB choice | [grilling](../../../../productivity/grilling/SKILL.md); legacy cs-grill-master remains BLOCKED |
| RA/QM compliance evidence (HIPAA, ISO 27001, SOC2) | BLOCKED, compliance owner selection | After Q4 reveals regulated data | No single ra-qm-team SKILL.md entrypoint. Ask the user and named compliance owner to select the exact HIPAA / ISO 27001 / SOC2 provider. Domain directory is not dispatch. |

## Composition rules

1. **Resolve and bind the exact provider first.** Fork only if the authorized host supports it. Stop on missing role bindings or capability gaps; return a ≤ 200-word digest after each completed branch.
2. **One sub-skill at a time.** Matt Pocock's depth-first rule. Finish the DB branch before opening the API branch.
3. **Honor sub-skill outputs as inputs.** If `database-designer` recommends a schema, the next call to `api-design-reviewer` uses it.
4. **Never reimplement specialist scope.** If the user asks "what's my index strategy?" do not answer with handcrafted advice — fork into `database-designer`.
5. **SLO before scale.** If Q7 (SLO) is not set, don't burn cycles on caching / sharding / queue topology. Fork into `slo-architect` first.

## Capability boundaries

- `api-design-reviewer` covers REST conventions and breaking-change review. GraphQL-specific coverage is unverified, so request explicit specialist or user review for GraphQL gaps rather than claim that this binding covers them.
- `senior-security` supplies STRIDE/DREAD threat modeling and security routing. `adversarial-reviewer` reviews code. Neither binding certifies compliance or promises every hardening capability.
- `observability-designer` owns dashboards, signals and alert noise. Authoritative SLO mathematics and error-budget review stay with the exact `slo-architect` provider, not another same-name implementation.
- `dependency-auditor` uses offline manifest and lockfile patterns. Its output does not establish current-CVE completeness. Record any advisory freshness gap before release.
- Multi-target `+` rows require separate sequential calls. Cloud `/` alternatives require an explicit AWS, Azure or GCP choice before dispatch. Provider outputs feed the next branch. Never silently pick a sibling.

Regulated-data kill criteria remain in force. `ra-qm-team` is a domain, not a single provider. Decision-engine output mentioning it means BLOCKED user/compliance-owner selection, not dispatch or certification. Strategic CISO review does not substitute for the missing compliance evidence provider.

## Anti-patterns

- ❌ Recommending Kafka before naming a second team that needs it (premature event-driven).
- ❌ Recommending microservices before Q5 (team-size justification) passes.
- ❌ Designing API contracts without forking into `api-design-reviewer` (consistency, breaking-change risk).
- ❌ Skipping `karpathy-reviewer` before commit — every commit must pass the diff-noise gate.
- ❌ Auto-approving a production schema migration — every migration names the on-call + DBA approver.

## When to escalate out of backend

- Frontend integration → BLOCKED. `cs-frontend-engineer` is absent. Ask the user to select a provider, not an invented agent alias.
- Org design, capacity, hiring → [cs-vpe-advisor](../../../../c-level-advisor/c-level-agents/agents/cs-vpe-advisor.md) for engineering, or [cs-bizops-orchestrator](../../../../business-operations/agents/cs-bizops-orchestrator.md) for cross-functional operations. Require the matching native agent-role binding.
- Strategic company-level build-vs-buy → BLOCKED. `cs-cto-advisor` is absent. Any skill-level alternative needs the user's explicit selection and approved rebinding.
- AI/ML pipelines and serving → [senior-ml-engineer](../../../../engineering-team/skills/senior-ml-engineer/SKILL.md).
- Warehouse, dbt, lakehouse → [senior-data-engineer](../../../../engineering-team/skills/senior-data-engineer/SKILL.md).
- Pure security threat model → [cs-ciso-advisor](../../../../c-level-advisor/c-level-agents/agents/cs-ciso-advisor.md) for strategic review with an authorized agent-role binding, or [senior-security](../../../../engineering-team/skills/senior-security/SKILL.md) for tactical threat modeling.

## References

- Karpathy 4 principles, passive read → [karpathy-principles.md](../../../../engineering/karpathy-coder/skills/karpathy-coder/references/karpathy-principles.md)
- Historical Matt Pocock attribution stays in [forcing_questions.md](forcing_questions.md). The legacy `forcing_question_patterns.md` resource is BLOCKED, absent; do not use an archive or manufacture a path. Native grilling is linked above as an explicit behavior change.
- Path-B 11-file contract, passive read → [business-operations/CLAUDE.md](../../../../business-operations/CLAUDE.md)
- SLO canon, passive read → [slo_principles.md](../../../../engineering/slo-architect/skills/slo-architect/references/slo_principles.md)
