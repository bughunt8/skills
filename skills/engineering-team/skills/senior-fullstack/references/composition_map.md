# Fullstack Engineer — Composition Map

**Principle (Karpathy #2, Simplicity First):** do not reimplement scope that the POWERFUL-tier engineering specialists already own. This skill is the *fullstack orchestrator*; the specialists are the *implementers*. Fork into them — do not duplicate them.

Use this routing table from the senior-fullstack skill. The advertised `cs-fullstack-engineer` agent and `/cs:fullstack-review` command are BLOCKED, absent. Do not emit an Agent call or slash invocation for them. The skill file is not an agent substitute.

## Dispatch boundaries

Resolve every linked provider against the repository root and require an authorized native host binding to that exact file. If the host accepts only ambiguous bare names, cannot register the required agent role, or lacks the required tools, mark that branch BLOCKED and ask the user to select or configure a provider. A document and an existing file do not prove host registration, agent execution, or downstream dependency closure.

Skill providers and agent files are different dispatch kinds. Call one model-invoked skill per loader operation. For agents, verify the exact file and role binding before dispatch. Use `context: fork` only when the authorized host supports it, not as an assumed capability. Return a ≤ 200-word digest with provider path, output artifact path, findings and unresolved checks. A required preflight or pre-commit branch that cannot run blocks stack locking, commit or launch, not just its digest.

Native [grilling](../../../../productivity/grilling/SKILL.md) is the explicit model preflight target. It asks frontier rounds and waits for shared-understanding confirmation. It is not an alias for missing `cs-grill-master` or human-only `grill-me` / `grill-with-docs`. Keep the local [forcing questions](forcing_questions.md) one-question-per-turn intake unchanged. Read those first when inputs are unknown. If domain boundaries need a separate approved modeling task, resolve and call [domain-modeling](../../../../engineering/domain-modeling/SKILL.md) independently after approval. Passive glossary reads do not invoke it. Never call either human wrapper from a model, even when this skill was user-invoked.

The `cs-grill-master` agent is BLOCKED, absent, and never auto-substituted. The table's native grilling route is an explicit skill-level behavior change, not evidence that the old role exists.


## Composition routing table

| User concern | Fork into | When to fork | Path |
|---|---|---|---|
| API contract / REST + GraphQL design / breaking change risk | api-design-reviewer | After Q1–Q3 of the forcing-question library reveal API surface area | [api-design-reviewer](../../../../engineering/skills/api-design-reviewer/SKILL.md) |
| Database schema / migration safety / index strategy | database-designer + migration-architect | After Q4 (traffic forecast) — read/write ratio drives schema choice | [database-designer](../../../../engineering/skills/database-designer/SKILL.md) + [migration-architect](../../../../engineering/skills/migration-architect/SKILL.md) |
| Bundle size, frontend perf, server response perf | performance-profiler | After Q7 success criteria include a latency/LCP target | [performance-profiler](../../../../engineering/skills/performance-profiler/SKILL.md) |
| Reliability target / SLO / error budget | slo-architect | After Q7 lists an uptime or p99 SLA | [slo-architect](../../../../engineering/slo-architect/skills/slo-architect/SKILL.md) |
| CI/CD pipeline (multi-language fullstack) | ci-cd-pipeline-builder | After Q2 cadence is daily / per-PR | [ci-cd-pipeline-builder](../../../../engineering/skills/ci-cd-pipeline-builder/SKILL.md) |
| Dependency vulnerability + license risk | dependency-auditor | Before every major release; before any production push | [dependency-auditor](../../../../engineering/skills/dependency-auditor/SKILL.md) |
| Monorepo tooling (Turbo / Nx / pnpm workspaces) | monorepo-navigator | When team size ≥ 6 and the codebase houses multiple deployable surfaces | [monorepo-navigator](../../../../engineering/skills/monorepo-navigator/SKILL.md) |
| API test generation + contract tests | api-test-suite-builder | After API contract is stable | [api-test-suite-builder](../../../../engineering/skills/api-test-suite-builder/SKILL.md) |
| Observability + golden signals + alert design | observability-designer | Concurrent with SLO design | [observability-designer](../../../../engineering/skills/observability-designer/SKILL.md) |
| Architecture onboarding doc for a new team member | codebase-onboarding | When ≥ 3 engineers will touch the code in 90 days | [codebase-onboarding](../../../../engineering/skills/codebase-onboarding/SKILL.md) |
| Hardening: AuthZ/AuthN, threat model, sensitive-data handling | senior-security + adversarial-reviewer | Before public launch; before handling PII/PHI/PCI data | [senior-security](../../../../engineering-team/skills/senior-security/SKILL.md) + [adversarial-reviewer](../../../../engineering-team/skills/adversarial-reviewer/SKILL.md) |
| Pre-commit code review (Karpathy 4 principles) | karpathy-reviewer agent, corrected from cs-karpathy-reviewer | Before EVERY commit this skill produces | [karpathy-reviewer agent](../../../../engineering/karpathy-coder/agents/karpathy-reviewer.md) |
| Pre-flight grill on a draft architecture | grilling skill, explicit preflight rebinding | Before locking the stack picks | [grilling](../../../../productivity/grilling/SKILL.md); legacy cs-grill-master remains BLOCKED |

## Composition rules

1. **Resolve and bind the exact provider first.** Fork only if the authorized host supports it. Stop on missing role bindings or capability gaps; return a ≤ 200-word digest after each completed branch.
2. **One sub-skill at a time.** Matt Pocock's depth-first rule. Finish the API contract branch before opening the database branch.
3. **Honor sub-skill outputs as inputs.** If `database-designer` recommends a schema, the next call to `api-design-reviewer` must use that schema, not invent one.
4. **Never reimplement specialist scope.** If the user asks "what's the right index strategy?" do not answer with handcrafted advice — fork into `database-designer`.
5. **Document the chain.** Every artifact this skill produces must list the sub-skills it invoked, in order, with the digest paths.

## Capability boundaries

- `api-design-reviewer` covers REST conventions and breaking-change review. GraphQL-specific coverage is unverified, so request explicit specialist or user review for GraphQL gaps rather than claim that this binding covers them.
- `senior-security` supplies STRIDE/DREAD threat modeling and security routing. `adversarial-reviewer` reviews code. Neither binding certifies compliance or promises every hardening capability.
- `observability-designer` owns dashboards, signals and alert noise. Authoritative SLO mathematics and error-budget review stay with the exact `slo-architect` provider, not another same-name implementation.
- `dependency-auditor` uses offline manifest and lockfile patterns. Its output does not establish current-CVE completeness. Record any advisory freshness gap before release.
- Multi-target `+` rows require separate sequential calls. Cloud `/` alternatives require an explicit AWS, Azure or GCP choice before dispatch. Provider outputs feed the next branch. Never silently pick a sibling.

## Anti-patterns

- ❌ Calling all sub-skills at the start "to be thorough." Burns context, produces noise.
- ❌ Skipping `karpathy-reviewer` before committing. Every commit from this skill must pass the diff-noise gate.
- ❌ Implementing what `api-design-reviewer` would have caught (e.g., inconsistent REST verbs). Fork first; commit second.
- ❌ Treating this skill's recommendations as approvals. Architecture choices must be sign-off-able by a named engineer; this skill never auto-approves.

## When to escalate out of fullstack

- Pure-engineering org design, team topology, manager triggers → [cs-vpe-advisor](../../../../c-level-advisor/c-level-agents/agents/cs-vpe-advisor.md) with an authorized native agent-role binding.
- Strategic company-level build-vs-buy → `cs-cto-advisor` is BLOCKED, absent. Ask the user to select a provider, with explicit approved rebinding for any skill-level alternative.
- AI/ML pipelines → choose [senior-ml-engineer](../../../../engineering-team/skills/senior-ml-engineer/SKILL.md) for pipelines/serving or [senior-prompt-engineer](../../../../engineering-team/skills/senior-prompt-engineer/SKILL.md) for prompt work, according to the actual concern.
- Warehouse, lakehouse, dbt → [senior-data-engineer](../../../../engineering-team/skills/senior-data-engineer/SKILL.md).
- Pure security threat model → [cs-ciso-advisor](../../../../c-level-advisor/c-level-agents/agents/cs-ciso-advisor.md) for strategic review with an authorized native agent-role binding, or [senior-security](../../../../engineering-team/skills/senior-security/SKILL.md) for tactical threat modeling.

## References

- Karpathy 4 principles, passive read → [karpathy-principles.md](../../../../engineering/karpathy-coder/skills/karpathy-coder/references/karpathy-principles.md)
- Historical Matt Pocock attribution stays in [forcing_questions.md](forcing_questions.md). The legacy `forcing_question_patterns.md` resource is BLOCKED, absent; do not use an archive or manufacture a path. Native grilling is linked above as an explicit behavior change.
- Path-B 11-file contract, passive read → [business-operations/CLAUDE.md](../../../../business-operations/CLAUDE.md)
