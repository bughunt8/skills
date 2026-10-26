---
name: vendor-import
description: Import an external repository of agent skills into this library through its vendor pipeline. Use when the user gives a repository URL and asks to analyse it, integrate it, bring it into this library, or update its references, templates, attribution and scripts. Covers upstream inspection, licence and commit pinning, name collisions, manifest mapping, the sync and index generators, site data, evidence collection and the Oracle review. Not for editing an already vendored tree, refreshing an existing source (run scripts/sync_vendor.py), or writing a local skill (use write-a-skill).
---

# Import an external skills repository

This is the procedure for taking someone else's skills repository and making it part of
this library. It exists because the import has more failure modes than it looks: name
collisions change routing, a wrong commit pin stops the scheduled refresh, a nested
layout breaks provenance, and the site has its own generated counts.

Read `AGENTS.md` and `CONTRIBUTING.md` first. Then follow the phases in order. Do not
start editing the tree until the plan has survived Momus and Metis.

## Inputs

- A repository URL. It is often wrong: wrong owner, singular or plural, or a renamed
  repository. Resolve it with `gh api repos/<owner>/<name>` and `gh repo list <owner>`
  before doing anything else.
- The current branch. Imports land on `staging`, never `main`.

## Phase 1: analyse the upstream

Clone to `/tmp` and record facts. Do not guess any of them.

```bash
gh api repos/<owner>/<name> --jq '{default_branch,license:.license.spdx_id,description,pushed_at}'
git clone https://github.com/<owner>/<name>.git /tmp/<id>
cd /tmp/<id> && git rev-parse HEAD && git log -1 --format='%ci %s'
head -4 LICENSE
```

Collect and write down:

| Fact | Command |
| --- | --- |
| Skill count and depth | `find skills -name SKILL.md \| sed 's\|/SKILL.md\|\|' \| awk -F/ '{print NF}' \| sort \| uniq -c` |
| Frontmatter compliance | PyYAML parse, then check name equals directory, kebab case, description under 1024 |
| Name collisions | intersect upstream names with every local `name:` under `skills/` |
| Links leaving `skills/` | resolve every relative Markdown link, count targets outside `skills/` |
| Symlinks | `find . -type l` |
| Files and size | `find skills -type f \| wc -l`, sum of byte sizes |
| Generated-name collisions | basenames `PROVENANCE.md`, `ATTRIBUTION.md`, `LICENSE.upstream`, `.vendor-owned.json` |
| Prose references | `grep -rhoE '(docs\|evals\|tests)/[A-Za-z0-9._/-]+' skills` |

The licence needs the copyright line and the package author, not just the SPDX id. If
they disagree, record both. `--validate-manifest` cannot prove the upstream had the right
to license its files, and do not claim it does.

## Phase 2: choose the mapping

Two shapes cover almost every upstream:

- **Flat**, `skills/<skill>/SKILL.md`: one path entry, `from: "skills"`, `to: ""`,
  `kind: "skill-collection"`, `include: ["*"]`.
- **Nested**, `skills/<category>/<skill>/SKILL.md`: one path entry per category,
  `from: "skills/<category>"`, `to: "<category>"`. A single entry would treat the
  category directories as the skills, write one `PROVENANCE.md` per category, and leave
  every nested skill without one. `lint_skills.py` SK008 then fails all of them as
  errors.

Map a support subtree only when a Markdown link from a skill points into it, and map it
at the same relative distance. Verify with `python3 scripts/check_links.py --path
skills/<dest>` after the sync. Prose-only references stay out and go into `limitations`.

## Phase 3: handle name collisions

A duplicate `name` makes routing ambiguous, and `lint_skills.py` SK007 treats it as an
error. The local skill is canonical. Exclude the upstream one and record why:

```json
{
  "exclude": ["copywriting"],
  "exclude_reasons": {
    "copywriting": "Frontmatter name collides with the local skills/marketing-skill/skills/copywriting. The local skill is canonical for this repository."
  }
}
```

Recompute the collision set against the current tree every time. Print the pairs with
their categories and local paths, and treat that printed list as the reviewed input.

## Phase 4: write the plan

Save it to `.omo/plans/<id>-integration.md`. It must contain the evidence table, the
decision for every mapping, the full mapping table when there is more than one entry,
the exact manifest entry, the ordered steps, the completeness check, acceptance criteria
and risks.

Then get it reviewed:

- Momus: `task(subagent_type="momus", prompt=".omo/plans/<id>-integration.md")`, the path
  as the sole prompt.
- Metis: point it at the same file and ask for blockers, ambiguities and AI failure
  points. Fix what it finds and send it back until it returns UNBLOCKED. It will check
  that the collision set is reproducible, that every mapping is enumerated, and that the
  completeness check fails when it should.

## Phase 5: implement

Add the manifest source:

```json
{
  "id": "<id>",
  "name": "<id>",
  "repo": "https://github.com/<owner>/<name>",
  "homepage": "https://github.com/<owner>/<name>",
  "author": "<author>",
  "license": "MIT",
  "license_path": "LICENSE",
  "ref": "main",
  "pinned_commit": "<full 40-char sha>",
  "dest": "skills/<id>",
  "paths": [ ... ],
  "mandatory": [],
  "limitations": [ ... ],
  "pinned_at": "<YYYY-MM-DD>"
}
```

Do not add `expected_commit`. The importer preflights every source, and a moved
`expected_commit` aborts the whole sync, which stops the fortnightly refresh for every
source rather than just this one. `pinned_commit`, `ref` and `pinned_at` already record
what was reviewed.

Then run, in order:

```bash
python3 scripts/sync_vendor.py --sync --source <id>
python3 scripts/generate_index.py --write
cd site && python3 build.py --write
```

Before the site build, add the new category to `site/domains.json` under the domain it
belongs to, or the build fails with `KeyError: '<id>'`. Add a display label to `LABELS`
in `site/build.py`; without one the site shows the raw directory name.

After the build, read the new totals from `site/data.js` and update the exact constants
in `site/tests/library-size.mjs`. Refresh the counts in `AGENTS.md` the same way.

## Phase 6: prove the import

Compare the pinned clone with the destination, ignoring only files the importer writes.
The check must print counts and exit nonzero on failure.

```bash
python3 - <<'PY'
import hashlib, pathlib
UP = pathlib.Path("/tmp/<id>/skills")
DST = pathlib.Path("skills/<id>")
GENERATED_ROOT = {"ATTRIBUTION.md", "LICENSE.upstream", ".vendor-owned.json"}

def is_generated(rel):
    parts = rel.split("/")
    if parts[-1] == "PROVENANCE.md" and len(parts) == 2:
        return True
    return rel in GENERATED_ROOT

def inventory(root, drop):
    out = {}
    for p in root.rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(root).as_posix()
        if drop and is_generated(rel):
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out

shadowed = [p.relative_to(UP).as_posix() for p in UP.rglob("*")
            if p.is_file() and is_generated(p.relative_to(UP).as_posix())]
a, b = inventory(UP, False), inventory(DST, True)
missing = sorted(set(a) - set(b)); extra = sorted(set(b) - set(a))
diff = sorted(k for k in set(a) & set(b) if a[k] != b[k])
print(f"shadowed {len(shadowed)} expected {len(a)} imported {len(b)} "
      f"missing {len(missing)} extra {len(extra)} mismatch {len(diff)}")
ok = not (shadowed or missing or extra or diff)
print("COMPLETE" if ok else "INCOMPLETE")
raise SystemExit(0 if ok else 1)
PY
```

Adjust the `PROVENANCE.md` depth for a nested layout (`len(parts) == 3`). Run the
negative case once: hardlink-copy the destination inside the repository filesystem,
delete one imported non-generated file, point `DST` at the copy, and require
`missing 1` and exit 1. A copy across filesystems fails with `Invalid cross-device
link` and can fill the disk, so keep it under the repository.

Then run every gate:

```bash
python3 scripts/lint_skills.py --self-test
python3 scripts/lint_skills.py
python3 scripts/generate_index.py --check
python3 scripts/sync_vendor.py --validate-manifest
python3 scripts/audit_third_party.py
python3 scripts/check_links.py
python3 scripts/check_solutions.py
python3 scripts/check_skill_dependencies.py --include-legacy
python3 -m unittest discover -s scripts -p 'test_*.py'
HARNESS_SOURCE_ROOT="$PWD" python3 -m unittest discover -s skills/engineering/agent-harness/tests -p 'test_*.py'
python3 skills/engineering/agent-harness/skills/agent-harness/scripts/harness_manifest_builder.py --check --repo-root .
cd site && python3 build.py --check
cd site && npm ci && npm run lint:html && npm run lint:secrets && npm test
```

## Phase 7: browser evidence

CI runs the browser suite with `--workers=1 --retries=1`, so compare in that mode, not
under parallel load. Create a worktree at the branch tip, symlink `site/node_modules`,
and run the same command on both. Report pass, fail, timeout and skip counts, plus the
failing test names. Counts alone are not evidence: the same totals can hide different
failures. Rerun any test that fails on one side and not the other in isolation before
calling it a regression.

If the branch tip already fails tests, an import is no worse only when its failure set
is a subset of the tip's. Anything new is a blocker, not noise.

## Phase 8: commit, then Oracle

Commit on `staging` with `feat(vendor): import <id>`. Do not push unless the user asks.
A push runs CI and can deploy.

For the final review, write the brief to `.omo/plans/oracle-<id>-verdict.md` and give
Oracle only that path. An inline brief of a full import hits the prompt limit and fails.
The brief must state what changed, the evidence, the known limitations, the browser
comparison and the open items, and ask for a verdict plus conditions.

Apply the must-fixes before reporting. If Oracle finds that a pin will block the
scheduled refresh, that the browser evidence is weaker than claimed, or that a
limitation is missing, fix it and amend the local commit. Then report outcome first,
with the gate results, the browser comparison and what is still open.

## Traps

- Never copy files in by hand. The manifest plus `--sync` is the only path that produces
  correct attribution.
- Never edit a vendored file, a `PROVENANCE.md`, an `ATTRIBUTION.md` or
  `THIRD_PARTY_NOTICES.md`. Change the manifest or the scripts and regenerate.
- `expected_commit` blocks the all-source refresh.
- A nested layout needs one mapping per category, or SK008 fails every nested skill.
- A duplicate `name` is a routing bug, not a style issue.
- The site needs a domain entry, a display label and updated test constants.
- `site/tests/library-size.mjs` holds exact counts on purpose. Update them from
  `data.js`, never by guessing.
- Do not claim a licence is verified. The manifest check proves declarations, not rights.
- Do not push, merge or deploy on your own.
