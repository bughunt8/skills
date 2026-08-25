# Architecture review: bughunt8/skills

Reviewed 25 August 2026 against `e3778af`, the tip of `main` before this branch.

Scope: repository architecture, structure, governance, provenance and automation. Not a
review of whether any individual skill gives good advice. Every count below was measured,
and the command that measured it is quoted so the number can be re-derived rather than
trusted.

## Verdict

The content is strong and unusually broad. The repository around it was doing almost nothing
to protect that content, and one of the gaps was a licensing exposure rather than a matter of
taste.

At review time the repository had 459 skills, 1912 Markdown files, 651 scripts and 44 MB of
material, and no licence, no CI, no contribution rules, no ownership, no issue templates, no
security policy and no branch protection. Its own bundled `start-github-repo` skill, run
against its own root, reported 8 errors and 2 warnings. Three README skill counts were wrong.
Four different directory shapes were in use for locating a `SKILL.md`.

The sharpest finding is the first one. Everything else is hygiene by comparison.

## Findings

Severity is about consequence, not effort.

### S1. Redistributing MIT-licensed work while having no licence of its own

**Critical.** The repository had no `LICENSE` file, so by default all rights were reserved
and nobody could legally use any of it. At the same time it redistributed at least five
upstream projects, including 18 skill domains taken from
[alirezarezvani-claude-skills](https://github.com/borahanmirzaii/alirezarezvani-claude-skills)
under MIT.

MIT requires the licence and copyright notice to be included in all copies. The
`ALIREZAREZVANI_CLAUDE_SKILLS_ATTRIBUTION.md` file did that job well for its own import, and
the per-skill `ATTRIBUTION.md` files in `skills/design/` were also good. But there was no
single place a user could look to learn what they were receiving or under what terms, and no
statement of the repository's own terms at all. For a public repository this is the only
finding that gets worse the longer it sits, because downstream copies inherit the ambiguity.

Fixed: `LICENSE` (MIT) explicitly scoped to this repository's own content, plus a generated
`THIRD_PARTY_NOTICES.md` consolidating every upstream with author, licence, destination and a
commit-pinned link. Presence of both is now enforced in CI.

### S2. Imports were unrepeatable, so they rotted silently

**High.** Prior imports were performed by hand. There was no machine-readable record of where
anything came from, which meant three things: an import could not be refreshed without
redoing the manual work, a hand-edit to imported content was indistinguishable from upstream
content, and nothing detected upstream moving on.

The evidence that this had already happened is in the README itself. The
`stitch-skills` import lists no commit and no licence, and 25 skills carry a frontmatter
`name` that no longer matches their directory, most of them from imports where the directory
was renamed on the way in and the frontmatter was not.

Fixed: [`skills/vendor.manifest.json`](../skills/vendor.manifest.json) declares each upstream
with repository, author, licence, licence path, ref, a full 40-character commit pin, include
and exclude patterns, a reason for every exclusion, and a list of mandatory skills.
[`scripts/sync_vendor.py`](../scripts/sync_vendor.py) reads it, and the same function performs
the first import and every later refresh. There is no separate import path that can drift
from the refresh path.

### S3. No CI, so structural claims were unverified

**High.** Nothing checked frontmatter, so 67 metadata violations had accumulated unnoticed.
Measured with `python3 scripts/lint_skills.py --strict`:

| Rule | Count | What it means |
| --- | ---: | --- |
| SK007 duplicate `name` | 32 | 16 names used twice. Two skills answer to the same invocation and which one loads is undefined. |
| SK004 `name` differs from directory | 25 | `/name` invocation does not match the path. |
| SK005 `name` not kebab-case | 8 | All eight are `stitch::*`, using a namespace separator no loader is documented to accept. |
| SK001 no frontmatter | 1 | A test fixture under `skill-tester/assets/`. Correctly not a skill; now excluded by path. |
| SK006 description over 1024 chars | 1 | 1161 characters, which may be truncated by a routing agent. |

SK007 is the one with teeth. `research`, `slo-architect`, `kubernetes-operator`,
`chaos-engineering`, `feature-flags-architect`, `eu-ai-act-specialist`, `iso42001-specialist`
and nine others each exist twice. An agent asked to load one of them gets whichever the
loader happens to find first.

Fixed: [`scripts/lint_skills.py`](../scripts/lint_skills.py) implements SK001 to SK008 and
runs on every pull request. The 66 pre-existing errors are recorded in
`scripts/skill_lint_baseline.json` so the gate blocks new debt immediately instead of waiting
for the backlog to be cleared. Working the baseline down is the open item in S8.

### S4. Hand-maintained counts, already wrong

**Medium.** The README domain table carried hand-counted totals. Three were wrong when
checked:

| Domain | README claimed | Actually on disk |
| --- | ---: | ---: |
| engineering | 81 | 108 |
| engineering-team | 52 | 51 |
| productivity | 10 | 20 |

The `design` and `start-github-repo` directories were absent from the table entirely, and no
total was published anywhere.

The interesting part is not the error, it is that a document describing 459 skills was being
maintained by hand at all. Fixed by
[`scripts/generate_index.py`](../scripts/generate_index.py), which counts the tree and splices
a generated block into the README. Human prose per domain stays in
`docs/domain-descriptions.json`. CI runs `--check`, so a stale index fails the build.

### S5. No ownership, no contribution rules, no security policy

**Medium.** No `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`,
`CODEOWNERS`, issue templates or pull request template. For a public repository accepting
imports of other people's work, the absence of contribution rules is what allowed S1 and S2
to happen: there was no documented moment at which someone had to supply a licence.

The security policy matters more here than in a typical library, and for an unobvious reason.
Every file in this repository is an instruction to an agent that may hold credentials. A
malicious edit to a `SKILL.md` is closer to a change in a deployment script than to a change
in documentation. `SECURITY.md` now states that threat model, and the pull request template
carries an explicit prompt-injection checkbox.

Fixed: all seven files added. `CODEOWNERS` puts vendored paths, licence files and automation
under the maintainer.

### S6. Four competing directory shapes

**Medium, and the largest remaining item.** There is no single answer to "where does a
`SKILL.md` live". Measured across all 459:

| Shape | Count |
| --- | ---: |
| `<domain>/skills/<skill>/SKILL.md` | 234 |
| `<domain>/<x>/skills/<skill>/SKILL.md` | 120 |
| `<domain>/<skill>/SKILL.md` | 103 |
| `<skill>/SKILL.md` at the top of `skills/` | 2 |

Path depth below `skills/` ranges from one segment to five. Alongside that there are 85
`.claude-plugin/plugin.json` manifests scattered through the tree at inconsistent depths and
no manifest at the repository root, so there is no single entry point a consumer can read to
enumerate what this repository offers.

This is not cosmetic. Every consumer has to implement a recursive search and guess, which is
also part of why the duplicate names in S3 went unnoticed. Nothing here is broken today, so
this review does not attempt the migration. It records the decision and the cost.

Partly addressed: `scripts/lint_skills.py` now enumerates all four shapes correctly and is
the tool a migration would be verified with. The migration itself is S8 item 3.

### S7. `references.md` was an unsorted link dump

**Low.** Thirty-odd bare URLs under two headings, no annotation, no dates, no statement of
why any of them is there. Some are candidate imports, some are unrelated reading. As a
personal scratchpad it is fine. In a public repository it reads as unfinished, and it is the
kind of file that quietly becomes the actual source of truth for what to import next.

Recommended, not done in this branch, because the intent behind each link is the author's:
either annotate each with one line saying what it is for, or convert the import candidates
into vendored-import issues and delete the rest.

### S8. Automation absent entirely

**High, and the substance of this branch.** No workflows of any kind. No CI, no dependency
updates, no scheduled anything. Combined with S2 this meant every import was frozen at
whatever state it was copied in.

Fixed:

- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs the three checks on every
  push and pull request.
- [`.github/workflows/sync-vendored-skills.yml`](../.github/workflows/sync-vendored-skills.yml)
  refreshes every declared upstream on a fortnightly cadence and opens a pull request.
- [`.github/dependabot.yml`](../.github/dependabot.yml) proposes action updates weekly, which
  is the necessary counterpart to pinning actions by SHA.

## What this branch changed

| Area | Before | After |
| --- | --- | --- |
| `start-github-repo` self-audit | 8 errors, 2 warnings | 0 errors, 0 warnings |
| Repository licence | none | MIT, scoped to own content |
| Consolidated third-party notices | none | generated, CI-enforced |
| Vendored upstreams under automation | 0 | 1 source, 40 skills |
| Skill metadata validation | none | SK001-SK008 on every pull request |
| README counts | hand-maintained, 3 wrong | generated, CI-enforced |
| Community health files | 0 of 7 | 7 of 7 |
| Workflows | 0 | 3 |
| Third-party actions | none | 3, all pinned to full commit SHAs |

## Design decisions worth stating

**One code path for import and refresh.** `sync_vendor.py --sync` performs the first import
and every subsequent one. A vendored directory therefore cannot become a quietly maintained
fork, because the next scheduled run would revert it and the reversion would be visible in a
pull request diff.

**Vendored content lives in its own namespace.** `skills/pstack/` rather than distributed
into existing domains by topic. Earlier imports were merged into domains, which is friendlier
to browse and makes automated refresh impossible: there is no way to diff a collection whose
members are scattered across eighteen directories. Browsability is recovered through the
generated index. The trade is deliberate.

**Vendored findings are warnings, not errors.** `skills/pstack/poteto-mode` fails SK004 and
SK005 because upstream names it `Poteto Mode`. That cannot be corrected here without
diverging from upstream, and a check that demands an impossible fix gets disabled. It is
reported and left alone. The one rule vendored content must pass is SK008, provenance
present, because that is the part this repository owns.

**The manifest validator is offline.** `--validate-manifest` gates every pull request and
touches no network, so an unrelated change cannot go red because upstream published a commit.
Drift against upstream is checked in the scheduled job, where it is news rather than a
failure.

**Fortnightly is a weekly cron with a parity gate.** GitHub cron cannot express "every two
weeks". The workflow runs weekly and exits early on odd ISO weeks. This is visible in the
workflow rather than hidden in an external scheduler, and it means the cadence survives a
missed week without drifting.

**The automated pull request runs its own checks.** A pull request opened with
`GITHUB_TOKEN` cannot trigger another workflow, so `ci` never runs on it. Rather than ship
automation whose green tick means nothing, the sync job runs the same three checks itself and
names the result in the pull request body. An optional `SYNC_PAT` secret restores normal CI
triggering for anyone who prefers that.

**Auto-merge fails safe.** The workflow requests auto-merge. If the repository has no
required status checks configured, GitHub refuses, the workflow emits a warning, and the pull
request waits for a human. An automated merge of unreviewed content that changes agent
behaviour is worse than a queue.

## Open backlog

In the order that maximises value per unit of risk.

1. **Enable branch protection on `main`** with `ci / validate` as a required check, and turn
   on auto-merge in repository settings. Until then the fortnightly pull request cannot land
   on its own. This is a settings change, not a code change, and it is the single highest-value
   item left.
2. **Resolve the 16 duplicate skill names** (32 baseline entries). Highest actual risk in the
   repository: the wrong skill loading is silent. Most pairs are the same skill imported at
   two different depths, so most resolutions are a deletion.
3. **Choose one directory shape and migrate to it** (S6), then add a root
   `.claude-plugin/plugin.json` enumerating the collection. Do it after item 2, since
   deduplication removes work from the migration.
4. **Fix the 25 `name` and 8 kebab-case violations** in non-vendored skills, removing each
   baseline entry as it is fixed until `scripts/skill_lint_baseline.json` holds only
   `ignore_globs`.
5. **Bring the pre-manifest imports under the manifest**: the 18 alirezarezvani domains, the
   stitch skills, the design collection. Each becomes a manifest source and gets automated
   refresh and generated attribution. Largest single reduction in ongoing maintenance
   remaining.
6. **Annotate or retire `references.md`** (S7).
7. **Add a link checker** to CI. With 1912 Markdown files, cross-references between skills
   will rot and nothing currently notices.

## How to re-derive every number here

```bash
git -C . rev-parse --short HEAD
python3 scripts/lint_skills.py --strict --output json      # all metadata findings
python3 scripts/generate_index.py --check                  # index freshness and counts
python3 scripts/sync_vendor.py --validate-manifest         # provenance completeness
python3 scripts/sync_vendor.py --check                     # drift against upstream
python3 skills/start-github-repo/scripts/validate_repo.py --root . --visibility public
git ls-files '*.md' | wc -l
find skills -name SKILL.md | wc -l
```

The audit was performed with this repository's own
[`start-github-repo`](../skills/start-github-repo/SKILL.md) skill in `audit` mode, which is
the most useful thing that can be said about that skill: pointed at its own repository, it
found eight real problems.
