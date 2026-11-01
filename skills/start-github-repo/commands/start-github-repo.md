---
name: "start-github-repo"
description: "/start-github-repo [plan | docs | audit | <profile>] scaffolds a GitHub repository from zero: README, AGENTS.md, LICENSE, CODE_OF_CONDUCT, CHANGELOG, issue forms, PR template, hardened workflows, SECURITY.md, SUPPORT.md, env examples, automation scripts, docs/, and a PRD/TRD/TOGAF-ADM/WIREFRAME/DESIGN spine with a traceability matrix. The agent-service profile adds runtime contracts and helper code for human approval. Use at day zero, or with `docs` to add the spine to an existing repo."
---

# /start-github-repo

**Command:** `/start-github-repo [plan | docs | audit | <profile>]`

Renders bundled repository templates without a network fetch or an external catalog.

## Modes

| Invocation | Behaviour |
|---|---|
| `/start-github-repo` | Interview → plan → confirm → scaffold → validate → summarize |
| `/start-github-repo plan` | Print the resolved file list, secrets and manual settings. Writes nothing. |
| `/start-github-repo docs` | Emit only the document spine into an existing repository |
| `/start-github-repo audit` | Report missing or stale template artifacts. Writes nothing. |
| `/start-github-repo worker-service` | Skip the profile question |

Profiles: `worker-service`, `ts-library`, `monorepo`, `docs-site`, `internal-tool`, `agent-service`.
The `agent-service` profile scaffolds contracts and helper code for an agent application in a
Cloudflare Worker with a human-in-the-loop gate. The application must implement agent execution,
HTTP serving and session management.

## The eight questions

Each core question has a default, so `--defaults` skips the interview.

1. Project name (kebab-case)
2. One-line description, under 120 characters
3. Profile
4. License, default `MIT`
5. Visibility, default `private`
6. Package manager, default `pnpm`
7. Code of conduct reporting contact
8. Release tooling, default `changesets`

### Conditional database question

Ask this question only when the agentic stack is on, which means the `agent-service` profile or
an explicit opt-in on another profile. Ask which database dialect to use: `postgres` or `sqlite`.
Default to `postgres`. Derive the remaining answers.

## Agentic stack

The `agentic-stack` group, labelled "Agent runtime and human-in-the-loop", always applies to
`agent-service`, the only profile with `agentic: true`. Every other profile includes it only when
the operator sets `emit_agentic_stack` to `true`; that answer defaults to `false`.
`--only agentic-stack` selects this group without changing its conditions.

It emits these destination files. `database` selects the dialect for the two migrations.

```text
config/persona.json
config/hitl_triggers.json
config/system_prompt.md
config/vector_store.yaml
config/tools.json
db/migrations/0001_create_agent_sessions.sql
db/migrations/0002_create_hitl_records.sql
src/agent/state.ts
src/agent/router.ts
src/agent/endpoints.ts
src/agent/ui_contracts.ts
src/agent/agentic_stack.test.ts
src/safety/filters.ts
tests/eval_dataset.json
docs/architecture/hitl-protocol.md
```

A project's own test command runs `src/agent/agentic_stack.test.ts` because the emitted
`vitest.config.ts` discovers both `test/**/*.{test,spec}.ts` and `src/**/*.{test,spec}.ts`.

A blocking trigger parks the session in `PENDING_HUMAN_APPROVAL` until a human resolves it.
`NOTIFY_ONLY` leaves the session running and is reported separately. The router checks the loop
budget before evaluating any trigger and aborts an exhausted session before human approval.
Never pre-approve a blocking trigger.
Replace the default `allowed_domains` in `config/persona.json` before production use.

## Six forcing questions before this scaffold is considered done

### 1. Is every placeholder resolved, or reported?

A scaffold that ships `TODO` in a licence file or a reporting contact is worse than no file. Two
templates deliberately refuse to guess: the Apache-2.0 licence text and the inlined Contributor
Covenant both carry a `REPLACE-WITH-CANONICAL-TEXT` marker rather than a paraphrase, because a
paraphrased legal text is a liability. `validate_repo.py` fails while either marker survives.

Run: `python3 scripts/validate_repo.py --root <target>`

### 2. Are all action pins resolved to full-length SHAs?

A tag can be moved; a SHA cannot. Every workflow ships with `# SCAFFOLD-PIN-SHA` comments and
`validate_repo.py` reports one error per file until they are gone. This is the single gated step
between a scaffolded repo and one with resolved action pins. Do not report readiness while it fails.

### 3. Does the document spine hold together in both directions?

Every `FR-`/`NFR-` in the PRD must appear in the TRD traceability matrix, and every matrix row must
cite a requirement that exists. Every `SCR-` referenced in the PRD must be specified in WIREFRAME.
Every ADR link in the TRD must resolve.

Run: `python3 scripts/validate_docs.py --root <target>`

### 4. Will `DESIGN.md` survive its own linter?

The canonical section order is enforced by `design.md` lint, and the `contrast-ratio` rule fails any
component colour pair below WCAG AA 4.5:1. The Motion, Breakpoints, States and Accessibility extensions
must come **after** the canonical sections or `section-order` fails.

Run: `npx --yes @google/design.md lint DESIGN.md`

### 5. Is `AGENTS.md` still under 200 lines, and still delegating?

Bloat makes agents ignore the instructions that matter. Every line must earn its place: would
removing it cause a mistake? Facts that live in `package.json`, `CONTRIBUTING.md` or the PR template
must appear as references, not copies. Copied versions and counts go stale.

### 6. Have remote mutations been confirmed separately?

File generation is local and reversible. Ruleset creation, label sync, secret creation and repository
settings are not. Each needs its own approval, listed by name, after the files land.

## Hard rules

- Never overwrite a file without showing the diff and getting approval. Use `--force` only after that.
- Never invent a command. Emit only what the chosen profile supports.
- Never write a secret value. `.env.example` and `.dev.vars.example` carry empty values and comments.
- Never hardcode a version in prose. `assets/versions.json` is the single source of truth, including
  package *names*. The Cloudflare Vitest package was renamed, so the name is data too.

## Verification

```bash
python3 scripts/scaffold.py --self-test
python3 scripts/validate_docs.py --self-test
python3 scripts/validate_repo.py --self-test
python3 scripts/traceability.py --self-test
```

All four are stdlib-only, deterministic, carry embedded sample input, and support
`--output {text,json}`.

## Adjacent

`github-repository-setup` audits a repository that already exists against an external preset catalog.
Use it for drift detection; use this command for day zero.
