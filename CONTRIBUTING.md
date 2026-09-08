# Contributing

This repository is a library of agent skills. It has no build and no runtime, so every
guarantee it offers is about metadata, structure and provenance. The rules below exist to
protect those three things.

## Before you open a pull request

Run the same three checks CI runs. All of them are Python standard library only, so there
is nothing to install.

```bash
python3 scripts/lint_skills.py --self-test         # the frontmatter parser refuses what it cannot read
python3 scripts/lint_skills.py                     # SK001-SK009 on every SKILL.md
python3 scripts/generate_index.py --check          # the README index still matches the tree
python3 scripts/sync_vendor.py --validate-manifest # provenance, licences, ownership records
python3 scripts/audit_third_party.py               # every licence marker is accounted for
python3 scripts/check_links.py                     # relative links resolve
```

Install PyYAML first if you do not have it (`python3 -m pip install PyYAML`). Without it the
linter falls back to a parser that refuses YAML it cannot read, which is safe but noisier.

`python3 scripts/lint_skills.py --strict` shows the full backlog including the 68 findings the
baseline currently accepts. Fixing one is always a welcome pull request. Two of them,
`markdown-html/skills/design-system` and `markdown-html/skills/md-slides`, have frontmatter no
YAML loader can parse, so they are broken rather than untidy and are the best place to start.

## Adding a skill you wrote

1. Create `skills/<domain>/<skill-name>/SKILL.md`.
2. The directory name and the frontmatter `name` must be identical, lowercase kebab-case.
   Skill invocation is `/<name>`, and a mismatch makes that unpredictable.
3. `description` is the only thing an agent sees before deciding whether to load the skill.
   Write it for that decision: what the skill does, when to use it, what to use instead.
   1024 characters is the ceiling.
4. Check the name is not already taken. There are 32 duplicate-name findings in the
   baseline already, and they are a real source of the wrong skill loading.
5. Add the domain to `docs/domain-descriptions.json` if it is new, then run
   `python3 scripts/generate_index.py --write`.

## Adding a solution

A Solution Skill chains existing skills in order to solve one concrete problem. It lives in
`solutions/<name>.md` with frontmatter `name`, `problem`, `summary`, `composed_by`, `steps`
(an ordered list of `{skill, handoff, why}`), and `prompt` — the drop-in hand-off message
another LLM executes.

1. Every `skill` in `steps` must be a real frontmatter `name` in `skills/`, and it must be
   unambiguous. `python3 scripts/check_solutions.py` fails on a dangling or ambiguous name.
2. A solution references skills by name and never copies their text. Write the `prompt` fresh.
3. The credit is `composed_by` — "composed by", never "built by". The skills stay their authors'.
4. Run `python3 scripts/check_solutions.py`, then commit the solution.

## Adding a skill someone else wrote

This is the part that is easy to get wrong, so it is mechanised. Do not copy files in by
hand.

1. Add a source to [`skills/vendor.manifest.json`](./skills/vendor.manifest.json) with the
   upstream repository, the author, the licence, the licence file path, the destination
   directory, and an `exclude_reasons` entry for anything you leave out.

   **Check the upstream links before you assume `skills/` is self-contained.** A source
   declares a list of `paths`, not one subdirectory, because that assumption already failed
   once: job-hunt-skills has 47 links from its skills into a sibling `guides/` directory and
   more into `templates/`. Map every subtree the skills link into, at the same relative
   distance, and the links keep resolving. Use `kind: "skill-collection"` for a directory of
   skill directories and `kind: "support"` for a subtree that is only linked into.

   Verify it afterwards. Every relative Markdown link inside the vendored tree must resolve:

   ```bash
   python3 scripts/check_links.py --path skills/<your-dest>
   ```

   That command treats an empty run as a failure. An earlier version of this section was a
   paste-in snippet containing a literal `<dest>`, so running it verbatim matched no files and
   printed "0 unresolved", which reads as success. If a link genuinely cannot be fixed here,
   because it is an upstream placeholder, exempt it by exact path with a reason in
   `docs/link-check-exemptions.json` rather than loosening the checker.

2. Run `python3 scripts/sync_vendor.py --sync`. That imports the tree, writes a
   `PROVENANCE.md` into every skill directory, copies the upstream licence verbatim to
   `LICENSE.upstream`, regenerates the collection's `ATTRIBUTION.md`, and rewrites
   `THIRD_PARTY_NOTICES.md`.
3. Run `python3 scripts/generate_index.py --write`.
4. Commit the manifest change and the generated result together.

An import without a licence, a named author and a commit-pinned source link does not get merged.
That is not a formality. This repository is public and MIT, and redistributing someone's work
without attribution is the one mistake here that cannot be quietly fixed later.

It has already happened once. Eighteen skills derived from
[mattpocock/skills](https://github.com/mattpocock/skills) say in their own text that Matt
Pocock's content is "preserved verbatim (MIT)", and no copy of the MIT notice existed anywhere in
the repository until an outside review found it. Naming an author in prose is credit. MIT also
requires the copyright and permission notice to travel with the copy. Those are different things,
and `scripts/audit_third_party.py` now enforces the second one.

## Never edit a vendored directory in place

Anything under a `dest` listed in the manifest, currently [`skills/pstack/`](./skills/pstack/)
and [`skills/job-hunt/`](./skills/job-hunt/), is a copy. The next fortnightly sync overwrites
it and your change disappears without a trace.

If a vendored skill needs changing, in order of preference:

1. Send the change upstream. Everyone benefits and the copy stays clean.
2. If this repository genuinely must diverge, remove the skill from `include` in the
   manifest, add an `exclude_reasons` entry saying why, copy it to a non-vendored path, and
   own it from then on.

## Never hand-edit generated files

These are written by scripts and overwritten without warning:

- the block between the `BEGIN GENERATED` and `END GENERATED` markers in `README.md`
- `THIRD_PARTY_NOTICES.md`
- any `PROVENANCE.md`
- any vendored collection's `ATTRIBUTION.md`
- `skills/vendor.manifest.json` fields `pinned_commit` and `pinned_at`

Each carries a generated-file banner. If you find yourself editing one, the change belongs
in the script or in the data the script reads.

## Commit messages

Conventional Commits, because the automation reads them:

```
feat(skills): add <name> to <domain>
chore(vendor): refresh vendored upstream skills
docs(readme): ...
fix(scripts): ...
```

## Writing style

[`skills/pstack/unslop/SKILL.md`](./skills/pstack/unslop/SKILL.md) is a mandatory import
and it applies to this repository's own prose, not only to what the skills generate. Before
you submit documentation, read it and apply it. No em dashes, no "delve", no bold-label
lists that restate the line, sentence-case headings, no decorative emoji.

## Record what an import cannot do

An import is rarely a clean subset. job-hunt-skills ships a Node 22 plus Typst toolchain for
DOCX and PDF export, which is an application rather than a prompt library, so it is not
vendored. That is a real reduction in capability and it is written down in the source's
`limitations` array, which the generator renders into the collection's `ATTRIBUTION.md` and
the README.

If your import drops something the upstream skills tell users to run, say so there. An
undocumented gap turns into a bug report from someone following the skill's own instructions.

## Reviewing a vendored refresh

The fortnightly sync pull request changes agent behaviour, which makes it higher risk than
its diff size suggests. Read the upstream diff, not only the local one. Confirm no new
upstream skill name collides with a local skill. Confirm `unslop` is still there.

## Reporting a problem

Open an issue using one of the forms in `.github/ISSUE_TEMPLATE/`. For anything with a
security or secret-handling dimension, read [SECURITY.md](./SECURITY.md) first and do not
open a public issue.
