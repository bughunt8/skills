---
name: agent-harness
description: "Compile domain goals into exact-provider task plans and drive bounded execute, verify, retry, escalate and close loops. Use for engineering, marketing or other repository domain harnesses and fresh-session continuation. Not for workflow-builder scripts, agenthub tournaments, autoresearch-agent metric optimization or loop-library recipe discovery."
---

# Agent harness

The manifest inventories providers and checks; the plan selects tasks;
`.agent-harness/state.json` preserves attempts and evidence across sessions.
Use Python 3.10+ and PyYAML. Run commands from the actual checkout root, not `skills/`.

## Workflow

1. Establish outcome, domain, no-touch paths, escalation reviewer and budget.
   Ask missing questions one per turn with a recommended answer.
   Read [runtime operations](references/runtime_operations.md) for intake, commands,
   exit codes, all domain assets and sibling routing.
2. Select a manifest from [assets/harnesses/](assets/harnesses/). Compile with
   [goal_compiler.py](scripts/goal_compiler.py). Review tasks, checks and caps with the
   user before init. On `HUMAN-COMMAND-REQUIRED`, show the exact provider path
   and independent human command, then stop. Loop approval cannot authorize a user-only
   provider. Qualify same-name matches by `--provider-path`.
3. Init a NEW state file with [loop_controller.py](scripts/loop_controller.py).
   Request `next`. Bind its exact `skill_file` with a qualified
   loader or verify the host selected that same file. If the loader accepts only an
   ambiguous bare name, block dispatch. Execute one task within its constraints and
   record the real result. Never start a second writer in that invocation.
4. Run `verify` with the checkout as `--cwd`; supply evidence for remaining manual checks.
   Never change checks to pass. Smoke/sample passes test tools, not the goal;
   inspect output against `done_when`.
   Change the approach on retry. Stop on escalation or exhausted caps.
5. Request `close`, which refuses unverified, unwaived tasks. Only the user
   may authorize a reasoned waiver. Return the handoff and evidence log. A fresh
   session starts at `next` with the same state and live checkout. Keep state out of
   `.agenthub/`, `.autoresearch/` and `docs/TC/`.

Example, from the checkout root:

```bash
H=skills/engineering/agent-harness/skills/agent-harness
mkdir -p .agent-harness
python3 "$H/scripts/goal_compiler.py" \
  --goal "test driven development red green refactor" \
  --manifest "$H/assets/harnesses/engineering.json" \
  --provider-path skills/engineering/tdd --repo-root . --out .agent-harness/plan.json
python3 "$H/scripts/loop_controller.py" init \
  --plan .agent-harness/plan.json --state .agent-harness/state.json --repo-root .
python3 "$H/scripts/loop_controller.py" next --state .agent-harness/state.json --repo-root .
# -> {"action":"execute","skill_path":"skills/engineering/tdd",
#     "skill_file":"skills/engineering/tdd/SKILL.md", ...}
```

## Binding and trust rules

The scripts validate live identity, role, hashes and paths before each operation.
On refusal, stop and read [provider bindings](references/provider_bindings.md).
Never reset state or edit hashes to hide drift. Validation grants no human authorization,
sandboxing or host-loader path enforcement. Plan/state checks remain trusted executable
configuration.

## Resource navigation

- Run [harness_manifest_builder.py](scripts/harness_manifest_builder.py) after provider
  changes; `--check` compares committed assets without writing. It calls shared
  [provider_bindings.py](scripts/provider_bindings.py), not a CLI.
- Read [manifest schema](assets/harness_manifest.schema.json) when validating inventories.
- Read [verification discipline](references/verification_discipline.md) for evidence,
  [loop canon](references/agentic_loop_canon.md) for fresh-session work and
  [domain design](references/domain_harness_design.md) when extending a domain.
- Use [harness-runner](../../agents/harness-runner.md) for one-task delegation and
  [cs-harness](../../commands/cs-harness.md) for the end-to-end command.
  Run [regressions](../../tests/test_provider_bindings.py) before accepting binding changes.
