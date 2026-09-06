# AGENTS.md

Instructions for an AI agent working inside this repository. Read this before editing
anything here.

## What this repository is

A library of 470 skill files across 22 directories, 469 of which are linted; the difference is
one deliberate test fixture. There is no application, no build, no
tests to run against behaviour. Every file is an instruction to some other agent, in a
future session, with credentials you do not have. Write accordingly.

## The five rules

1. **Do not edit anything under a vendored directory.** Currently `skills/pstack/` and
   `skills/job-hunt/`. Those files are copies, and the fortnightly sync overwrites them. The
   authoritative list of vendored destinations is the `dest` field of each source in
   `skills/vendor.manifest.json`.
2. **Do not hand-edit generated files.** They carry a banner saying so. That covers the
   block between the `BEGIN GENERATED` and `END GENERATED` markers in `README.md`,
   `THIRD_PARTY_NOTICES.md`, every `PROVENANCE.md`, and every vendored `ATTRIBUTION.md`.
   Change the script or the data it reads, then run the script.
3. **Do not import someone else's work by copying files.** Add a source to
   `skills/vendor.manifest.json` and run `scripts/sync_vendor.py --sync`. That is the only
   path that produces correct licence, author and commit-pinned attribution, and CI rejects
   an import that lacks them.
4. **Run the three checks before you claim to be finished.** Not "should pass". Run them.
5. **Apply `skills/pstack/unslop/SKILL.md` to every sentence you write here,** including
   commit messages and pull request bodies. It is a mandatory import for exactly this reason.

## The three checks

```bash
python3 scripts/lint_skills.py --self-test         # the frontmatter parser refuses what it cannot read
python3 scripts/lint_skills.py                     # SK001-SK009 on every SKILL.md
python3 scripts/generate_index.py --check          # README index matches the tree
python3 scripts/sync_vendor.py --validate-manifest # provenance, licences, ownership records
python3 scripts/audit_third_party.py               # every licence marker is accounted for
python3 scripts/check_links.py                     # relative links resolve
```

All offline. Standard library plus PyYAML, which CI installs. These are exactly the steps in
`.github/workflows/ci.yml`, so a green local run means a green pull request. Run them. Do not
report "should pass".

`scripts/lint_skills.py --strict` shows the 68 findings the baseline currently accepts. Do not add
to that number. `--write-baseline` exists, and using it to silence a violation you introduced is
the wrong move.

## Adding a skill

```
skills/<domain>/<skill-name>/SKILL.md
```

Frontmatter `name` must equal the directory name, lowercase kebab-case. The `description` is
the only text a routing agent sees before deciding whether to load the skill, so it must say
what the skill does, when to use it, and what to use instead. Ceiling is 1024 characters.

Check the name is free first. There are already 32 duplicate-name findings in the baseline
and each one is a live risk of the wrong skill loading.

New domain: add a line to `docs/domain-descriptions.json`, then
`python3 scripts/generate_index.py --write`.

## Where things are

```
skills/                        one directory per domain
skills/vendor.manifest.json    every vendored upstream: repo, author, licence, commit pin, exclusions
skills/pstack/                 vendored, read-only, refreshed automatically
skills/job-hunt/               vendored, read-only. skills/ plus the guides/ and templates/ they link into
scripts/sync_vendor.py         first import and every refresh use this one code path
scripts/lint_skills.py         SKILL.md metadata validation
scripts/generate_index.py      regenerates the README index from the tree
scripts/audit_third_party.py   reconciles licence markers against docs/third-party-inventory.json
scripts/check_links.py         relative links resolve, used by CI
scripts/sync_due.py            whether a refresh is due
scripts/skill_lint_baseline.json  accepted pre-existing violations, plus non-skill path ignores
docs/ARCHITECTURE_REVIEW.md    the audit this structure came from, and the open backlog
docs/domain-descriptions.json  human prose for the generated index
.github/workflows/ci.yml       the three checks, on every push and pull request
.github/workflows/sync-vendored-skills.yml  fortnightly upstream refresh, opens a pull request
```

## Things that will trip you up

- **The fortnightly cadence is a weekly cron with an even-ISO-week gate.** GitHub cron
  cannot express "every two weeks". Do not simplify the gate away.
- **A pull request opened by `GITHUB_TOKEN` cannot trigger `ci`.** The sync workflow
  therefore runs the three checks itself. If you move those steps out, the automated pull
  requests become unverified.
- **`--check` exits 1 when upstream moved.** That is a report, not a failure. Only
  `--validate-manifest` belongs in a blocking gate, because it needs no network.
- **`--validate-manifest` checks declarations, not truth.** It proves the tree matches what the
  manifest claims and that provenance, licence copies and ownership records exist. It cannot
  prove an upstream had the right to license what it published, or that a declared author is the
  real one. Do not describe it as licence verification.
- **Symlinks in an upstream tree are a hard error, not a warning.** Following one would let
  upstream publish the contents of an arbitrary runner path into a public pull request.
- **Never hand-edit `.vendor-owned.json`.** The sync writes it to know what to delete next time.
  Editing it either orphans content or deletes something it should not.
- **The cadence is measured in days, not weeks.** `scripts/sync_due.py` reads `pinned_at` from
  the manifest. An even-ISO-week gate was tried and produces 21-day gaps; `--self-test` shows
  them. Do not replace this with cron arithmetic.
- **`poteto-mode` fails SK004 and SK005** because upstream names it `Poteto Mode`. It is
  reported as a warning, not an error, because vendored content cannot be corrected here.
  Do not "fix" it in place.
- **Some vendored skills assume a Cursor-style multi-model runner** (`poteto-mode`,
  `setup-pstack`, `arena`). The discipline is portable; the model names are not.
- **A vendored source can map several upstream subtrees, not one.** job-hunt-skills has 47
  links from its skills into a sibling `guides/` directory. The manifest maps `skills/`,
  `guides/` and `templates/` at the same relative distance so those links keep resolving.
  If you add a source, check its internal links before assuming `skills/` is self-contained.
- **`skills/job-hunt/skills/_shared/` has no SKILL.md** and is not a skill. It holds the
  shared state-layer contract. It is exempt from the per-skill provenance rule by design.
- **The job-hunt export toolchain is not vendored.** Upstream needs Node 22 and Typst for
  DOCX and PDF output. Markdown workflows are unaffected. Do not vendor the scripts without
  adding Node CI to keep them honest.

## Commit convention

Conventional Commits. `feat(skills):`, `chore(vendor):`, `docs(readme):`, `fix(scripts):`.
