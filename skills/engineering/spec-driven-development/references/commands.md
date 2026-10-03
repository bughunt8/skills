# Command workflow

Every response starts with `[Command] [Target specs files]`. Use resolved authoritative paths and include the selected feature when applicable. A command is one phase, not permission to run the entire lifecycle. Approval of a spec is not approval of architecture, all tasks, or deployment.

## /constitution

Inspect existing repository policy and product context. Create or map the four globals, then scope the request. For multiple independently testable capabilities, propose CAPABILITY_MAP module IDs, owners, shared contract locations, and acyclic provider-to-consumer build order. Ask bounded clarification questions. Record assumptions with owner/validation method. Seek human approval and stop before writing feature requirements.

The scaffold only makes draft files and refuses overwrites. Existing globals are reused in multi-feature mode, not replaced. No draft scaffold passes a readiness gate.

## /spec

Load selected mission/scope plus approved policy. Write SPECIFICATION what-only requirements and acceptance criteria using [EARS](ears.md). Record exclusions and questions without silently resolving them. Run `lint --stage spec`. Summarize the spec, list unresolved questions, ask for human approval, and stop the turn. Planning starts in a later turn after actual approval, consistent with the source's explicit stop rule. [Addy's gated SDD](https://github.com/addyosmani/agent-skills/blob/main/skills/spec-driven-development/SKILL.md)

## /plan

Require approved behavior and resolved material questions. Write DESIGN with mechanisms, provider-owned contracts, data handling, both allowed/denied security paths, mocks where useful, and simplicity rationale. Write INVARIANTS positive and attempted-violation tests. Write OBSERVABILITY safe runtime event design or specific opt-outs. Run `lint --stage plan`. Ask for human design approval and stop.

## /tasks

Require approved design. Split into one focused-session tasks, usually no more than five owned files unless justified. Declare requirements, invariant/observation refs, files, tests, dependencies, complete Verify command, cwd, expected exit, and completion condition. Add execution rows. Future test paths may be absent. Run `lint --stage tasks`, inspect DAG and scope, ask for human task-plan approval, and stop.

Explicit dependencies do not prevent independent tasks. Do not invent a "tasks must have no dependencies" restriction. Module prerequisites require a human review of provider contract and verified completion evidence; the local checker cannot approve another feature's readiness.

## /analyze

Read all selected artifacts and their mapped authorities, not the entire project by default. Compare requirement/AC coverage, design decisions, invariant intent, observation privacy, task DAG, assumptions, and implementation scope. Identify the actual base and compared diff. Inspect relevant code, tests, contracts, and positive/negative security paths. UI review uses mocks/screenshots for intent and actual browser/keyboard proof for execution when UI exists. [Zach Lloyd's three-skill workflow](https://www.linkedin.com/pulse/three-skills-you-need-spec-driven-development-zach-lloyd-bdhvc)

Append every material contradiction to CROSS_ANALYSIS with severity, affected IDs/paths, evidence, owner, and options. If code and spec materially conflict, halt and ask the human whether to correct code or deliberately revise the spec. Never quietly rewrite a requirement to make code appear compliant.

Pre-build analysis checks `tasks`, records planned tests honestly, and hashes expected missing code/tests as missing. Post-build review names one `task`, checks its owned code/test declarations plus completed tasks, and requires distinct Red/Green/Refactor evidence. Its scope excludes unstarted future tasks. Pre-build scope covers all owned paths; post-build scope covers active/completed paths plus other reviewed changes. The checker cannot detect undeclared changes. Humans check actual diff completeness, including new/deleted/untracked files.

For a structurally successful review, supply a manual review JSON per [review protocol](review.md), then run `analyze --review <file>`. Blockers prevent success. Successful reviews produce a new content-addressed JSON and append CROSS_ANALYSIS. Blocked findings must still be appended manually; the script never erases history or "resolves" a contradiction. `analyze` is not approval.

## /build

Require real human behavior/design/task approval plus fresh pre-build analysis and immutable human-authored approval record. Run `gate --approval <file> --task TASK-N` before code changes. Independently confirm the human authorization record is genuine. The local checker only tests its structure and matching content hashes.

1. Load selected task and relevant artifacts/contracts/source only. Ensure explicit prerequisites have verified evidence.
2. Author meaningful behavior and invariant assertions. Run the individually reviewed test command. Record an actual assertion failure caused by missing behavior, not a broken environment, import error, or stub exception.
3. Implement the smallest change. Run green, inspect both allowed and denied security paths, and verify safe observations.
4. Refactor without changing behavior, rerun task verification and regression/integration/contract tests as applicable. Use actual browser/keyboard evidence for UI behavior.
5. Record actual commands, cwd, exits, assertions, and results in distinct evidence files, and mark TASKS in-progress. Perform task-specific post-build analysis and human verify approval. After genuine human verification, mark completed and record Verification evidence. The next build approval's completed map binds that post-build analysis and verification file hashes.
6. Stop after this task. A refreshed analysis/approval is needed for another task because source, tests, and TASKS changed.

A human may explicitly authorize a scoped unattended policy with named tasks, limits, and separate verification checkpoints, but it is never assumed and does not bypass hashes, task prerequisites, material-drift stops, or destructive-action authorization. The bundled gate still authorizes only one selected task at a time.

## Version control

Include authoritative specs and review evidence with implementation PRs and link the relevant requirement/task IDs. Preserve old review/approval records; create new ones after amendments. Ask before dependencies, contract breaks, schema changes, PII handling, external posting, deployment, or commits. No bundled script performs those actions. Living specs document deliberate decisions, not retrospective excuses. [Addy's living-spec guidance](https://github.com/addyosmani/agent-skills/blob/main/skills/spec-driven-development/SKILL.md)
