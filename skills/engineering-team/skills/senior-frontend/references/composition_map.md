# Frontend Engineer — Composition Map

**Principle (Karpathy #2, Simplicity First):** do not reimplement scope that the POWERFUL-tier specialists already own. This skill is the *frontend orchestrator*; the specialists are the *implementers*.

Use this routing table from the senior-frontend skill. The advertised `cs-frontend-engineer` agent and `/cs:frontend-review` command are BLOCKED, absent. Do not emit an Agent call or slash invocation for them. The skill file is not an agent substitute.

## Dispatch boundaries

Resolve every linked provider against the repository root and require an authorized native host binding to that exact file. If the host accepts only ambiguous bare names, cannot register the required agent role, or lacks the required tools, mark that branch BLOCKED and ask the user to select or configure a provider. A document and an existing file do not prove host registration, agent execution, or downstream dependency closure.

Skill providers and agent files are different dispatch kinds. Call one model-invoked skill per loader operation. For agents, verify the exact file and role binding before dispatch. Use `context: fork` only when the authorized host supports it, not as an assumed capability. Return a ≤ 200-word digest with provider path, output artifact path, findings and unresolved checks. A required preflight or pre-commit branch that cannot run blocks stack locking, commit or launch, not just its digest.

Native [grilling](../../../../productivity/grilling/SKILL.md) is the explicit model preflight target. It asks frontier rounds and waits for shared-understanding confirmation. It is not an alias for missing `cs-grill-master` or human-only `grill-me` / `grill-with-docs`. Keep the local [forcing questions](forcing_questions.md) one-question-per-turn intake unchanged. Read those first when inputs are unknown. If domain boundaries need a separate approved modeling task, resolve and call [domain-modeling](../../../../engineering/domain-modeling/SKILL.md) independently after approval. Passive glossary reads do not invoke it. Never call either human wrapper from a model, even when this skill was user-invoked.

The `cs-grill-master` agent is BLOCKED, absent, and never auto-substituted. The table's native grilling route is an explicit skill-level behavior change, not evidence that the old role exists.


## Composition routing table

| User concern | Fork into | When to fork | Path |
|---|---|---|---|
| WCAG audit, contrast checks, screen-reader gaps | a11y-audit | After Q7 (WCAG target) is set | [a11y-audit](../../../../engineering-team/a11y-audit/skills/a11y-audit/SKILL.md) |
| Bundle profiling, Lighthouse perf, runtime CPU/memory | performance-profiler | After Q2 (LCP target) is set | [performance-profiler](../../../../engineering/skills/performance-profiler/SKILL.md) |
| Cinematic / parallax / scroll-storytelling landing | epic-design | When `marketing-site` or `landing-page` profile applies | [epic-design](../../../../engineering-team/skills/epic-design/SKILL.md) |
| Pre-commit Karpathy review on changed files | karpathy-reviewer agent, corrected from cs-karpathy-reviewer | Before EVERY commit this skill produces | [karpathy-reviewer agent](../../../../engineering/karpathy-coder/agents/karpathy-reviewer.md) |
| Pre-flight architecture grill | grilling skill, explicit preflight rebinding | Before locking framework or rendering model | [grilling](../../../../productivity/grilling/SKILL.md); legacy cs-grill-master remains BLOCKED |
| Monorepo coordination (Turbo / Nx / pnpm) | monorepo-navigator | When frontend shares repo with backend / mobile / extension | [monorepo-navigator](../../../../engineering/skills/monorepo-navigator/SKILL.md) |
| Dependency vulnerability sweep | dependency-auditor | Before every major release | [dependency-auditor](../../../../engineering/skills/dependency-auditor/SKILL.md) |
| Visual / accessibility regression in CI | api-test-suite-builder + pw toolkit, separate scopes | After Q7 (WCAG target) is set | [api-test-suite-builder](../../../../engineering/skills/api-test-suite-builder/SKILL.md) + [pw](../../../../engineering-team/playwright-pro/skills/pw/SKILL.md) |
| Apple HIG / iOS / macOS / visionOS app review | apple-hig-expert | When the surface is Apple-platform-native | [apple-hig-expert](../../../../product-team/apple-hig-expert/skills/apple-hig-expert/SKILL.md) |
| AEO (Answer Engine Optimization) — visibility in LLM search | aeo | After Q5 (SEO-dependent surface) is confirmed | [aeo](../../../../marketing-skill/skills/aeo/SKILL.md) |
| SEO crawlability + meta + structured data | seo-audit, explicit label correction, optional | After Q5 (SEO-dependent surface) | [seo-audit](../../../../marketing-skill/skills/seo-audit/SKILL.md) only if installed, authorized and Q5 is SEO-dependent. No seo-auditor provider. Technical/on-page audit is not structured-data implementation. |
| API contract from the consumer side | api-design-reviewer | When frontend defines/consumes a new API contract | [api-design-reviewer](../../../../engineering/skills/api-design-reviewer/SKILL.md) |

## Composition rules

1. **Resolve and bind the exact provider first.** Fork only if the authorized host supports it. Stop on missing role bindings or capability gaps; return a ≤ 200-word digest after each completed branch.
2. **One sub-skill at a time.** Matt Pocock's depth-first rule. Finish the a11y branch before opening the perf branch.
3. **Honor sub-skill outputs as inputs.** `performance-profiler` produces a baseline; the next iteration of `senior-frontend` must respect that baseline.
4. **Never reimplement specialist scope.** If the user asks "what's my CLS?" do not hand-roll a check — fork into `performance-profiler`.
5. **Document the chain.** Every artifact lists the sub-skills invoked, in order.

## Capability boundaries

- `api-design-reviewer` covers REST conventions and breaking-change review. GraphQL-specific coverage is unverified, so request explicit specialist or user review for GraphQL gaps rather than claim that this binding covers them.
- `senior-security` supplies STRIDE/DREAD threat modeling and security routing. `adversarial-reviewer` reviews code. Neither binding certifies compliance or promises every hardening capability.
- `observability-designer` owns dashboards, signals and alert noise. Authoritative SLO mathematics and error-budget review stay with the exact `slo-architect` provider, not another same-name implementation.
- `dependency-auditor` uses offline manifest and lockfile patterns. Its output does not establish current-CVE completeness. Record any advisory freshness gap before release.
- Multi-target `+` rows require separate sequential calls. Cloud `/` alternatives require an explicit AWS, Azure or GCP choice before dispatch. Provider outputs feed the next branch. Never silently pick a sibling.

The corrected `pw` route is the Playwright Pro toolkit entrypoint, not an installed `playwright-pro` skill alias. Keep API/integration/contract tests with `api-test-suite-builder`; never invent its visual extension. Visual and accessibility browser regression use `pw`. Before using `/pw:` commands, agents, hooks, templates, TestRail or BrowserStack, verify plugin/tool installation and host support. Preserve generate → review, fix → full-suite rerun, and migrate → coverage parity checks. Credentials, remote integrations and test execution need their own authorization. A toolkit file does not prove those integrations work.

The a11y and Apple HIG rows bind the nested entrypoints, not stale engineering-team/skills or product-team/skills directories. AEO handles answer-engine visibility. Optional `seo-audit` handles technical/on-page audit only after Q5 and exact-path availability checks; neither implies full structured-data implementation.

## Anti-patterns

- ❌ Adding a third-party perf monitoring lib without checking it against the bundle budget from Q4.
- ❌ Implementing what `a11y-audit` would have caught (e.g., missing alt text, color contrast, focus traps).
- ❌ Skipping `karpathy-reviewer` before committing — every commit must pass the diff-noise gate.
- ❌ Treating shipped UI as a final product without the exact `pw` toolkit visual-regression baseline.

## When to escalate out of frontend

- Brand voice and copy → [content-creator](../../../../marketing-skill/skills/content-creator/SKILL.md) is a deprecated redirect, not a writer. `cs-content-creator` is BLOCKED, absent. Its documented [content-production successor](../../../../marketing-skill/skills/content-production/SKILL.md) is passive selection guidance only, not an automatic rebind. Ask the user to approve a direct successor binding before writing.
- Backend API design → `cs-backend-engineer` is BLOCKED, absent. The separate [api-design-reviewer](../../../../engineering/skills/api-design-reviewer/SKILL.md) skill can review REST contracts, but does not satisfy the missing engineer-agent handoff.
- iOS/macOS-native UI → `cs-apple-hig` is absent, not a callable conditional agent. Use the already-declared [apple-hig-expert skill alternative](../../../../product-team/apple-hig-expert/skills/apple-hig-expert/SKILL.md) when the surface is Apple-native.
- Marketing-site infrastructure choice, Astro vs Next vs Hugo → `cs-fullstack-engineer` is BLOCKED, absent. A marketing-site profile is not an agent registration. Ask the user to select a provider.

## References

- Karpathy 4 principles, passive read → [karpathy-principles.md](../../../../engineering/karpathy-coder/skills/karpathy-coder/references/karpathy-principles.md)
- Historical Matt Pocock attribution stays in [forcing_questions.md](forcing_questions.md). The legacy `forcing_question_patterns.md` resource is BLOCKED, absent; do not use an archive or manufacture a path. Native grilling is linked above as an explicit behavior change.
- Path-B 11-file contract, passive read → [business-operations/CLAUDE.md](../../../../business-operations/CLAUDE.md)
