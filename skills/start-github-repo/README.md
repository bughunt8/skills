# start-github-repo

Greenfield repository scaffolder for TypeScript/Node and Cloudflare Workers projects. Produces a
repository that passes its own CI on the first push.

Templates are **bundled**. There is no network fetch at scaffold time and no dependency on an
external template catalog.

## What it emits

56 bundled templates, 52 of which apply to a default `worker-service` scaffold.

| Group | Contents |
|---|---|
| Document spine | `PRD.md`, `TRD.md`, `WIREFRAME.md`, `DESIGN.md`, `docs/index.md`, `docs/adr/` (template + ADR-0001), `docs/architecture/` (principles, vision, roadmap, building blocks) |
| Root | `README.md`, `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`, `.gitignore`, `.gitattributes`, `.editorconfig`, `.nvmrc`, `.env.example`, `.dev.vars.example` |
| Community health | `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `LICENSE`, `NOTICE` |
| GitHub | three YAML issue forms + `config.yml`, PR template, `CODEOWNERS`, `dependabot.yml`, scoped `.github/AGENTS.md` |
| Workflows | `ci`, `docs-check`, `security`, `release`, `scorecard`, `e2e` — least-privilege permissions, concurrency, SHA-pin markers |
| Scripts | `bootstrap`, `setup`, `update`, `server`, `test`, `cibuild`, `console`, `check-docs` |
| Toolchain | `vitest.config.ts`, `playwright.config.ts`, `wrangler.jsonc`, `.changeset/config.json` |

## Usage

```
/start-github-repo              # interview, plan, confirm, scaffold, validate
/start-github-repo plan         # dry run — writes nothing
/start-github-repo docs         # add only the document spine to an existing repo
/start-github-repo audit        # report missing or stale artifacts
```

Profiles: `worker-service`, `ts-library`, `monorepo`, `docs-site`, `internal-tool`.

## Three design decisions worth knowing

**1. Versions are data, not prose.** Every pinned spec and package version lives in
`assets/versions.json` with a `checked_at` field. `SKILL.md` and `references/` never hardcode one.
Package *names* are data too — the Cloudflare Vitest integration was renamed from
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
(tasks). One traceability matrix, in `TRD.md` section 4, joins them — and CI fails when the join
breaks.

TOGAF ADM is used as a **reference model, not a process model**, collapsed to three verbs:
**Understand** (phases A–D), **Specify** (E–F), **Govern** (G–H). Seven deliverables are kept in
`docs/architecture/`; enterprise-level artifacts are deliberately excluded.

`DESIGN.md` follows the Google Labs `design.md` specification, so it is machine-checkable —
`npx @google/design.md lint` enforces section order and WCAG AA contrast, and
`export --format dtcg` emits W3C Design Tokens JSON.

## Structure

```
start-github-repo/
├── .claude-plugin/plugin.json
├── commands/start-github-repo.md
└── skills/start-github-repo/
    ├── SKILL.md
    ├── references/     6 files — document spine, GitHub platform, release/versioning,
    │                   Cloudflare, repo hygiene/scripts, traceability
    ├── assets/
    │   ├── manifest.json    file → destination → condition
    │   ├── versions.json    pinned versions + the evidence base
    │   └── templates/       56 files
    └── scripts/        4 stdlib validators
```

## Adjacent skills

`github-repository-setup` audits an existing repository against an external preset catalog — use it
for drift detection. This skill is for day zero.

## License

MIT.
