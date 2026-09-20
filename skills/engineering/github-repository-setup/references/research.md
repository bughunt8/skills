# Research and design rationale

Reviewed 2026-09-21 in Hong Kong. These sources support the profile; its
conservative policy choices are identified separately from platform behavior.

## GitHub practices

- GitHub recommends clear, scoped agent tasks with acceptance criteria, file
  hints, and build/test instructions. That supports the issue form and
  repository entry point, rather than vague feature assignments.
  [Agent task guidance](https://docs.github.com/copilot/how-tos/agents/copilot-coding-agent/best-practices-for-using-copilot-to-work-on-tasks).
- Native sub-issues represent parent/child work and can be nested. Native
  dependencies separately identify blockers. Keep both relationships and
  provide an explicit fallback rather than treating a checklist as a dependency.
  [Sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues)
  and [dependencies](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies).
- Closing keywords are interpreted for the default branch; merging into a
  different branch does not automatically close the issue. Use explicit
  staging verification and a chosen closure boundary.
  [PR-to-issue linking](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue).
- Rulesets can enforce PRs and checks, depend on plan/visibility, and layer
  with existing rules. Inspect effective settings and bypasses before claiming
  the repository is protected.
  [Rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets).
- GitHub recommends full-length action commit pins and least-privilege tokens,
  and warns about script injection and privileged untrusted PR checkout.
  [Actions secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use).
- Dependency review availability differs by repository visibility and security
  entitlement. Do not make an unavailable scanner a promised enforcement gate.
  [Dependency review](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review).

## AI-CMO adaptation

The inspected AI-CMO revision was
`5cb085f6f0046515c3359117a6f82e2c3dffd0da`. Its
[agent instructions](https://github.com/Profit-Rise-Consulting/ai-cmo/blob/5cb085f6f0046515c3359117a6f82e2c3dffd0da/AGENTS.md)
and
[execution protocol](https://github.com/Profit-Rise-Consulting/ai-cmo/blob/5cb085f6f0046515c3359117a6f82e2c3dffd0da/docs/agents/execution-protocol.md)
informed issue-scoped worktrees, requirement/ADR traceability, tested
architecture boundaries, independent review, and separate release authority.
These are reusable patterns, not a mandate to copy the product's topology.

The adaptation deliberately does not copy Plane references, sync workflows,
product package boundaries, tenant-specific checks, hostnames, secrets, or
deployment commands. It also avoids the reference protocol's assumptions that
an assignment prevents concurrent claims or that a staging merge necessarily
closes an issue. A serialized dispatcher is this profile's recommended policy;
it is not presented as a native GitHub transactional lock.

## Local integration and scope

The inspected skills staging revision was
`ec4e89d29d3a0dca56c809bdf7b8ba5816cf8674`. The canonical names are
[`github-repository-setup`](https://github.com/bughunt8/skills/blob/ec4e89d29d3a0dca56c809bdf7b8ba5816cf8674/skills/engineering/github-repository-setup/SKILL.md)
and
[`setup-matt-pocock-skills`](https://github.com/bughunt8/skills/blob/ec4e89d29d3a0dca56c809bdf7b8ba5816cf8674/skills/engineering/setup-matt-pocock-skills/SKILL.md).
The latter defines tracker configuration, five triage roles, instruction-file
selection, and context/ADR layout. This profile explicitly overrides its
Claude-first selection because the user does not use Claude; AGENTS.md is
the entry point and Claude files/configuration are excluded. Its linked seeds were absent in this
snapshot, so this profile supplies original fallback templates without
modifying that separate skill or importing third-party text.

The update preserves the upstream catalog workflow in `catalog-setup.md`.
The target remains a repository-managed skill, not an installation into a
personal skill library. Repository settings, live agent services, and
production deployment are outside this skill-authoring change.

CodeGraph guidance uses the
[upstream README](https://github.com/colbymchenry/codegraph) and
[indexing guide](https://colbymchenry.github.io/codegraph/guides/indexing/).
The installer configures agent clients separately from per-project indexing
and can modify client permissions, so this profile requires a scoped,
non-Claude configuration review rather than unrestricted auto-install.
