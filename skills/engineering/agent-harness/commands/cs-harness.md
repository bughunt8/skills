---
description: Compile a goal into a verified agent-harness loop for a domain and drive it to close — /cs:harness <domain> <goal>
argument-hint: <domain> <goal text>
---

# /cs:harness — run a goal through a domain's agent harness

Parse `$ARGUMENTS`: the first token is the domain (one of the 18 manifest names under
`skills/engineering/agent-harness/skills/agent-harness/assets/harnesses/`); the rest is the goal.
If the domain token doesn't match a manifest file, list the available manifests and ask.
Run from the actual checkout root, not its `skills/` directory. Set
`H=skills/engineering/agent-harness/skills/agent-harness` and create `.agent-harness/`.
Read `$H/references/provider_bindings.md` if bindings or legacy schemas refuse.

## Sequence (gates are blocking — never skip forward)

1. **Compile** —
   `python3 "$H/scripts/goal_compiler.py" --goal "<goal>" --manifest "$H/assets/harnesses/<domain>.json" --repo-root . --out .agent-harness/plan.json`
   - Exit 3: relay the forcing questions to the user one at a time (recommended answer
     first), then recompile with the enriched goal. Do not proceed on a vague goal.
   - Exit 4: show `nearest_candidates`, ask whether to switch domain or refine the goal.
   - Exit 7: stop on a binding/schema refusal. For duplicate names, qualify with
     `--provider-path <exact-directory>`, not a guessed namespace or bare name.
   - Exit 8: relay `HUMAN-COMMAND-REQUIRED` with the exact path and independent
     human command. Stop; never fall through to a model provider or reuse an old output.
2. **Review the plan with the user** — show tasks, verifications, and caps. Confirm before
   initializing. Preserve provider-specific and repository approval gates too.
3. **Init** — `python3 "$H/scripts/loop_controller.py" init --plan .agent-harness/plan.json --state .agent-harness/state.json --repo-root .`.
   If state exists, preserve it; never reset it to bypass a legacy/drift refusal.
4. **Drive** — repeat: `next` → execute the task per its skill's SKILL.md → `record` →
   `verify`. For long goals, spawn the `harness-runner` agent per task instead of executing
   inline, one at a time (writes stay serialized).
   Use `--repo-root .` on controller commands and `--cwd .` on verify. Bind the
   directive's exact `skill_file`; if the host cannot qualify a collision, block dispatch.
   A loader check or smoke/sample pass grants neither human approval nor objective proof.
5. **On exit 2 or 5** — stop, show `status` and the failing evidence; the user decides:
   fix and continue, waive with a reason, or abandon.
6. **Close** — `close --state .agent-harness/state.json`; paste the handoff block
   (tasks, statuses, evidence, waivers) as the deliverable summary.

## Rules

- Never edit checks, manifests, or the plan mid-loop to make verification pass.
- Never report an exhausted budget as success.
- `.agent-harness/` is git-ignorable working state; the handoff block is the record.
