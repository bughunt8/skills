# start-github-repo

Renders a repository skeleton with a document spine, community files and workflows for TypeScript/Node and Cloudflare Workers projects, plus agent runtime contracts for the `agent-service` profile.
It bundles 77 templates. A default `worker-service` scaffold plans 56 files, and
`agent-service` plans 71 files.

Templates are **bundled**. There is no network fetch at scaffold time and no dependency on an
external template catalog.

## What it emits

| Group | Contents |
|---|---|
| Document spine | `PRD.md`, `TRD.md`, `WIREFRAME.md`, `DESIGN.md`, `docs/index.md`, `docs/adr/` (template + ADR-0001), `docs/architecture/` (principles, vision, roadmap, building blocks) |
| Root | `README.md`, `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`, `.gitignore`, `.gitattributes`, `.editorconfig`, `.nvmrc`, `.env.example`, `.dev.vars.example` |
| Community health | `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `LICENSE`, `NOTICE` |
| GitHub | three YAML issue forms + `config.yml`, PR template, `CODEOWNERS`, `dependabot.yml`, scoped `.github/AGENTS.md` |
| Workflows | `01-quality-gates`, `02-docs-review`, `03-e2e`, `04-security`, `05-release`, `06-scorecard`, `50-promote-to-staging`, `60-staging-checks`, `80-promote-to-production`, `90-deploy-production`, with least-privilege permissions, concurrency, SHA-pin markers and placeholder steps for the promotion and deployment commands |
| Scripts | `bootstrap`, `setup`, `update`, `server`, `test`, `cibuild`, `console`, `check-docs` |
| Toolchain | `vitest.config.ts`, `playwright.config.ts`, `wrangler.jsonc`, `.changeset/config.json` |
| Agent runtime and human-in-the-loop (`agentic-stack`) | `config/persona.json`, `config/hitl_triggers.json`, `config/system_prompt.md`, `config/vector_store.yaml`, `config/tools.json`, `db/migrations/0001_create_agent_sessions.sql`, `db/migrations/0002_create_hitl_records.sql`, `src/agent/state.ts`, `src/agent/router.ts`, `src/agent/endpoints.ts`, `src/agent/ui_contracts.ts`, `src/agent/agentic_stack.test.ts`, `src/safety/filters.ts`, `tests/eval_dataset.json`, `docs/architecture/hitl-protocol.md` |

## The numbered pipeline

The ten workflow templates carry a two-digit number. Sorted by name, they read in the order work
moves from a pull request to production. Three of the ten are conditional, so a default scaffold
emits nine. Five bands group the numbers:

| Band | Numbers | Files |
|---|---|---|
| Checks | `01`-`49` | `01-quality-gates.yml`, `02-docs-review.yml`, `03-e2e.yml`, `04-security.yml`, `05-release.yml`, `06-scorecard.yml`; `07`-`49` stays free for more checks |
| Staging promotion | `50`-`59` | `50-promote-to-staging.yml`; `51`-`59` stays free |
| Staging actions | `60`-`79` | `60-staging-checks.yml`; `61`-`79` stays free for the other work a staging environment needs |
| Production promotion | `80`-`89` | `80-promote-to-production.yml`; `81`-`89` stays free |
| Production deployment | `90`-`99` | `90-deploy-production.yml`; `91`-`99` stays free |

Inside one workflow, `needs:` gates one job on another. Across workflows, `workflow_run` gates the
staging checks and the production deployment on the promotion that precedes them, and the
repository ruleset gates a pull request: it must require the `check` job from
`01-quality-gates.yml` before a merge. `80-promote-to-production.yml` is the workflow a person
starts for a production deployment. It runs on `workflow_dispatch` alone and refuses anything but
the exact string `PROMOTE`, and `03-e2e.yml`, `05-release.yml` and `50-promote-to-staging.yml`
also accept a manual dispatch. The production deployment sits behind the `production` environment,
so its reviewers approve it, and `05-release.yml` declares the same environment.

The commit that ships is the commit that was verified. `50` checks out the pushed SHA and deploys
that SHA, `60` checks out the SHA the promotion ran on, `80` promotes the staging commit it tested
rather than merging it, and `90` deploys the head commit of the promotion run. The production
promotion is dispatched from the branch that holds the commit to promote and refuses to run when
that branch is not the current staging head, so the promoted commit is fixed at dispatch time. It
waits for a successful staging deployment of that commit and for the staging checks to publish a
passing result on it before it moves the default branch. The staging promotion itself refuses a
dispatch that did not start on the default branch.

`50-promote-to-staging.yml`, `60-staging-checks.yml` and `90-deploy-production.yml` ship with a
`SCAFFOLD-PLACEHOLDER` step. The validator warns once per file instead of failing, because a fresh
scaffold cannot know the deploy command. The skill's Assess step fills each placeholder from the
target's own environment-specific script or from its wrangler config, and a command that cannot
name its environment stays a placeholder. `references/workflow_pipeline.md` holds the assessment
rules and the procedure for adding a workflow to a reserved band.

## Usage

```
/start-github-repo              # interview, plan, confirm, scaffold, assess, validate
/start-github-repo plan         # dry run, writes nothing
/start-github-repo docs         # add only the document spine to an existing repo
/start-github-repo audit        # report missing or stale artifacts
```

Profiles: `worker-service`, `ts-library`, `monorepo`, `docs-site`, `internal-tool`, `agent-service`.
The `agent-service` profile scaffolds contracts and helper code for an agent application in a
Cloudflare Worker with a human-in-the-loop gate. The application must implement agent execution,
HTTP serving and session management.

## Three design decisions

**1. Versions live in a data file.** Every pinned spec and package version lives in
`assets/versions.json` with a `checked_at` field. `SKILL.md` and `references/` never hardcode one.
Package *names* live there too. The Cloudflare Vitest integration changed its name from
`@cloudflare/vitest-pool-workers` to `@cloudflare/vitest-plugin`, so a scaffolder that hardcodes the
name generates broken config.

**2. Defaults are evidence-based.** A file-by-file survey of 14 production repositories
(`cloudflare/workers-sdk`, `vercel/next.js`, `sveltejs/svelte`, `denoland/deno`,
`microsoft/TypeScript`, `openai/openai-node`, `kubernetes/kubernetes`, `nodejs/node`,
`supabase/supabase`, `tailwindlabs/tailwindcss`, `github/docs` and others) is recorded under
`evidence` in `assets/versions.json` and drives the defaults. Notably: **0 of 14 use a
`PULL_REQUEST_TEMPLATE/` directory**, so a single file is the default; **`ISSUE_TEMPLATE/config.yml`
appears in 12 of the 12** repos that have the directory, so it is never omitted; and a code of
conduct is usually a short pointer rather than an inlined document.

**3. Some templates refuse to guess.** The Apache-2.0 licence text and the inlined Contributor
Covenant ship as `REPLACE-WITH-CANONICAL-TEXT` markers rather than paraphrases, because a paraphrased
legal text is worse than none. `validate_repo.py` fails while a marker survives.

## Validators

Four scripts, standard library only, deterministic, no network, `--output {text,json}`, each with
`--self-test` and embedded sample input.

| Script | Purpose |
|---|---|
| `scaffold.py` | Render the manifest. `--dry-run`, `--only <group>`, `--force`, `--print-answers-template` |
| `validate_repo.py` | Artifact presence plus structural traps: missing `permissions:`, unpinned actions, `pull_request_target` with a head checkout, missing `concurrency`, `.env` ignore/negation errors, missing `config.yml`, unresolved markers |
| `validate_docs.py` | Required headings, ID formats, matrix integrity both ways, screen references, ADR links, ADR front matter, unresolved clarification markers, `DESIGN.md` section order |
| `traceability.py` | Rebuild the matrix from PRD IDs, test names and commit scopes. Reports orphans in both directions. `--output markdown` |

```bash
python3 skills/start-github-repo/scripts/scaffold.py --self-test
python3 skills/start-github-repo/scripts/validate_docs.py --self-test
python3 skills/start-github-repo/scripts/validate_repo.py --self-test
python3 skills/start-github-repo/scripts/traceability.py --self-test
```

## The document spine

Each artifact answers exactly one question and owns one set of IDs. Five ID families, assigned once
and never renumbered: `FR-`/`NFR-` (PRD), `US` (stories), `SCR-` (screens), `ADR-` (decisions), `T`
(tasks). One traceability matrix, in `TRD.md` section 4, joins them. CI fails when the join
breaks.

TOGAF ADM supplies a **reference model** through three verbs:
**Understand** (phases A–D), **Specify** (E–F), **Govern** (G–H). Seven deliverables are kept in
`docs/architecture/`; enterprise-level artifacts are deliberately excluded.

`DESIGN.md` follows the Google Labs `design.md` specification.
`npx @google/design.md lint` enforces section order and WCAG AA contrast, and
`export --format dtcg` emits W3C Design Tokens JSON.

### Agent runtime and human-in-the-loop

The `agent-service` profile is the only profile that includes the `agentic-stack` group by
default. Every other profile includes it only when the operator sets `emit_agentic_stack` to
`true`; that answer defaults to `false`. The operator must replace the default `allowed_domains`
value in `config/persona.json` before running the agent in production.

The group emits thirteen shared files and two migrations. Ask the `database` question only when
the group is on. It selects `postgres`, the default, or `sqlite` for both migrations at the same
destination paths. A trigger is a condition in `config/hitl_triggers.json` that can require human
review. A blocking trigger parks the session in `PENDING_HUMAN_APPROVAL` until a human resolves it.
`NOTIFY_ONLY` leaves the session running and is reported separately. The router checks the loop
budget before evaluating triggers and aborts an exhausted session before it can wait for a human.
The scaffold never pre-approves a blocking trigger.
The emitted `vitest.config.ts` discovers `test/**/*.{test,spec}.ts` and
`src/**/*.{test,spec}.ts`, so the project's own test command runs
`src/agent/agentic_stack.test.ts`.
Read `references/agentic_stack_and_hitl.md` for the reviewed blueprint.

## Structure

```
skills/start-github-repo/
├── .claude-plugin/plugin.json
├── SKILL.md
├── README.md
├── assets/
│   ├── manifest.json
│   ├── versions.json
│   └── templates/
├── commands/start-github-repo.md
├── references/
│   ├── agentic_stack_and_hitl.md
│   ├── cloudflare_worker_repo.md
│   ├── document_spine.md
│   ├── github_platform.md
│   ├── release_and_versioning.md
│   ├── repo_hygiene_and_scripts.md
│   ├── traceability_scheme.md
│   └── workflow_pipeline.md
└── scripts/
    ├── scaffold.py
    ├── traceability.py
    ├── validate_docs.py
    └── validate_repo.py
```

## Adjacent skills

`github-repository-setup` audits an existing repository against an external preset catalog. Use it
for drift detection. This skill is for day zero.

## License

MIT.
