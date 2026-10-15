# Skill invocation policy template

Use for the proposed `.agents/invocation.md`, not as another SKILL.md.
Merge existing policy, replace inventory placeholders, and link the generated
file from AGENTS.md. In the generated plan and handoff replace template links
with the actual repository policy path. This is an original native profile,
not a copy of upstream harness setup.

```markdown
# Skill invocation and authority

AGENTS.md is the canonical instruction entry point. This policy constrains
companion skills without modifying their raw vendor bodies.

## Who may invoke

- User-invoked skills require an explicit human command. Neither a
  model-invoked nor a user-invoked skill may tool-call another user-invoked
  skill. Tell the user which command is needed and why.
- Model-invoked skills may be reached by the user or by the runtime's native
  Skill loader. Pass one skill name per call. Two dependencies need two
  separate calls, not one call with two names.
- Reading configuration or seed documents as data is not invocation.
  Reading a glossary for vocabulary is passive. Active domain changes use
  domain-modeling only within approved document-edit scope.
- Inspect the host-maintained .agents/skill-dependencies.json if present
  and verify names, invocation classification, resources and transitive
  dependencies against installed files. Do not assume the registry is
  present, correct or an enforcement mechanism.

## Verified installed inventory

User-invoked: REPLACE_WITH_VERIFIED_USER_ONLY_NAMES
Model-invoked: REPLACE_WITH_VERIFIED_MODEL_NAMES
Alias availability: REPLACE_WITH_VERIFIED_LOCAL_ALIASES_OR_UNAVAILABLE
Runtime classification enforcement: REPLACE_WITH_CHECKED_BEHAVIOR_OR_GAP

setup-matt-pocock-skills is user-only. Preserve working tracker, triage and
domain configuration. Missing configuration requires an approved native
configuration change or the user's independent /setup-matt-pocock-skills
command, never an automatic Skill call.
grill-me and grill-with-docs are user-only. The local /grill-me-with-docs
compatibility alias, if provided, points to /grill-with-docs; the vendor name
remains grill-with-docs. implement-spec and retro also require human commands.

## Profile guards

AGENTS.md only; do not create or update CLAUDE.md, Claude.md, .claude/ or
Claude integrations. Preserve unrelated existing files. GitHub Issues own
ticket state. Retain the repository's canonical .specs/ behavioral authority,
domain GLOSSARY vocabulary and ADR decisions through pointers, not copies.
During review, read CODING_STANDARDS.md or its existing equivalent for judgement.
Mechanical violations belong in deterministic checks, not more standards prose.

The approved repository plan bounds changes and phases. Native review,
readiness, Epic/Feature/Story, evidence and completion gates override vendor
shortcuts. Production release has separate authority.
No automatic resets, destructive worktree cleanup, branch deletion, commits,
pushes, merges or deployment. Preserve dirty/untracked work and seek exact
action approval. No self-approval or self-merge.

prototype may skip tests only in an explicitly approved, isolated throwaway
scope. Production adoption is separate tested implementation, never direct
promotion. retro recommends environment changes; writes require separate
approval, including global configuration.

## Verification limits

This file documents reachability and safety policy; it alone neither grants
nor enforces permissions. Runtime loader controls, tool permissions, GitHub
rules and CI must be tested separately. Report unavailable enforcement as
documented only or blocked, never verified.
```
