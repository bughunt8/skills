# Legacy harness provider bindings

This follow-up qualifies the older consumers of the pinned Matt skill suite.
It repairs local paths and invocation boundaries without editing the 27 vendored
providers or treating static verification as host registration.

## Scope

- The backend, frontend and fullstack composition maps now point to exact
  Skill, agent-definition and reference files. The audit covered 41 routing
  rows, 48 declared targets, 22 escalation targets and 10 resource declarations.
- The existing harness builder regenerates its 18 domain inventories from the
  checkout root. Its compiler and controller carry and revalidate the selected
  provider into each fresh-session directive.
- PM sprint retrospectives use the installed `/cs:pm` command and the existing
  scrum-master discipline. Matt's human-only `retro` remains a different request.
- All local declarations are registered in `legacy_bindings` inside the existing
  `.agents/skill-dependencies.json`. There is no second loader or registry.

The discovery baseline is
[commit 00e07d2](https://github.com/bughunt8/skills/tree/00e07d2f6d0588ac05f857c095de78cd038ab828).
The work remains within the
[open staging PR](https://github.com/bughunt8/skills/pull/64), not a production promotion.

## Senior-engineer routing

Read the affected composition map before selecting a specialist:

- [Backend](../skills/engineering-team/skills/senior-backend/references/composition_map.md).
- [Frontend](../skills/engineering-team/skills/senior-frontend/references/composition_map.md).
- [Fullstack](../skills/engineering-team/skills/senior-fullstack/references/composition_map.md).

The short hubs route to preserved detailed workflows and local forcing-question
resources. Existing tool commands, profiles, examples and approval criteria remain.
Concrete paths use actual entrypoints, including nested a11y and Apple HIG
packages, the canonical `pw` toolkit and the `karpathy-reviewer` definition.
Grilling is a separately identified model primitive, not a forged
`cs-grill-master` alias or an implicit call to a human-only grill wrapper.

Model consumers can resolve one exact declared Skill file:

```bash
python3 scripts/check_skill_dependencies.py --include-legacy
python3 scripts/check_skill_dependencies.py \
  --resolve-legacy-target skills/productivity/grilling/SKILL.md \
  --caller senior-backend --invoker model
```

The resolver prints a verified path and invokes nothing. Conditional branches
retain their approval, project-profile and capability requirements.
Agent-definition files cannot be dispatched through the Skill loader.
An actual registered host role is required before an agent handoff.

Missing senior-engineer wrappers, their advertised review commands,
`cs-grill-master`, `cs-cto-advisor`, `cs-content-creator` and a single RA/QM
entrypoint remain explicit blocked branches. They were not replaced with
invented agents. Deprecated content-creator guidance and its successor require
manual selection; the helper does not silently rebind that route.

## PM retrospective namespace

The explicit PM request is:

```text
/cs:pm sprint retrospective action items
```

Qualify it without invoking the command:

```bash
python3 scripts/check_skill_dependencies.py \
  --resolve-pm-retrospective --invoker user
python3 skills/project-management/skills/pm-skills/scripts/pm_goal_router.py \
  --repo-root . --text "sprint retrospective action items" --output json
```

The first command emits the command definition, inquiry and exact scrum-master
provider path with `executed: false`. The router accepts only the checkout
derived from its own installed location. It checks live provider/client metadata
and the registered PM file hashes, refusing foreign roots, dangling policy links
and stale records. Classification without that root is
unqualified; qualification itself grants no execution or mutation authority.

For Matt's agent-environment retrospective:

```bash
python3 scripts/check_skill_dependencies.py \
  --resolve retro --namespace matt --invoker user
```

An unqualified human `retro` request is refused as ambiguous. A PM namespace does
not alias to Matt's Skill, and models cannot invoke that human-only target.
The PM AGENTS.md corrects the historical command advertisements without creating
or updating a Claude integration. The old CLAUDE.md remains historical, not
proof that PM `/retro`, `/sprint-health` or `/project-health` commands exist.

## Executable harness migration

The existing builder is still the only writer of committed inventories:

```bash
H=skills/engineering/agent-harness/skills/agent-harness
python3 "$H/scripts/harness_manifest_builder.py" --all --repo-root . \
  --out-dir "$H/assets/harnesses" --no-timestamp
python3 "$H/scripts/harness_manifest_builder.py" --check --repo-root .
HARNESS_SOURCE_ROOT="$PWD" python3 -m unittest discover \
  -s skills/engineering/agent-harness/tests -p 'test_*.py' -v
```

Run from the checkout root containing AGENTS.md and skills/, not from skills/.
The inventories use `manifest.v2`; executable plans and states use `plan.v2`
and `state.v2`. Paths, names, invocation policy and non-derived owned file hashes
are checked against the live provider. Generated harness inventories are excluded
from their own provider fingerprint to avoid circular hashes and checked
separately for byte-for-byte freshness.

The compiler refuses a selected human-only provider without writing a new plan.
It does not silently choose a lower-ranked model alternative.
For a duplicate name, select the exact provider directory using `--provider-path`.
The controller preserves `skill_path` and emits the exact `skill_file` into fresh
execution directives. A forged role, missing resource, changed source or client
policy blocks operations before state mutation or verification execution.

Legacy manifests must be regenerated and legacy plans recompiled. Preserve
existing state and evidence, inspect the mismatch, and use a reviewed NEW state
filename. Initialization refuses an existing state file; it never resets one.
See [provider bindings](../skills/engineering/agent-harness/skills/agent-harness/references/provider_bindings.md)
for exit codes, hash scope and recovery details.

Two owned markdown-html description scalars were quoted to make their actual
YAML parseable. Their text and instruction bodies were unchanged. The binding
parser refuses malformed metadata rather than manufacturing a corrected role.
The starter's historical nested `disable-model-invocation: false` means
model-routing intent, not a missing human-only guard. Its phase and mutation
approval rules remain separate.

## Qualification limits

These checks establish declared local identity, file freshness, routing kinds
and invocation boundaries. They do not prove native host path binding, agent
registration, MCP access, objective correctness, reviewer independence or a
human's identity. Loop plan/state files remain trusted executable configuration.
Existing smoke/sample passes prove tools load, not that a goal was accomplished.
No broader sandbox or formal safety claim is made.

The runtime checks can refuse stale inputs but do not lock the filesystem against
concurrent writers or authenticate waivers. Serialize source changes with runs,
keep higher-priority repository instructions and human approvals, and inspect
actual evidence before closure. No merge or deployment is authorized by this file.
