# Architecture review: bughunt8/skills

Reviewed 25 August 2026. Base is `e3778af`, the tip of `main` before this branch.

Scope: repository architecture, structure, governance, provenance and automation. Not a review
of whether any individual skill gives good advice.

## How to read the numbers

Three different things can be called "a skill count", so each is named explicitly:

| Metric | Meaning |
| --- | --- |
| physical | files named `SKILL.md` anywhere under `skills/` |
| linted | physical, minus paths in `ignore_globs` (currently one test fixture) |
| imported | skill directories a single vendored source contributed |

Every figure is bound to a commit, and the command that produced it is in
[How to re-derive every number here](#how-to-re-derive-every-number-here). An earlier draft of
this document mixed base, mid-branch and final measurements in one table and called the
repository 459 skills, which was true at neither end. That is corrected below.

| | base `e3778af` | this branch |
| --- | ---: | ---: |
| physical skills | 419 | 470 |
| linted skills | 419 | 469 |
| Markdown files | 1,912 | 2,092 |
| top-level directories in `skills/` | 20 | 22 |
| workflows | 0 | 2 |
| repository size excluding `.git` | 42 MB | 46 MB |

## Verdict

The content is strong and unusually broad. The repository around it was doing almost nothing
to protect that content, and one of the gaps was a licensing exposure rather than a matter of
taste.

At base the repository had 419 skills, 1,912 Markdown files, 651 scripts and 42 MB of material,
and no licence, no CI, no contribution rules, no ownership, no issue templates, no security
policy and no branch protection. Its own bundled `start-github-repo` skill, run against its own
root, reported 8 errors and 2 warnings. Three README skill counts were wrong. Four different
directory shapes were in use for locating a `SKILL.md`.

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

**High.** Nothing checked frontmatter, so metadata violations accumulated unnoticed. Measured
with `python3 scripts/lint_skills.py --strict`, which reports 68 errors plus 2 warnings in
vendored trees:

| Rule | Count | What it means |
| --- | ---: | --- |
| SK007 duplicate `name` | 32 | 16 names used twice. Two skills answer to the same invocation and which one loads is undefined. |
| SK004 `name` differs from directory | 25 | `/name` invocation does not match the path. |
| SK005 `name` not kebab-case | 8 | All eight are `stitch::*`, using a namespace separator no loader is documented to accept. |
| SK009 unreadable frontmatter | 2 | `markdown-html/skills/design-system` and `markdown-html/skills/md-slides` contain YAML no loader can parse: "mapping values are not allowed here". |
| SK006 description over 1024 chars | 1 | 1,161 characters, which a routing agent may truncate. |

A separate SK001 finding, a `SKILL.md` with no frontmatter under
`skills/engineering/skills/skill-tester/assets/sample-skill/`, is a deliberate test fixture. It
is excluded by path in `ignore_globs` rather than counted or baselined.

The two SK009 findings were invisible until this branch replaced a line-matching frontmatter
reader with a real YAML parser. That substitution is described in S10.

SK007 is the one with teeth. `research`, `slo-architect`, `kubernetes-operator`,
`chaos-engineering`, `feature-flags-architect`, `eu-ai-act-specialist`, `iso42001-specialist`
and nine others each exist twice. An agent asked to load one of them gets whichever the
loader happens to find first.

Fixed: [`scripts/lint_skills.py`](../scripts/lint_skills.py) implements SK001 to SK009 and runs
on every pull request. The 68 pre-existing errors are recorded in
`scripts/skill_lint_baseline.json` so the gate blocks new debt immediately instead of waiting for
the backlog to be cleared. Each baseline key is rule, path and a fingerprint of the message, so
replacing a baselined skill with a different violation at the same path still fails. Working the
baseline down is backlog item 2.

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

The interesting part is not the error, it is that a document describing hundreds of skills was
being maintained by hand at all. Fixed by
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
`SKILL.md` live". Measured across all 419 at base:

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

- [`.github/workflows/a0-skills-checks.yml`](../.github/workflows/a0-skills-checks.yml) runs the three checks on every
  push and pull request.
- [`.github/workflows/sync-vendored-skills.yml`](../.github/workflows/sync-vendored-skills.yml)
  refreshes every declared upstream on a fortnightly cadence and opens a pull request.
- [`.github/dependabot.yml`](../.github/dependabot.yml) proposes action updates weekly, which
  is the necessary counterpart to pinning actions by SHA.

### S9. A coverage gap the domain list hid

**Medium, and a content finding rather than a structural one.** The repository had 68
`c-level-advisor` skills, 51 `engineering-team` skills and 48 `marketing-skill` skills, and no
coherent workflow for a person applying for work. Adjacent pieces existed:
`productivity/andreessen` for career bets, `research/dossier` for person research,
`marketing-skill/social-content` for LinkedIn presence, and CHRO and interview-system skills
from the employer's side. None of them writes a resume, tailors it to a posting, or prepares a
candidate. For a library whose README describes its audience as "Agentic Entrepreneurs and OPC",
that is an odd hole: the same person who needs a pricing strategist skill needs a resume that
survives a screen.

The gap was invisible because the domain table listed directory names, not capabilities. A
reader scanning 18 domain names has no way to notice that none of them covers the job search.

Addressed by vendoring [Remotivated/job-hunt-skills](https://github.com/Remotivated/job-hunt-skills)
(MIT) into `skills/job-hunt/`: 11 skills covering source resume, honest audit, tailoring to a
posting, cover letters, company research, LinkedIn, proof-of-value assets, interview coaching,
stage tracking, and a final claim-check pass. It is the only import here whose value is directly
measurable, since the outcome is an interview or not. Routing against the adjacent skills above
is worth documenting; it is not done yet.

Two limitations are recorded rather than glossed over: the skills need a `my-documents/`
workspace in the user's own directory, and the DOCX and PDF export toolchain is not vendored.
Both are in the collection's attribution, the README and SUPPORT.md.

### S10. Checks that could not fail, and the review that found them

**High, and found by someone else.** After the work above was finished and opened as
[pull request #18](https://github.com/bughunt8/skills/pull/18), an independent adversarial review
was run by a different model with instructions to assume the author was overconfident. It
returned 25 findings, three of them blockers. That was the correct outcome and the findings were
real. The important ones, and what they say about the design:

**The import engine followed symlinks.** `shutil.copytree` dereferences by default. A moving
upstream could add `secret -> /home/runner/work/_temp/...` and the scheduled job would commit the
contents of a runner-local path into a public pull request. Demonstrated with a working
reproduction. Every symlink in an upstream tree is now a hard error.

**Manifest paths were not validated.** `dest: ../escaped` wrote and deleted outside the
repository root. The manifest is data that this script writes and deletes from, so it is now
treated as untrusted: absolute paths, `..`, and drive or UNC forms are rejected, and every
resolved target must prove it stays under its designated root. The first version of that guard
was itself wrong, stripping the leading slash before testing for absoluteness, so `/etc` passed.
Negative tests now cover both.

**Ownership was inferred, not recorded.** A `skills -> ""` collection decided what it owned by
listing the children of its destination, so it deleted a sibling `guides/` support tree, and
removing a `paths` entry orphaned the tree it used to manage. Each destination now carries a
`.vendor-owned.json` written by the sync, overlapping destinations are rejected outright, and
orphans are deleted rather than abandoned.

**The linter was not a YAML parser and said so proudly.** `description: |` parsed as the
one-character string `|`, so the 1024-character limit was bypassable by any block scalar, and
`description: [unterminated` parsed as valid. It now uses PyYAML when available and a strict
subset parser that raises SK009 rather than guessing when it is not. The substitution immediately
found two `SKILL.md` files whose frontmatter no YAML loader accepts.

**The baseline could launder new debt.** Suppression was keyed on rule and path, so replacing a
baselined skill with a different violation at the same path was silently accepted. Keys now
include a fingerprint of the message.

**Consolidated attribution was hand-written and incomplete.** It listed five upstream projects.
The tree contains 144 licence and attribution markers covering 18 distinct pre-manifest projects.
Two specific errors mattered: `stitch-skills` is Apache-2.0, recorded as "see per-skill LICENSE",
and `mattpocock/skills` was redistributed by 18 skills whose own text says Matt Pocock's content
is "preserved verbatim (MIT)" with no copy of the MIT notice anywhere in the repository. MIT
requires that notice to travel with copies. That was the most serious defect in the whole review
and is exactly the class of problem S1 was supposed to close. Fixed by
[`docs/third-party-inventory.json`](third-party-inventory.json), a generated tier 2 notices
table, and [`scripts/audit_third_party.py`](../scripts/audit_third_party.py), which fails CI when
a licence marker appears with nothing covering it.

**"Fortnightly" was not fortnightly.** The even-ISO-week gate produces 21-day gaps in ISO years
with 53 weeks. `scripts/sync_due.py --self-test` reproduces the two that occur between 2026 and
2036. The cadence is now measured in elapsed days from the manifest's own `pinned_at`, which
cannot drift and self-heals after a missed run.

**A verification snippet could not fail.** The link-check recipe pasted into `CONTRIBUTING.md`
contained a literal `<dest>` placeholder. Run verbatim it matched zero files and printed
"0 unresolved", which reads as success. It is now
[`scripts/check_links.py`](../scripts/check_links.py), which reports what it examined and treats
an empty run as a failure.

The lesson generalises past any single bug. Six of these findings are the same mistake: a check
that reports success in a situation it was never able to evaluate. A linter that cannot parse
YAML, a baseline keyed too loosely, a notices file assembled by hand, a snippet with a
placeholder in it, a schedule that looks periodic, an ownership model that guesses. Each produced
confidence rather than information, and confidence is worse than an empty result, because nobody
goes back to check it.

Two findings were deliberately not fixed and are recorded instead. The review noted that
"nothing that helps a person get hired" overstated the gap in S9, since adjacent skills existed
in `productivity/andreessen`, `research/dossier` and the CHRO and interview-system tooling. That
is fair, and S9 now says the repository lacked a coherent job-seeker workflow rather than
nothing at all. The review also noted that `CODEOWNERS` currently enforces nothing, because the
repository has no branch protection. That is true, it is backlog item 1, and it needs a settings
change no pull request can make.

The full report is preserved at
[`docs/adversarial-review-2026-08-25.md`](adversarial-review-2026-08-25.md), including the
findings that were disputed.

## What this branch changed

| Area | Before | After |
| --- | --- | --- |
| `start-github-repo` self-audit | 8 errors, 2 warnings | 0 errors, 0 warnings |
| Repository licence | none | MIT, scoped to own content |
| Consolidated third-party notices | none | generated, CI-enforced |
| Vendored upstreams under automation | 0 | 2 sources, 51 skills |
| Skills covering the job search | 0 | 11 |
| Skill metadata validation | none | SK001-SK008 on every pull request |
| README counts | hand-maintained, 3 wrong | generated, CI-enforced |
| Community health files | 0 of 7 | 7 of 7 |
| Workflows | 0 | 3 |
| Third-party actions | none | 3, all pinned to full commit SHAs |
| Physical skills | 419 | 470 |
| Linted skills | 419 | 469 |
| Unresolved relative links | not checked | 0 of 499, 1 exempted with a reason |
| Licence markers reconciled against an inventory | 0 of 86 | 144 of 144 |
| Checked-in verification scripts | 0 | 6 |

## Design decisions worth stating

**One code path for import and refresh.** `sync_vendor.py --sync` performs the first import
and every subsequent one. A vendored directory therefore cannot become a quietly maintained
fork, because the next scheduled run would revert it and the reversion would be visible in a
pull request diff.

**A source maps a list of subtrees, not one directory.** The first version of the manifest
assumed an upstream keeps everything under `skills/`, because pstack does. The second import
broke that assumption immediately: job-hunt-skills carries 47 links from its skills into a
sibling `guides/` directory and more into `templates/`. Copying only `skills/` would have
produced a tree where every one of those links pointed at nothing, and nothing in the original
design would have noticed.

Rather than special-case it, the schema was generalised. A source now declares `paths`, a list
of upstream subtrees mapped into the vendored root at the same relative distance, so the links
resolve unchanged. Two kinds: `skill-collection` for a directory of skill directories, tracked
per child with individual provenance, and `support` for a subtree that is only linked into,
copied whole with one provenance file. All 499 relative links across the vendored trees and the
governance docs now resolve, checked by [`scripts/check_links.py`](../scripts/check_links.py) in
CI rather than by a snippet someone runs once.

The lesson is worth stating plainly, because it will recur: a skills collection is not
necessarily a self-contained directory. It is a directory plus everything it links into. The
manifest has to be able to describe the second part.

**An import records what it cannot do.** job-hunt-skills ships a Node 22 plus Typst toolchain
for ATS-safe DOCX and PDF export. It is not vendored: it is an application rather than a prompt
library, its checked-in dependency bundle is 1.9 MB, and this repository has no Node CI to keep
it honest. That is a real reduction in capability, so it is recorded in the source's
`limitations` array and rendered into the collection's attribution, the README and SUPPORT.md.
A user following the skill's own instructions will otherwise file it as a bug.

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

1. **Enable branch protection on `main`** requiring the `ci / validate skills and provenance`
   check, and turn on auto-merge in repository settings. Until both are set, three things that
   look enforced are not: the scheduled pull request cannot land on its own, `CODEOWNERS` is
   advisory only, and a human can merge past a red build. A settings change, not a code change,
   and the single highest-value item left.
2. **Resolve the 16 duplicate skill names** (32 of the 68 baseline entries), then the 2 SK009
   files with unparseable frontmatter, which are outright broken rather than merely untidy. Highest actual risk in the
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
   remaining. The `paths` schema now handles collections that are not self-contained, so this
   is unblocked.
6. **Annotate or retire `references.md`** (S7).
7. **Add a link checker** to CI. With over 1900 Markdown files, cross-references between
   skills will rot and nothing currently notices. Vendored trees are the urgent case: link
   integrity there is now checked by `scripts/check_links.py` in CI and in the sync job. Done.
8. **Decide whether to vendor the job-hunt export toolchain.** It needs Node 22, Typst and a
   Node CI job. Worth it only if people ask for DOCX and PDF output from this repository
   rather than from upstream.

## How to re-derive every number here

```bash
git -C . rev-parse --short HEAD
python3 scripts/lint_skills.py --strict --output json      # all metadata findings
python3 scripts/generate_index.py --check                  # index freshness and counts
python3 scripts/sync_vendor.py --validate-manifest         # provenance completeness
python3 scripts/sync_vendor.py --check                     # drift against upstream

# every relative link inside the vendored trees resolves
python3 - <<'EOF'
import glob, os, re
bad = []
for f in glob.glob("skills/pstack/**/*.md", recursive=True) + glob.glob("skills/job-hunt/**/*.md", recursive=True):
    base = os.path.dirname(f)
    for m in re.finditer(r'\]\((?!https?:|mailto:|#)([^)#\s]+)', open(f).read()):
        if not os.path.exists(os.path.normpath(os.path.join(base, m.group(1)))):
            bad.append((f, m.group(1)))
print(f"{len(bad)} unresolved")
EOF
python3 skills/start-github-repo/scripts/validate_repo.py --root . --visibility public
git ls-files '*.md' | wc -l
find skills -name SKILL.md | wc -l
```

The audit was performed with this repository's own
[`start-github-repo`](../skills/start-github-repo/SKILL.md) skill in `audit` mode, which is
the most useful thing that can be said about that skill: pointed at its own repository, it
found eight real problems.
