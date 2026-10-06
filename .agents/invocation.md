# Skill invocation policy

This policy governs the repository's integration. Installing it does not change
the host's loader or tool permissions.

## Authority and reachability

Human-only providers require an explicit human command, including when their
caller is itself human-invoked. A human-only skill may call a model-invoked
provider, but never another human-only provider. These are the upstream rules,
not permission inferred from an approved setup plan.
[Pinned invocation policy](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/.agents/invocation.md)

For the 27 Matt providers, `disable-model-invocation: true` pairs with
`policy.allow_implicit_invocation: false` in `agents/openai.yaml`. Model
providers omit both disabling settings.
[Pinned invocation policy](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/.agents/invocation.md)

The historical `github-repository-setup` snapshot nests its human-only flag
under `metadata`.
[Historical setup metadata](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/github-repository-setup/SKILL.md)

The reviewed local integration must place `disable-model-invocation: true`
and `argument-hint` at the top level, and supply required Codex metadata with
`policy.allow_implicit_invocation: false`. Preserve human-only reachability,
not the unsupported historical nesting. The checker rejects a nested-only
setup flag, a missing Codex file, pair disagreement and unexplained file drift.

Repository instructions, human approvals, least-privilege credentials, and the
existing SDD gates take precedence over a skill's commit, publication, cleanup,
or delegation defaults.
[Repository authority](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/AGENTS.md),
[SDD approval protocol](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/spec-driven-development/references/review.md)

## Exact provider resolution

Run the read-only checker against the installed repository before dispatch:

```bash
python3 scripts/check_skill_dependencies.py --root /path/to/repository
python3 scripts/check_skill_dependencies.py --root /path/to/repository --include-legacy
python3 scripts/check_skill_dependencies.py --root /path/to/repository \
  --resolve grilling --invoker model --caller grill-me
```

A successful resolver prints the absolute path to the registered `SKILL.md`.
It does not invoke the skill. The host must use a qualified loader that binds
that exact provider, or verify its native loader selected that same path. If
the loader accepts only ambiguous bare names, block dispatch. Do not resolve
Matt `research` and then call an unqualified `research` loader.

There are two distinct `research` providers in the audited repository:
Matt's `skills/engineering/research/SKILL.md` and the hybrid router's
`skills/research/research/skills/research/SKILL.md`.
[Matt provider](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/research/SKILL.md),
[Hybrid provider](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/research/research/skills/research/SKILL.md)

The resolver refuses bare `research` without a declared caller scope. Matt's
wayfinding scope selects the native engineering provider:

```bash
python3 scripts/check_skill_dependencies.py --root /path/to/repository \
  --resolve research --invoker model --caller wayfinder
```

That scope is appropriate because wayfinder explicitly dispatches Matt's
research discipline from its research tickets.
[Wayfinder research dispatch](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/wayfinder/SKILL.md#L77)

Only declared providers are resolved. The hybrid router remains preserved but
has no model caller scope in this Matt-focused registry. Do not silently select
it or rename it. A separate approved router binding is required.

When `--caller` is supplied for model dispatch, the resolver validates the
declared caller and its operative graph or explicit local scope. Without a
caller on a unique name, it checks provider reachability only. It does not prove
that a currently running caller has authorization to use that provider.

## Qualified legacy consumers

The same registry now contains `legacy_bindings` for the three senior-engineer
consumers and the explicit PM retrospective command. The structural helper
validates concrete map links, consumer instruction hashes and dispatch kinds.
Use `--include-legacy` in the repository gate. It does not prove a native host
registered an agent or can bind an exact file.

```bash
python3 scripts/check_skill_dependencies.py \
  --resolve-legacy-target skills/productivity/grilling/SKILL.md \
  --caller senior-backend --invoker model
python3 scripts/check_skill_dependencies.py --resolve-pm-retrospective --invoker user
python3 scripts/check_skill_dependencies.py --resolve retro --namespace matt --invoker user
```

Human `retro` without a namespace is ambiguous. PM sprint retrospectives use
the installed `/cs:pm` inquiry, never an alias to Matt's human-only environment
review. Missing wrappers are blocked, and agent definitions are not Skill
targets. Conditional routes retain their separate approval and host requirements.
Read [legacy binding recovery](../docs/legacy-harness-bindings.md) before
regenerating inventories or resuming an old loop state.

## Human aliases

Expand these commands before invocation while keeping the invoker as `user`:

| Human request | Canonical provider |
| --- | --- |
| `/grill-me-with-docs` | `skills/engineering/grill-with-docs/SKILL.md` |
| `/setup-github-repository` | `skills/engineering/github-repository-setup/SKILL.md` |

The first canonical provider is human-only upstream, and the native setup
provider already treats the second spelling as request wording.
[Grill with docs](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/grill-with-docs/SKILL.md),
[Native setup wording](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/github-repository-setup/SKILL.md)

An alias binds its registered `provider_path` directly, not a second bare-name
lookup. It can therefore expand safely even when the canonical name has another
installed provider. An unscoped canonical name still fails if ambiguous.

No alias is a new `SKILL.md`, copied provider, wrapper, or Skill-tool call to a
human-only target. The resolver rejects alias cycles, a wrong alias path, a
model-origin alias request, and an installed alias wrapper. If the host cannot
expand a command before invocation, display the canonical human command and
stop. A returned path is not evidence that an alias was installed in the host.

## Dependency classes

- Operative model dependencies are current Skill-tool instructions, including
  those inside worker instructions.
- Imperative slash calls are operative too. Matt's `implement` still uses
  `Use /tdd` and `use /code-review`, so the registry retains those two edges.
  [Implement](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/implement/SKILL.md)
- Human setup prerequisites are configuration or a request for an independent
  human command, not model edges. Wayfinder's tracker fallback remains
  conditional rather than an unconditional setup blocker.
  [Setup prerequisite ADR](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/.agents/adr/0001-explicit-setup-pointer-only-for-hard-dependencies.md),
  [Wayfinder fallback](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/wayfinder/SKILL.md)
- Passive glossary/ADR reads do not invoke `domain-modeling`.
  [Passive domain rule](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/.agents/invocation.md)
- Router labels, workflow examples, future handoff suggestions and attribution
  are not dispatch. `ask-matt` and `handoff` remain human routing surfaces.
  [Ask Matt](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/ask-matt/SKILL.md),
  [Handoff](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/productivity/handoff/SKILL.md)

Call one model-invoked provider per native loader operation. A step needing
`grilling` and `domain-modeling` requires two independent resolutions and calls.
[Two-call contract](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/.agents/invocation.md)

## Worker and approval boundaries

Wayfinder's user-authored Notes can name further skills, while Matt research
starts a background reading worker.
[Dynamic Notes](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/wayfinder/SKILL.md#L124),
[Research worker](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/research/SKILL.md)

The host must budget those workers. Assign a numbered reading job, sources,
output path, timeout and token limit. Permit one leaf reading worker per
research job, no reloading the dispatcher, no further delegation and no
self-dispatch. Resolve dynamic Notes targets individually; reject human-only
targets and undeclared or ambiguous providers. A static acyclic skill graph
does not bound worker recursion or verify these runtime budgets.

Keep GitHub Issues authoritative, PRs as delivery records, optional Projects,
serialized claims/merges, independent review, and separate release authority.
Do not configure Claude clients or create/modify Claude instruction files in
this setup profile.
[GitHub-native contract](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/github-repository-setup/references/agentic-development.md),
[Tooling scope](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/github-repository-setup/references/tooling.md)

Prototype's upstream instructions deliberately skip tests and error handling.
[Prototype instructions](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/prototype/SKILL.md)

Allow that exception only after approval of a throwaway discovery question,
isolated scratch location/branch, data scope and disposal/capture plan. Do not
use it in an approved production SDD task or as implementation evidence. Record
manual walkthrough results; production adoption needs a separate reviewed,
tested implementation.

SDD still stops at phase approvals and builds one fresh, authorized atomic
task at a time. Do not substitute `implement-spec` orchestration for those
gates, manufacture human approval, or turn a structural pass into proof of
implementation.
[SDD commands and gates](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/spec-driven-development/SKILL.md),
[SDD human authority](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/spec-driven-development/references/review.md)

## What a pass means

The checker validates the declared 27-provider pinned bundle, YAML/Codex pairs,
owned file hashes, graph evidence/closure/cycles, aliases, and importer source
paths once import markers or Matt manifest entries exist. It is read-only.
`--include-legacy` additionally checks the three qualified senior consumers and
PM command binding. The executable harness separately validates live providers
against its regenerated 18 inventories and persisted v2 task bindings.

It is not runtime enforcement, a sandbox, a signing service, an authenticated
approval channel, a license-rights audit, or whole-repository dispatch closure.
Treat registry/script files as trusted reviewed inputs. Do not bypass a failed
check by editing source hashes or graph entries to match unexplained drift.
The historical inbound inventory is not a current whole-library registration
record. Missing wrappers stay blocked, and actual host roles and integrations
still require separate qualification.
