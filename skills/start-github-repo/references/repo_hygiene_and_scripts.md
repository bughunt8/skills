# Repo Hygiene, Environment Files and Automation Scripts

Answers one decision: **which root files to emit, what goes in them, and how the `scripts/` directory
is organised.**

---

## 1. `.gitignore` — use GitHub's own idiom verbatim

```gitignore
# dotenv environment variable files
.env
.env.*
!.env.example
```

This is also the **strongest available evidence that `.env.example` is the conventional name**: it is
the only filename GitHub's default Node template negates. Add `.dev.vars` and `.dev.vars.*` with a
matching `!.dev.vars.example` negation for Workers profiles.

Source: [github/gitignore Node.gitignore](https://github.com/github/gitignore/blob/main/Node.gitignore)

---

## 2. `.gitattributes`

```gitattributes
* text=auto

pnpm-lock.yaml            linguist-generated
package-lock.json         linguist-generated
worker-configuration.d.ts linguist-generated
```

- `* text=auto` normalizes text to LF in the index. Re-apply to an existing repo with
  `git add --renormalize .`. Use `-text` to disable and `path -text` for binaries. `eol=lf`/`eol=crlf`
  only take effect where `text` is set.
- **`linguist-generated` both excludes a file from language statistics and collapses its diff by
  default** — this is the actual mechanism people want when they say "hide lockfile diffs".
  `linguist-vendored` only excludes from statistics.
- `export-ignore` keeps files out of `git archive` output.
- `merge=union` exists for changelog-style files but the Git docs warn it "tends to leave the added
  lines in the resulting file in random order and the user should verify the result. Do not use this if
  you do not understand the implications." Prefer changesets-style intent files, which avoid the
  conflict entirely.

Sources: [gitattributes](https://git-scm.com/docs/gitattributes) ·
[Linguist overrides](https://github.com/github-linguist/linguist/blob/main/docs/overrides.md) ·
[customizing how changed files appear](https://docs.github.com/en/repositories/working-with-files/managing-files/customizing-how-changed-files-appear-on-github)

---

## 3. `.editorconfig`

Lowercase filename, UTF-8, INI-like. Keys worth setting: `root = true` in the preamble (search stops
there), `indent_style`, `indent_size`, `end_of_line = lf`, `charset = utf-8`,
`trim_trailing_whitespace`, `insert_final_newline`. Use `unset` to clear an inherited value. Keys are
case-insensitive. Glob syntax supports `*`, `**`, `?`, `[name]`, `[!name]`, `{s1,s2}`, `{num1..num2}`.

Source: [EditorConfig specification](https://spec.editorconfig.org/)

---

## 4. Toolchain pinning — stack three layers

| Layer | File / field | Behaviour |
|---|---|---|
| Local shell | `.nvmrc` (or `.node-version`) | One version string plus newline, searched upward; accepts `lts/*` and `node`; `#` comments allowed |
| Advisory floor | `engines` in `package.json` | **Advisory unless `engine-strict` is enabled**; `version` must parse with node-semver |
| Package manager | `packageManager` in `package.json` | `name@x.y.z`, hash optional but strongly recommended; Corepack enforces it |

`devEngines.packageManager` adds `onFail` (`ignore`/`warn`/`error`) and is checked before
`install`/`ci`/`run`. Volta is the alternative — `volta pin node@…` writes a `volta` block into
`package.json`. Corepack escape hatches: `COREPACK_ENABLE_STRICT=0`, `COREPACK_ENABLE_PROJECT_SPEC=0`.

Sources: [nvm](https://github.com/nvm-sh/nvm) ·
[npm package.json](https://docs.npmjs.com/cli/v11/configuring-npm/package-json) ·
[Corepack](https://nodejs.org/api/corepack.html) ·
[Volta](https://docs.volta.sh/guide/understanding)

---

## 5. Env layering for non-Workers profiles

| Framework | Precedence, lowest → highest |
|---|---|
| Vite | `.env` → `.env.local` → `.env.[mode]` → `.env.[mode].local`; shell env always wins |
| Next.js | `process.env` → `.env.$(NODE_ENV).local` → `.env.local` → `.env.$(NODE_ENV)` → `.env` |
| dotenv-flow | `.env` → `.env.local` → `.env.<NODE_ENV>` → `.env.<NODE_ENV>.local` → shell env |

Notes worth putting in `.env.example` comments: only prefixed variables are exposed to client bundles
(`VITE_`, `NEXT_PUBLIC_`), `NEXT_PUBLIC_` values are **inlined at build time and frozen** so dynamic
lookups fail, and `.env.local` is skipped when `NODE_ENV=test` in both Next.js and dotenv-flow.

**`.env` must never be committed.** dotenv's own FAQ: "Should I commit my `.env` file? No. Unless you
encrypt it with dotenvx." **dotenvx** is the escape hatch if committed secrets are genuinely wanted: it
encrypts `.env` with ECIES, keeping a `DOTENV_PUBLIC_KEY` in the file and the private key in
`.env.keys`, so the encrypted file is safe to commit. Useful commands: `dotenvx ext genexample`,
`dotenvx ext gitignore`, `dotenvx ext precommit --install`. **direnv** is the per-directory shell
alternative via `.envrc`; it needs a shell hook and cannot export aliases or functions.

Sources: [Vite env and mode](https://vite.dev/guide/env-and-mode) ·
[Next.js environment variables](https://nextjs.org/docs/app/guides/environment-variables) ·
[dotenv-flow](https://github.com/kerimdzhanov/dotenv-flow) ·
[dotenv](https://github.com/motdotla/dotenv) ·
[dotenvx](https://github.com/dotenvx/dotenvx) ·
[direnv](https://direnv.net/)

---

## 6. Secret-leak prevention

| Tool | Config | Notes |
|---|---|---|
| gitleaks | `.gitleaks.toml` | MIT. `detect`/`protect` are deprecated; `[[allowlists]]` replaced `[allowlist]`; `.gitleaksignore` is experimental |
| trufflehog | `--config` for custom detectors | AGPL-3.0. Action needs `actions/checkout` with `fetch-depth: 0`; use `--results=verified,unknown` |
| git-secrets | `.gitallowed` | Apache-2.0. Installs its own hooks; `--no-verify` bypasses it |

**Durability warning:** gitleaks describes itself as feature-complete, with future releases limited to
security patches while the maintainer moves to a successor project. Keep secret scanning behind a
single switch in `manifest.json` so it can be swapped. **GitHub push protection is the durable layer**
— see `github_platform.md` §8.

**Hook runners:**

| Runner | Config | Trade-off |
|---|---|---|
| husky + lint-staged | `.husky/pre-commit` + `lint-staged` in `package.json` | Pure npm, no Python. `npx husky init` writes the `prepare` script. `HUSKY=0` disables |
| lefthook | `lefthook.yml` (+ `lefthook-local.yml`) | Single YAML, parallel jobs, `{staged_files}` placeholders |
| pre-commit | `.pre-commit-config.yaml` | Widest hook ecosystem, but adds a Python dependency |

**Default to husky + lint-staged** for a Node repo. A sensible staged-file set: a secret scan,
`prettier --write`, `eslint --fix`, and `shellcheck` for anything under `scripts/`. **Type-checking
cannot be scoped to staged files — `tsc --noEmit` belongs in CI, not a pre-commit hook.**

```json
{ "lint-staged": { "*.{ts,tsx}": "eslint --fix", "*.{ts,tsx,md,json}": "prettier --write" } }
```

Sources: [gitleaks](https://github.com/gitleaks/gitleaks) ·
[trufflehog](https://github.com/trufflesecurity/trufflehog) ·
[git-secrets](https://github.com/awslabs/git-secrets) ·
[husky](https://typicode.github.io/husky/get-started.html) ·
[lint-staged](https://github.com/lint-staged/lint-staged) ·
[lefthook](https://github.com/evilmartians/lefthook) ·
[pre-commit](https://pre-commit.com/)

---

## 7. `scripts/` — names from GitHub, directory from Node

GitHub's canonical pattern is **`script/`** singular, with fixed responsibilities:

| Script | Responsibility (verbatim) |
|---|---|
| `bootstrap` | "used solely for fulfilling dependencies of the project" |
| `setup` | "used to set up a project in an initial state… typically run after an initial clone, or, to reset the project back to its initial state" |
| `update` | "used to update the project after a fresh pull… Typically, `script/bootstrap` is run inside this script" |
| `server` | "used to start the application… `script/update` should be called ahead of any application booting" |
| `test` | "used to run the test suite… Linting… can also be considered a form of testing… put them towards the beginning" |
| `cibuild` | "used for your continuous integration server… typically only called from your CI server" |
| `console` | "used to open a console for your application" |

**Use `scripts/` plural with those names.** Every JavaScript repo in the survey uses the plural form,
and the singular/plural question has no authoritative arbiter. Alias each from an npm script so both
entry points work.

**Split `bin/` from `scripts/`.** The cleanest convention observed: `bin/` holds release gating
(`check-release-version`, `publish-npm`) and `scripts/` holds the dev lifecycle. It makes "which of
these can I safely run locally?" answerable at a glance.

Shell hygiene for every emitted script: a shebang, `set -euo pipefail`, executable bit, and
`shellcheck` + `shfmt` in CI. shellcheck's own README points onward: "ShellCheck does not attempt to
enforce any kind of formatting or indenting style, so also check out shfmt!"

npm `pre`/`post` hooks let STRTA-style ordering be expressed without a second task runner — a
`precompress` script runs before `compress` automatically, and the same applies to `test` and `start`.

**Task runners, if npm scripts are not enough:** Taskfile (`Taskfile.yml`) bundles a native Go shell
interpreter so commands work on Windows, and `task --list` prints tasks with their `desc`. `just`
(`justfile`) has `just --list`, `--summary`, and `set default-list := true`. Neither appeared in any
surveyed repo — 0 of 14 — so do not scaffold one by default.

Sources: [github/scripts-to-rule-them-all](https://github.com/github/scripts-to-rule-them-all) ·
[npm scripts](https://docs.npmjs.com/cli/v11/using-npm/scripts) ·
[shellcheck](https://github.com/koalaman/shellcheck) ·
[shfmt](https://github.com/mvdan/sh) ·
[Taskfile getting started](https://taskfile.dev/docs/getting-started) ·
[just manual](https://just.systems/man/en/listing-available-recipes.html)

---

## 8. Do not create a `.config/` directory

The one serious standardization attempt — a Node.js tooling issue with 47+ participants titled "the
creeping scourge of tooling config files in project root directories" — was **closed without
consensus**: "I don't think we're going to be able to get consensus on a new config directory. Getting
all tools to allow you to customize the location of the config file seems more realistic."

Objections worth knowing, because they recur: moving `package.json` breaks tools that assume its
location and Node's handling of the `type` field; ESLint config "composes up the hierarchy and
describes the current folder"; and several participants argued the honest fix is *fewer* config files
rather than relocated ones. There is no standard to follow — keep config at the root.

Source: [nodejs/tooling#79](https://github.com/nodejs/tooling/issues/79)

---

## 9. `docs/` layout

`docs/` in this template is the **architecture repository plus decision log**, not a documentation
site. That is defensible: in the survey `docs/` was rarely product documentation — one repo keeps a
deliberately empty `docs/` stub, and others use `doc/`, `documentation/` or `contributing/` instead.
Only two of fourteen ship real product docs under `docs/`.

If a docs site is later wanted, structure the content by **Diátaxis** — four quadrants, each with a
different orientation:

| Quadrant | Orientation |
|---|---|
| Tutorials | learning-oriented |
| How-to guides | goal-oriented |
| Reference | information-oriented |
| Explanation | understanding-oriented |

A flat `docs/` with `tutorials/`, `how-to/`, `reference/`, `explanation/` gives the structure with zero
tooling and stays consumable by every markdown-sourced generator.

Source: [Diátaxis](https://diataxis.fr/)
