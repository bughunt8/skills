# Cloudflare Workers Repository Conventions

Answers one decision: **what a Workers repo needs that a plain Node repo does not.**

Read pinned package names and versions from `assets/versions.json`. The package naming in this
ecosystem changes; the name itself is pinned data, not prose.

---

## 1. Configuration file

`wrangler.toml`, `wrangler.json` and `wrangler.jsonc` are all supported. **Scaffold
`wrangler.jsonc`** — it is what `create-cloudflare` generates, and comments in config are worth
having. Convert an existing project with `npx wrangler config migrate`.

Cloudflare's own rule: **"treat Wrangler's configuration file as the source of truth."** Set
`keep_vars = true` only if dashboard-set variables must survive deploys.

Sources: [Wrangler configuration](https://developers.cloudflare.com/workers/wrangler/configuration/) ·
[Wrangler migration](https://developers.cloudflare.com/workers/wrangler/migration/) ·
[Workers get started](https://developers.cloudflare.com/workers/get-started/guide/)

---

## 2. Environment variables and secrets — the traps

| Concern | Convention |
|---|---|
| Non-secret config | `[vars]` in the Wrangler config, or the dashboard |
| Local secrets | `.dev.vars`, or `.env`, next to the Wrangler config, dotenv syntax |
| Per-environment local secrets | `.dev.vars.<environment>` / `.env.<environment>` |
| Production secrets | `wrangler secret put <KEY>` |
| Version-scoped secrets | `wrangler versions secret put <KEY>` then `wrangler versions deploy` |
| Bulk | `--secrets-file` on `wrangler deploy` / `versions upload`, up to 100 per request |

**Three traps to encode in the template comments:**

1. **`vars` is non-inheritable across named environments.** Every variable must be redefined in every
   environment block. Target one with `--env`/`-e`, e.g. `npx wrangler dev --env staging`.
2. **If `.dev.vars.<environment>` exists, only that file loads.** `.dev.vars` is skipped entirely and
   every secret must be redefined in the environment-specific file.
3. **`process.env` is not native.** It requires `nodejs_compat` plus
   `nodejs_compat_populate_process_env`, which is the default for compatibility dates at or after the
   documented cutover. Otherwise import `env` from `cloudflare:workers`.

`.env` file layering, lowest to highest precedence: `.env` → `.env.<environment>` → `.env.local` →
`.env.<environment>.local`.

**`.dev.vars.example` is not a Cloudflare-documented convention.** Shipping one is a reasonable
extrapolation from `.env.example`, and the template says so in a comment rather than implying it is
official.

Cloudflare's own framing is worth quoting in SECURITY-adjacent docs: **"Secrets are environment
variables"** — the difference is that values are not visible after definition.

**Secrets Store** binds with `binding`, `store_id` and `secret_name`, and **access on `env` is
async** — a real code-shape difference. CLI: `wrangler secrets-store store create <name> --remote`,
`wrangler secrets-store secret create`, `wrangler secrets-store store list`. API tokens need
`Secrets Store Write`.

Sources: [environment variables (config)](https://developers.cloudflare.com/workers/configuration/environment-variables/) ·
[environment variables (dev/test)](https://developers.cloudflare.com/workers/development-testing/environment-variables/) ·
[secrets](https://developers.cloudflare.com/workers/configuration/secrets/) ·
[Secrets Store + Workers](https://developers.cloudflare.com/secrets-store/integrations/workers/)

---

## 3. Typed bindings

`wrangler types` generates `worker-configuration.d.ts` containing the `Env` interface. Add it to
`tsconfig.json` `compilerOptions.types`, **commit it**, and verify freshness in CI:

```bash
wrangler types --check
```

Options include `--path`, `--include-env`, `--check`, `--env-interface <name>`.

A newer `secrets` config object with `secrets.required` (a string array) makes `wrangler types`
generate typed bindings from that declared list instead of inferring from `.dev.vars`/`.env`, and
makes `wrangler deploy` / `wrangler versions upload` validate that the required secrets exist. Prefer
it when available — it turns a runtime surprise into a deploy-time failure.

Cloudflare recommends `wrangler types` over `@cloudflare/workers-types`, and installing `@types/node`
when `nodejs_compat` is enabled.

For plain (non-binding) environment variables, layer runtime schema validation with `@t3-oss/env-core`
plus Zod. It is ESM-only and needs module resolution `Bundler`. If server variable *names* are
themselves sensitive, split client and server schemas into two files.

Sources: [TypeScript on Workers](https://developers.cloudflare.com/workers/languages/typescript/) ·
[t3-env core](https://env.t3.gg/docs/core)

---

## 4. Testing — and the rename that breaks stale scaffolds

**The Workers Vitest integration was renamed.** `@cloudflare/vitest-pool-workers` is now
`@cloudflare/vitest-plugin`, and the entry point is the `cloudflareTest()` plugin. Anything generating
`defineWorkersConfig` is generating stale code. The Vitest configuration API itself is unchanged.

Migration for an existing repo:

```bash
npx @cloudflare/codemods vitest:pool-workers-to-vitest-plugin --dry-run
npx @cloudflare/codemods vitest:pool-workers-to-vitest-plugin
```

It updates the dependency name, package imports and TypeScript `types` entries. The rename applies to
subpath imports too (`@cloudflare/vitest-plugin/config`). Outbound request mocking moved to
`@msw/cloudflare`.

Prerequisites: a compatibility date at or after the documented minimum, an ES-modules Worker, and both
packages as dev dependencies. Configure via `wrangler.configPath`; a `miniflare` block in the config
**takes precedence over** values from the Wrangler config. The tests folder `tsconfig.json` must add
`@cloudflare/vitest-plugin` to `types` (that is what defines `cloudflare:test`) and include the
`wrangler types` output.

**Two tiers, which map onto the testing trophy:**

- **Unit/integration in-runtime** — tests run inside the Workers runtime, so they can assert directly
  against binding state: values written to KV, R2, D1 or Durable Objects. Integration tests can use
  the `exports` object from `cloudflare:workers` and call `exports.default.fetch()`.
- **`createTestHarness()`** — compatible with any Node test runner and with Playwright or MSW.

Everything runs fully locally on Miniflare.

Sources: [Vitest integration](https://developers.cloudflare.com/workers/testing/vitest-integration/) ·
[write your first test](https://developers.cloudflare.com/workers/testing/vitest-integration/write-your-first-test/) ·
[migrate to Vitest plugin](https://developers.cloudflare.com/workers/testing/vitest-integration/migration-guides/migrate-to-vitest-plugin/) ·
[Workers testing overview](https://developers.cloudflare.com/workers/testing/) ·
[changelog: vitest-plugin rename](https://developers.cloudflare.com/changelog/post/2026-08-19-vitest-plugin/)

---

## 5. Docs site hosting, if the profile needs one

| Tool | Config | Cloudflare path | Search |
|---|---|---|---|
| Astro Starlight | `astro.config.mjs`, content in `src/content/docs/` | **Workers** via `@astrojs/cloudflare`; `astro add cloudflare` then `npx wrangler deploy` | Pagefind by default, zero config |
| Docusaurus | `docusaurus.config.ts` | **Pages**, framework preset "Docusaurus", build `npm run build`, output `build` | Algolia DocSearch official |
| VitePress | `.vitepress/config.ts` | **Pages**, build `npm run docs:build`, output `docs/.vitepress/dist` | built-in |
| MkDocs Material | `mkdocs.yml` | not documented by Cloudflare | client-side lunr, on by default |
| mdBook | `book.toml` | not documented by Cloudflare | built-in |

**Starlight is the only option with a first-class, Cloudflare-documented Workers path plus zero-config
search.** Docusaurus is the safest Pages choice. For most new repos, skip all of them and keep flat
markdown in `docs/` — it stays consumable by any of these later.

Sources: [Astro on Cloudflare](https://docs.astro.build/en/guides/deploy/cloudflare/) ·
[Starlight site search](https://starlight.astro.build/guides/site-search/) ·
[Docusaurus on Cloudflare Pages](https://developers.cloudflare.com/pages/framework-guides/deploy-a-docusaurus-site/) ·
[VitePress deploy](https://vitepress.dev/guide/deploy) ·
[MkDocs Material publishing](https://squidfunk.github.io/mkdocs-material/publishing-your-site/) ·
[mdBook CI](https://rust-lang.github.io/mdBook/continuous-integration.html)

---

## 6. Deploy workflow shape

- Build and test on `pull_request`; deploy only from the default branch or a tag.
- Use an environment with protection rules for production.
- Prefer OIDC where the provider supports it; otherwise a single scoped API token in a repository
  secret named in `.env.example` by purpose, never by value.
- Name the environments in the Wrangler config and in `docs/index.md` so the mapping between
  `--env staging` and the GitHub environment is written down somewhere.
