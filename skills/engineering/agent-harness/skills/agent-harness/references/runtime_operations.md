# Runtime operations

Read this before the first compilation, for command/exit-code details, or when choosing
a sibling workflow. Run from the actual checkout root. Use Python 3.10+ with PyYAML.

## Intake

Ask unresolved questions one per turn, with a recommended answer.

| Question | Recommended answer |
|---|---|
| What single observable outcome means DONE? | A named artifact and a command checked against that artifact |
| Which domain harness applies? | The domain whose skills name the deliverable; run two domains sequentially if needed |
| What must NOT change? | Name no-touch paths and put those constraints in the goal |
| Who reviews escalations, and how fast? | A named human; escalation blocks the loop |
| What is the iteration budget? | Defaults are 12 loop iterations and 3 attempts per task; raise only with a reason |

## Commands

```bash
H=skills/engineering/agent-harness/skills/agent-harness
mkdir -p .agent-harness
python3 "$H/scripts/goal_compiler.py" \
  --goal "test driven development red green refactor" \
  --manifest "$H/assets/harnesses/engineering.json" \
  --provider-path skills/engineering/tdd --repo-root . --out .agent-harness/plan.json
# Review the task plan and obtain user approval before init.
python3 "$H/scripts/loop_controller.py" init \
  --plan .agent-harness/plan.json --state .agent-harness/state.json --repo-root .
python3 "$H/scripts/loop_controller.py" next --state .agent-harness/state.json --repo-root .
# Load the exact directive skill_file, perform ONE task, then record the real result.
python3 "$H/scripts/loop_controller.py" record --state .agent-harness/state.json \
  --task T1 --phase execute --exit-code 0 --repo-root .
python3 "$H/scripts/loop_controller.py" verify --state .agent-harness/state.json \
  --task T1 --cwd . --repo-root .
# For remaining manual checks only, provide what you actually observed.
python3 "$H/scripts/loop_controller.py" record --state .agent-harness/state.json \
  --task T1 --phase verify --exit-code 0 --evidence "<observation>" --repo-root .
python3 "$H/scripts/loop_controller.py" close --state .agent-harness/state.json --repo-root .
```

Repeat `next`, execution, record and verification until `close` or `escalate`. Branch on
each exit code; never continue after a binding refusal. `verify` executes trusted command
strings with a subprocess timeout and logs the output tail. A passing manual verify
record still requires evidence. Failure consumes attempts; exhausted caps escalate.
Human-authorized `close --waive T3 --reason "<reason>"` retains the reason in the handoff.
Never alter checks, manifests or plans to make a gate pass.

| Exit | Meaning |
|---|---|
| 0 | OK or directive emitted |
| 2, controller | Attempts exhausted, human review required |
| 3, compiler | Vague goal, answer forcing questions and recompile |
| 4, compiler/controller | No match / close refused |
| 5, controller | Global iteration cap |
| 6, controller | Invalid transition, unknown task or missing verify evidence |
| 7 | Binding/schema/path/committed-drift refusal; preserve state, review and regenerate/recompile |
| 8, compiler | Human command required; no executable plan output |

## All committed assets

The [manifest schema](../assets/harness_manifest.schema.json) describes generated
inventories. Pick one of these 18 existing domain targets:

| Domain manifests | Domain manifests | Domain manifests |
|---|---|---|
| [business-growth](../assets/harnesses/business-growth.json) | [business-operations](../assets/harnesses/business-operations.json) | [c-level-advisor](../assets/harnesses/c-level-advisor.json) |
| [commercial](../assets/harnesses/commercial.json) | [compliance-os](../assets/harnesses/compliance-os.json) | [engineering](../assets/harnesses/engineering.json) |
| [engineering-team](../assets/harnesses/engineering-team.json) | [finance](../assets/harnesses/finance.json) | [loop-library](../assets/harnesses/loop-library.json) |
| [markdown-html](../assets/harnesses/markdown-html.json) | [marketing](../assets/harnesses/marketing.json) | [marketing-skill](../assets/harnesses/marketing-skill.json) |
| [product-team](../assets/harnesses/product-team.json) | [productivity](../assets/harnesses/productivity.json) | [project-management](../assets/harnesses/project-management.json) |
| [ra-qm-team](../assets/harnesses/ra-qm-team.json) | [research](../assets/harnesses/research.json) | [research-ops](../assets/harnesses/research-ops.json) |

Regenerate and run `--check` using [provider bindings](provider_bindings.md) after changes.
The three tools' `--help` and `--sample` are smoke/demonstration checks, not objective proof.
Test vague-goal refusal, unverified close refusal and a failed verify consuming an attempt
before trusting a run. Outer `tests/test_provider_bindings.py` checks provider regressions.

## Choose adjacent skills instead

- `workflow-builder` authors Workflow-tool `.js` scripts, not goal-to-close state.
- `agenthub` runs competing agents on one task; use inside a task needing alternatives.
- `autoresearch-agent` optimizes one file against a locked metric evaluator.
- `tc-tracker` tracks a code change; this state tracks a goal.
- `loop-library` discovers or audits loop recipes, rather than running this controller.
- `ship-gate`, `self-eval` and `spec-driven-workflow` may supply task checks after their
  own provider/authorization validation. They do not replace independent approval gates.
