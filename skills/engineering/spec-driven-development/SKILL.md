---
name: spec-driven-development
description: "Use for spec-first projects, features, significant changes, ambiguous requirements, capability decomposition, EARS behavior, design/task planning, cross-artifact drift analysis, or gated test-first implementation. Supports /constitution /spec /plan /tasks /analyze /build with human review and one atomic task per build. Not for isolated typo fixes."
compatibility: "Python 3.10+ standard library for bundled checks. Works standalone; repository tools, git, browsers, and test frameworks are optional project-specific tools."
---

# Spec-driven development

Begin every response with `[Command] [Target specs files]`, for example `[/spec] [.specs/SPECIFICATION.md]`. Resolve the actual flat, feature, or INDEX-mapped paths. Never imply a draft or structural pass is approved.

## Start here

Read [artifact contract](references/artifact-contract.md) for storage and templates, [commands](references/commands.md) for phases, [EARS](references/ears.md) for `/spec`, and [review](references/review.md) before `/analyze` or `/build`. [README](README.md) has installation, CLI and examples. [Source analysis](references/source-analysis.md) credits all three sources. [Review closure](references/review-closure.md) records adversarial checks and limits.

Inspect policy and authoritative docs; surface assumptions and clarify unresolved behavior. For independently testable capabilities, propose stable module IDs, provider-owned contracts and a CAPABILITY_MAP DAG; request human approval and stop before feature specs. Otherwise use flat `.specs/` with all nine artifacts. Multi-capability layouts share four globals and five files per feature.

Map PRD/TRD/README/AGENTS/TDD/WIREFRAME/TOGAF ADM via INDEX without duplication. Load only shared policy, selected feature, contracts and current task/code. Legacy `spec-driven-workflow` remains separate RFC2119 tooling; never overwrite it or treat its score as EARS validation.

## Command boundaries

| Command | Write or review | Exit |
| --- | --- | --- |
| `/constitution` | CONSTITUTION, MISSION, TECH_STACK, ROADMAP; INDEX; scope map if needed | Summarize boundaries and assumptions; request human approval; stop. |
| `/spec` | SPECIFICATION only; EARS what, not how; AC-N Given/When/Then | Run spec-stage lint. List questions, request approval, end turn. Never plan in the same turn. |
| `/plan` | DESIGN, INVARIANTS, OBSERVABILITY; justified decisions and safe events | Run plan-stage lint; request human review; stop. |
| `/tasks` | TASKS with explicit dependencies, owned files, tests, command/cwd/exit, execution log | Run tasks-stage lint; request approval; stop. |
| `/analyze` | CROSS_ANALYSIS and immutable review evidence | Compare artifacts and actual reviewed changes; report blockers. Record pre-build or post-build review, never authorize it. |
| `/build` | One approved atomic task's tests/code and TASKS evidence | Check fresh pre-build gate, actual Red-Green-Refactor, run reviewed verification, stop for human verification. |

Run the documented `scripts/sdd.py --root <project>` subcommand with Python 3.10+. It scaffolds without clobbering, lints, extracts AC intent, records analysis and checks fresh human-authored authorization. It never executes spec commands, installs dependencies, commits, posts or deploys. Missing/stale authorization blocks builds. Earlier phase approvals require the trusted human channel; the tool checks only final build/verify records.

## Build discipline

Confirm real human authorization separately from local JSON. Select a dependency-ready task; independent tasks are allowed after explicit dependencies, but default execution is one task then stop. First write meaningful assertions and observe a genuine behavior assertion failure. An import error or generated stub exception is not a sufficient red. Implement minimally, run green, refactor, rerun, and inspect code against behavior, contracts, both security paths, invariants, and event privacy. For UI work gather actual browser and keyboard evidence; mocks and screenshots alone are design intent.

Mark TASKS in-progress with distinct red/green/refactor evidence. Obtain task-scoped post-build review and human verification before marking completed. Completed prerequisite records bind that review and verification evidence. Edits stale earlier authorization; obtain a fresh next-task review/approval. Link specs, evidence and requirement/task IDs in the implementation PR without automatic commits.

Always preserve CROSS_ANALYSIS history. Ask on ambiguity, boundary changes, secrets/PII, new dependencies, or material drift. Halt contradictions and offer a user choice: correct code, or deliberately revise specs and re-review. Never silently change specs to excuse code. Structural checks and prose cannot prove semantic compliance, deterministic generation, or formal safety.
