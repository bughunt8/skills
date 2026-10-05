# Matt Pocock v1.3.1 dependency integration

## Installed scope

The upgrade imports the complete stable release through `scripts/sync_vendor.py`
at its existing native paths. It adds a read-only dependency checker, resolver,
regression tests and invocation policy. The checker does not invoke skills,
install a loader or grant worker permissions.

The release pin is `24fe0ef7737efae15c87225755e9f6f5965e4888`, and its manifest
lists 20 engineering providers and seven productivity providers at native
paths.
[Pinned release manifest](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/.claude-plugin/plugin.json)

The registry records each of those 27 providers, 79 upstream skill/resource
files, SHA-256 values, source paths, source URLs, invocation class and dependency
evidence. The MIT notice is a separately hashed legal resource.
[Stable source tree](https://github.com/mattpocock/skills/tree/24fe0ef7737efae15c87225755e9f6f5965e4888/skills),
[Upstream license](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/LICENSE)

Do not add a parallel `skills/mattpocock/` copy, rename native providers, relax
the lint baseline, or import root steering/glossary files as consumer policy.
[Repository import rules](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/AGENTS.md),
[Upstream root steering](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/CLAUDE.md)

## Validation and resolution

Requires Python 3.10+ and PyYAML. All checker operations are local and read-only:

```bash
python3 scripts/check_skill_dependencies.py --root /path/to/installed/repository
python3 scripts/check_skill_dependencies.py --root /path/to/installed/repository \
  --require-provenance
python3 scripts/test_skill_dependencies.py
```

`--root` defaults to the repository containing `.agents/` and
`scripts/`. That default deliberately fails if skill providers have not been
imported there. Tests build complete fixtures in system temporary directories
and clean them automatically. The checker itself creates no files.

For a portable test checkout, set `SKILL_DEPENDENCY_SOURCE_ROOT` to a verified
v1.3.1 upstream or installed native tree and `SKILL_DEPENDENCY_LOCAL_ROOT` to
the reviewed local setup/router tree. When these files are integrated at a
repository root containing the providers, tests use that root by default.
An isolated candidate requires these explicit source-root settings. Installed
scripts have no hardcoded workspace/audit checkout defaults. Set
`SKILL_DEPENDENCY_TEST_REPORT` only when a JSON report file is desired.

The registry is read from `<root>/.agents/skill-dependencies.json` when present,
otherwise from beside the installed scripts. This supports read-only validation
of an upstream snapshot using the installed registry.

Imported-mode detection uses any native Matt `PROVENANCE.md`/ownership marker
or Matt manifest source. Imported mode requires evidence for all 27 providers,
not just the first marked provider. It validates exact upstream path/commit
permalinks, MIT license hash, attribution pin and narrow ownership records.
The MIT hash covers the original notice bytes after the importer's exact
repository/commit attribution preface, when that preface is present.
If `skills/vendor.manifest.json` exists, it also verifies the 27
`mattpocock-<name>` source IDs, native destinations, release ref/pin and
one-root source mappings.

The mapping and provenance checks follow the importer-produced field/table
formats; importer-generated ownership files must never be fabricated in the
real repository.
[Importer provenance and ownership](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/scripts/sync_vendor.py),
[Repository ownership rule](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/AGENTS.md)

Auxiliary provider body hashes cover the installed local GitHub setup
adaptation and preserved hybrid research router. They are not Matt release
members or evidence that local adaptations equal the historical source URL.
After a reviewed local adaptation, deliberately update its auxiliary hash;
do not change the 79 upstream hashes to accommodate a vendor edit.

## Exact resolution and refusals

The resolver's only success output is the exact absolute `SKILL.md` path.
The host must load that qualified provider, or block when its loader cannot
bind the path. Resolving a path and then passing an ambiguous bare name to
another loader does not solve the collision. This script invokes nothing.

```bash
# Human alias expansion, before invocation
python3 scripts/check_skill_dependencies.py --root /repo \
  --resolve grill-me-with-docs --invoker user
# /repo/skills/engineering/grill-with-docs/SKILL.md

python3 scripts/check_skill_dependencies.py --root /repo \
  --resolve setup-github-repository --invoker user
# /repo/skills/engineering/github-repository-setup/SKILL.md

# Refused, exit 1: user-only target
python3 scripts/check_skill_dependencies.py --root /repo \
  --resolve grill-with-docs --invoker model
# ERROR: model invocation refused: user-only grill-with-docs

# Refused, exit 1: collision has no caller context
python3 scripts/check_skill_dependencies.py --root /repo \
  --resolve research --invoker model
# ERROR: ambiguous research: caller scope required; use --caller wayfinder for Matt research

# Matt's scoped provider, not the hybrid router
python3 scripts/check_skill_dependencies.py --root /repo \
  --resolve research --invoker model --caller wayfinder
# /repo/skills/engineering/research/SKILL.md
```

The canonical grill wrapper is human-only, the historical GitHub setup nests
its human-only metadata, and the two research bodies implement different workflows.
[Grill wrapper](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/grill-with-docs/SKILL.md),
[GitHub setup](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/github-repository-setup/SKILL.md),
[Matt research](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/research/SKILL.md),
[Hybrid research](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/research/research/skills/research/SKILL.md)

The alias exists in this resolver, not automatically in the host command UI.
There is no alias wrapper skill. Model callers cannot use either human alias.
A host that cannot expand a human alias before invocation must ask the human
to use the canonical command.

The reviewed setup migration must move the human-only flag and argument hint
to the top level and provide a required matching Codex pair. The registry hashes
both local setup files and rejects nested-only metadata. Human reachability is
preserved; unsupported nesting is not treated as runtime enforcement.

Human aliases bind their exact registered paths before invocation even when
another installed provider has the canonical name. Bare canonical resolution
without a declared scope remains fail-closed on ambiguity. Model invocation
of a registered human-only target is refused regardless of that collision.

## Operative native dependency graph

There are 18 unique operative edges in the pinned bodies, including two
imperative slash calls from `implement`. Their targets are model-invoked; the
pinned native graph is acyclic and closed within this release.
[Invocation contract](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/.agents/invocation.md),
[Stable bodies](https://github.com/mattpocock/skills/tree/24fe0ef7737efae15c87225755e9f6f5965e4888/skills)

| Caller | Operative model providers | Exact evidence |
| --- | --- | --- |
| grill-with-docs | grilling, domain-modeling | [Two separate calls](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/grill-with-docs/SKILL.md#L7) |
| triage | grilling, domain-modeling | [Conditional interview](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/triage/SKILL.md#L76) |
| improve-codebase-architecture | codebase-design, grilling, domain-modeling | [Vocabulary](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/improve-codebase-architecture/SKILL.md#L13), [decision interview and domain work](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/improve-codebase-architecture/SKILL.md#L64) |
| tdd | codebase-design | [Interface-shape condition](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/tdd/SKILL.md#L26) |
| wayfinder | research, prototype, grilling, domain-modeling | [Ticket types](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/wayfinder/SKILL.md#L77) |
| implement | tdd, code-review | [Imperative slash wording](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/implement/SKILL.md#L9) |
| implement-spec | tdd, code-review | [Worker call](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/implement-spec/SKILL.md#L29), [integration review](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/implement-spec/SKILL.md#L36) |
| retro | writing-for-agents | [Writing guide](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/retro/SKILL.md#L11) |
| grill-me | grilling | [Grilling call](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/productivity/grill-me/SKILL.md#L7) |

The checker compares registry targets with a bounded parser for the exact
pinned call syntax, then validates every declared line/text/URL evidence
occurrence. It is not a universal natural-language call detector. Changed
source syntax requires a deliberate parser review, not just new hashes.

Human tracker/label setup requirements are a separate class for `to-spec`,
`to-tickets`, `triage`, `code-review` and `implement-spec`; wayfinder permits
local-markdown fallback when no tracker is supplied.
[Hard setup ADR](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/.agents/adr/0001-explicit-setup-pointer-only-for-hard-dependencies.md),
[Code review setup](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/code-review/SKILL.md),
[Implement-spec setup](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/implement-spec/SKILL.md),
[Wayfinder fallback](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/wayfinder/SKILL.md)

`ask-matt` router suggestions, future `handoff` recommendations, passive
glossary/ADR reads and `pr/CREDITS.md` attribution are not current model calls.
[Ask Matt](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/ask-matt/SKILL.md),
[Handoff](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/productivity/handoff/SKILL.md),
[Passive domain rule](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/.agents/invocation.md),
[PR credits](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/pr/CREDITS.md)

Owned-resource backlinks are document navigation, not operative graph cycles.
[Prototype resources](https://github.com/mattpocock/skills/tree/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/prototype),
[Design resources](https://github.com/mattpocock/skills/tree/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/codebase-design),
[Writing resources](https://github.com/mattpocock/skills/tree/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/productivity/writing-for-agents)

## Actual inbound-reference inventory

`inbound-reference-inventory.json` records 392 selected name-reference
occurrences in 137 files, from 3,451 readable UTF-8 files at repository commit
`5f132c008d5c8d261b4fa30e94899151c186ce94`, outside the 27 native provider
directories; ten binary/symlink files are listed as skipped.
[Audited repository snapshot](https://github.com/bughunt8/skills/tree/5f132c008d5c8d261b4fa30e94899151c186ce94)

This is a reproducible candidate inventory, not 392 verified calls. It matches
slash labels, backtick names, `skill:` YAML, native `SKILL.md` paths and Skill-tool
lines. Ordinary unmarked prose and dynamic names are excluded; some URL/file
paths are false positives. Each entry retains the complete line and a pinned
source URL. Snapshot data is read through `git archive`, so concurrent working
tree edits cannot be incorrectly cited as historical commit contents.

The automatic buckets are 241 context-review mentions, 125 index/doc/test
references, seven router/optional suggestions, seven companion-selection
suggestions, two operative instructions needing review, one user-only
prerequisite-call problem, and nine solution-chain references.
[Audited repository snapshot](https://github.com/bughunt8/skills/tree/5f132c008d5c8d261b4fa30e94899151c186ce94)

Context review found these consequential inbound cases:

| Inbound caller/reference | Classification and required follow-up | Exact snapshot evidence |
| --- | --- | --- |
| `solutions/idea-to-shipped-code.md` | Current chain instructions, not suggestions. Five human-only stages, `ask-matt`, `to-spec`, `wayfinder`, `to-tickets`, `implement`, must not be automatically dispatched by a Solution agent. Require separate human stage commands or an approved redesigned flow. | [Solution steps and executable prompt](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/solutions/idea-to-shipped-code.md#L9) |
| `solutions/hard-to-find-bug.md` | Three current model-compatible chain targets, diagnosing-bugs, tdd and code-review. Provider/resource closure is available, but actual tests, review independence and approvals remain runtime obligations. | [Bug solution chain](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/solutions/hard-to-find-bug.md#L9) |
| Native GitHub setup, historical body | "Run setup ... first" is an operative request to a now human-only provider, not proof of a safe automatic prerequisite. Use compatible approved configuration or an independent human command. | [Historical setup sequence](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/github-repository-setup/SKILL.md#L48) |
| Native setup tooling | Conditional grilling is a current interview instruction. Its companion table is selection guidance. The conditional grill-with-docs instruction needs explicit human routing; domain-modeling may be an approved active model call. | [Companion table](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/github-repository-setup/references/tooling.md#L110), [Interview steps](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/github-repository-setup/references/tooling.md#L135) |
| Senior backend/frontend/fullstack composition maps | Routing/fork instructions refer to `engineering/grill-me/` and absent agent/reference layouts. They are not validated aliases for native `skills/productivity/grill-me`, and should not cause a model call to the user-only skill. Resolve the intended local agent/derivative separately or require human invocation. | [Backend routing and fork rules](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering-team/skills/senior-backend/references/composition_map.md#L25), [Frontend map](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering-team/skills/senior-frontend/references/composition_map.md), [Fullstack map](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering-team/skills/senior-fullstack/references/composition_map.md) |
| BizOps, Commercial, Research-Ops grill commands | "Apply Matt's discipline" followed by their own question rules is an inline derivative, not an explicit load of the Matt wrapper. Preserve attribution; do not invent a user-only model edge from copied discipline prose. | [BizOps command](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/business-operations/commands/cs-grill-bizops.md#L8), [Commercial command](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/commercial/commands/cs-grill-commercial.md#L8), [Research-Ops command](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/research-ops/commands/cs-grill-research-ops.md#L8) |
| Agent-harness domain assets | Provider/tool metadata is not itself a current Skill-tool call. Some paths describe nested grill/handoff derivative resources that are not Matt native paths. Their consumers need a separate regeneration/review before runtime use. | [Engineering harness asset](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/agent-harness/skills/agent-harness/assets/harnesses/engineering.json), [Productivity harness asset](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/agent-harness/skills/agent-harness/assets/harnesses/productivity.json) |
| Research router agent and summarizer | Path-qualified router references intend the hybrid provider, not Matt's wayfinding research worker. The registry does not rewrite these into Matt calls. | [Research agent path](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/research/research/agents/cs-research.md#L4), [Summarizer distinction](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/product-team/research-summarizer/skills/research-summarizer/SKILL.md#L29) |
| Project-management `/retro` wording | Domain command suggestion with the same spelling as Matt's new environment-review entry. The host command namespace and intended target are unresolved; do not auto-map every `/retro` mention to Matt. | [PM command list](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/project-management/CLAUDE.md#L20), [PM orchestrator](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/project-management/agents/cs-pm-orchestrator.md#L77) |
| SDD | Its only inventory candidate is source-analysis prose containing an implementation term, not a named Matt dispatch. TDD.md in its document mapping means a test-strategy document, not an automatic call to `tdd`. | [SDD source analysis](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/spec-driven-development/references/source-analysis.md#L11), [SDD authoritative mapping](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/spec-driven-development/SKILL.md#L17) |

The inventory is deliberately not included as operative edges in the stable
graph. A passing checker does not resolve those historical Solution, path,
derivative-agent and command-namespace ambiguities. No full library closure
claim is supported.

## Setup and SDD review

Keep the no-Claude override, GitHub-only issue authority, approved label
changes, optional Projects, serialized dispatcher, independent PR review,
tested integration SHA, and separate promotion authority.
[Native setup integration](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/github-repository-setup/references/agentic-development.md),
[Native tooling scope](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/github-repository-setup/references/tooling.md)

The local setup caller scope permits `grilling`, active
`domain-modeling`, `pr` body assistance, and an approved isolated `prototype`.
It does not permit automatic setup, grill wrappers, spec/ticket commands,
whole-spec implementation, or retro. Scope membership only permits exact
resolution; the host still needs the task's actual approval.

Matt `implement-spec` uses parallel workers, integration worktrees and final
code review, while SDD explicitly requires fresh authorization for one atomic
task, distinct red/green/refactor evidence, post-build review and human
verification.
[Implement-spec orchestration](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/implement-spec/SKILL.md),
[SDD task gate](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/spec-driven-development/SKILL.md),
[SDD review records](https://github.com/bughunt8/skills/blob/5f132c008d5c8d261b4fa30e94899151c186ce94/skills/engineering/spec-driven-development/references/review.md)

Do not run Matt parallel workers as a bypass around SDD. Human approval of a
different orchestration profile must resolve the authority/layout question
before execution; this checker creates no such approval.

Prototype skips tests upstream, so permit it only for an approved isolated
throwaway question and never as production SDD completion evidence.
[Prototype exception in upstream](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/prototype/SKILL.md)

Wayfinder's research worker can load a skill that creates another worker;
bound delegation at the host, and pass leaf workers their numbered reading
job rather than the entire dispatcher instruction.
[Wayfinder research delegation](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/wayfinder/SKILL.md#L115),
[Research background worker](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/research/SKILL.md)

## Regression evidence and remaining limits

The tests exercise successful native resolution and explicit refusals for
model-to-user-only dispatch, both human aliases, unscoped research, wrong
research caller/provider, missing resources, body/resource drift, YAML/Codex
pair mismatch, non-boolean flags, duplicate keys, graph/body/evidence mismatch,
graph closure/cycles, alias cycles/wrappers, unsafe paths, symlink resources,
provenance source paths, ownership IDs and manifest mappings. The read-only
test compares every fixture file hash before and after checking/resolution.

Run the shipped test commands for current evidence rather than relying on
authoring reports. Regression fixtures use system temporary directories and
automatic cleanup, never installed repository directories. Negative cases
succeed by returning refusal, not by repairing their inputs.

## Script-driven migration and preservation

The 24 existing native skill trees were adopted only through the importer's
explicit `--sync --adopt-existing --source ID` mode. Each manifest entry records
the complete legacy tree fingerprint and its exclusive archive destination
under `docs/migrations/matt-v1.3.1/legacy/`. The three new stable entries were
imported through normal `--sync --source ID`. No external skill body was copied
or modified by hand.

The migration audit and precise historical body matches are in
[dependency-audit.md](migrations/matt-v1.3.1/dependency-audit.md) and
[dependency-audit.json](migrations/matt-v1.3.1/dependency-audit.json).
The previous common pin did not accurately describe most old bodies. The local
`caveman` and `write-a-skill` derivatives remain intact, with unresolved original
pins explicitly recorded in the legacy inventory.

Archives preserve original names and permissions so they can be compared with
their exact fingerprints. Skill discovery must be scoped to `skills/`, as the
repository index, linter, site source configuration and resolver are. Never
point a recursive host skill loader at the whole repository. It could discover
old `SKILL.md` files in migration archives or read-only source references.
These are historical evidence, not active skills. Full permission fingerprints
are local migration evidence; a fresh checkout's umask can change them.

Adoption refuses an existing archive, changed legacy hash, managed destination,
corrupt ownership, unsafe path, symlink, overlapping scope or mismatched upstream
commit. It preflights selected sources before writes and restores the source on
a caught import failure. Recovery is per source, not whole-run or crash atomic.
Interrupted processes and concurrent hostile writers still require manual
inspection of archives and holding directories. Never forge ownership records
to bypass a refusal.

`kind: skill` imports one complete skill directory, including its resources.
Root metadata names reserved by the importer are rejected before import;
nested legitimate files remain content. Filtered reference comparison uses the
same projection as copying, so excluded files do not create false drift.
The unchanged 13-case self-test remains part of the importer regression suite.

Matt sources use release ref `v1.3.1` plus `expected_commit`, not moving `main`.
Future upgrades need a deliberately reviewed ref, pin, registry and resource
hash update. A retargeted tag fails closed. A normal repeat refresh needs no
adoption flag and must report no drift:

```bash
python3 scripts/sync_vendor.py --check --source mattpocock-prototype
python3 scripts/sync_vendor.py --sync --source mattpocock-prototype
```

The read-only invocation reference imports policy/ADRs and their linked
documentation, not root steering or active Claude plugin configuration.
`pr/CREDITS.md` is preserved. A separate license-only HumanLayer reference
retains the MIT notice for the credited copied material; it installs no
`show-me` skill. Its expected-commit guard rejects a moved source ref until
reviewed. This records notices, not independently proven text ancestry.
[PR credits](https://github.com/mattpocock/skills/blob/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/pr/CREDITS.md),
[HumanLayer MIT notice](https://github.com/humanlayer/skills/blob/ca7c8088db69e315a8b2deea43820270457f8f3c/LICENSE)

## Current inbound closures and unresolved legacy consumers

The historical inbound inventory is evidence of the pre-upgrade snapshot,
not a claim that all findings remain open. The native setup now uses top-level
human-only metadata with matching Codex policy, never auto-calls Matt setup,
and tells the user to invoke `/start-github-repo docs` independently if needed.
The existing `start-github-repo` package's legacy nested invocation metadata is
outside this upgrade's client-metadata qualification; the setup guard does not
claim that every host correctly classifies that other package.

The strict `agentskills validate` tool implements the core Agent Skills schema.
It rejects top-level `disable-model-invocation` and `argument-hint`, which are
client extensions also used by the pinned upstream human-only skills. Do not
move the flag back under metadata merely to obtain a green core-schema check;
that restores the client-classification defect. Validate a throwaway projection
without those two extension fields for core-schema checks, and validate the
actual top-level flags and Codex pair through the shipped bundle and dependency
tests. Report the strict validator's extension rejection separately, never as a
passed full-package validation.

The authored `idea-to-shipped-code` Solution now declares its first five stages
as `invocation: user`. Its prompt stops for each independent human command.
`check_solutions.py` rejects a human-only provider in an automatic step, with
regression tests. This fixes that executable chain without modifying Matt's
vendor bodies.

Senior-engineer derivative agent paths, broader harness assets and the PM
`/retro` namespace remain separate legacy qualification work. The root policy
blocks dispatch if the intended provider, invocation class or required resources
cannot be verified; it does not silently substitute a Matt skill. The inbound
inventory reports the actual candidates so these limits are visible rather than
presenting the 27-provider check as full-library closure.

The local domain consumer now points to lazy `GLOSSARY.md` and existing ADRs.
No missing glossary was fabricated or unrelated CONTEXT file renamed.
If a consumer project declines naming migration, upgraded Matt consumers do not
automatically read its old domain filenames. Record an approved pointer adapter
or explicit read instruction before claiming compatibility. There is no new
`GRAMMAR.md`; `.agents/invocation.md` governs invocation, GLOSSARY defines domain
language, and `.specs/` retains behavioral authority.

These are static tests of trusted local records. They do not authenticate a
human, prove license rights, ensure review independence, verify actual tracker
permissions, test a host's qualified loader, stop concurrent hostile writers,
or enforce worker budgets.
