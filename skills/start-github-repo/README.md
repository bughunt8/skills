# start-github-repo

Renders a repository skeleton with a document spine, community files and workflows for TypeScript/Node and Cloudflare Workers projects, plus agent runtime contracts for the `agent-service` profile.
It bundles 73 templates. A default `worker-service` scaffold plans 52 files, and
`agent-service` plans 67 files.

Templates are **bundled**. There is no network fetch at scaffold time and no dependency on an
external template catalog.

## What it emits

| Group | Contents |
|---|---|
| Document spine | `PRD.md`, `TRD.md`, `WIREFRAME.md`, `DESIGN.md`, `docs/index.md`, `docs/adr/` (template + ADR-0001), `docs/architecture/` (principles, vision, roadmap, building blocks) |
| Root | `README.md`, `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`, `.gitignore`, `.gitattributes`, `.editorconfig`, `.nvmrc`, `.env.example`, `.dev.vars.example` |
| Community health | `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `LICENSE`, `NOTICE` |
| GitHub | three YAML issue forms + `config.yml`, PR template, `CODEOWNERS`, `dependabot.yml`, scoped `.github/AGENTS.md` |
| Workflows | `ci`, `docs-check`, `security`, `release`, `scorecard`, `e2e`, with least-privilege permissions, concurrency and SHA-pin markers |
| Scripts | `bootstrap`, `setup`, `update`, `server`, `test`, `cibuild`, `console`, `check-docs` |
| Toolchain | `vitest.config.ts`, `playwright.config.ts`, `wrangler.jsonc`, `.changeset/config.json` |
| Agent runtime and human-in-the-loop (`agentic-stack`) | `config/persona.json`, `config/hitl_triggers.json`, `config/system_prompt.md`, `config/vector_store.yaml`, `config/tools.json`, `db/migrations/0001_create_agent_sessions.sql`, `db/migrations/0002_create_hitl_records.sql`, `src/agent/state.ts`, `src/agent/router.ts`, `src/agent/endpoints.ts`, `src/agent/ui_contracts.ts`, `src/agent/agentic_stack.test.ts`, `src/safety/filters.ts`, `tests/eval_dataset.json`, `docs/architecture/hitl-protocol.md` |

## Usage

```
/start-github-repo              # interview, plan, confirm, scaffold, validate
/start-github-repo plan         # dry run, writes nothing
/start-github-repo docs         # add only the document spine to an existing repo
/start-github-repo audit        # report missing or stale artifacts
```

Profiles: `worker-service`, `ts-library`, `monorepo`, `docs-site`, `internal-tool`, `agent-service`.
The `agent-service` profile scaffolds contracts and helper code for an agent application in a
Cloudflare Worker with a human-in-the-loop gate. The application must implement agent execution,
HTTP serving and session management.

## Three design decisions worth knowing

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
│   └── traceability_scheme.md
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
