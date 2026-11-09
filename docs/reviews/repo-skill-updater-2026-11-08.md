# Review evidence: repo-skill-updater

Date: 2026-11-08. Branch: `staging`. Base before the change: `02a69ab`.

## What was added

`skills/engineering/repo-skill-updater/SKILL.md` is a locally authored decision layer for adding a new skill or skill repository to this library.

It does not replace the existing procedures and does not add a second import path. It routes:

- local skills to `skills/engineering/write-a-skill/skills/write-a-skill/SKILL.md` and the `skills/<domain>/<skill-name>/SKILL.md` layout;
- external repositories to `skills/engineering/vendor-import/SKILL.md` and the manifest plus `scripts/sync_vendor.py` path;
- drafting and review to `skills/engineering/skill-creator/SKILL.md`.

It records the repository-specific additions: generated versus hand-maintained files, the site and README count sources, the `kind: "skill"` mapping, the support-tree mapping, completeness with a real byte copy, the harness `--out-dir` command, the verification block, evidence, failure handling, and the no-promotion boundary.

## Reviews

- Standards and Spec reviews ran in several rounds. Their findings were applied: count-source split, generated versus hand-maintained files, runnable name checking through SK007, the single-skill mapping, byte-copy completeness, honest skill-creator scope, and the commit/push boundary.
- Oracle verdict: **approve with conditions**. All conditions were applied:
  1. New-domain guidance treats `site/domains.json` as the grouping source and `LABELS` as an optional display choice.
  2. External pin verification records the reviewed SHA in the plan and compares the fetched commit with it.
  3. Completeness projects the upstream inventory through the same `file_include` selection.
  4. Browser comparison names the pre-change commit and uses matching `--workers=1 --retries=1` settings.
  5. The external path commits before Oracle and uses a follow-up commit for must-fixes.

`quick_validate.py` reports `Skill is valid!`. The frontmatter is a 503-character description and the file is 188 lines.

## Counts

| Value | Before | After |
| --- | ---: | ---: |
| Repository skills | 741 | 742 |
| Directories | 28 | 28 |
| Linted | 740 | 741 |
| Site skills | 759 | 760 |
| Site categories | 30 | 30 |
| Site communities | 92 | 92 |
| Solutions | 61 | 61 |

`site/tests/library-size.mjs` now records 760 skills, 30 categories and 61 solutions. `AGENTS.md` records 742 skill files, 28 directories and 741 linted. The `engineering` harness manifest was regenerated.

## Local validation

| Check | Result |
| --- | --- |
| `lint_skills.py --self-test` | 9 cases, 0 failures |
| `lint_skills.py` | 741 linted, 0 errors, 2 vendored warnings, 33 baseline |
| `generate_index.py --check` | up to date |
| `sync_vendor.py --validate-manifest` | 41 sources, 0 problems |
| `audit_third_party.py` | 0 unaccounted |
| `check_links.py` | 0 unresolved |
| `check_links.py --scope vendored` | 0 unresolved |
| `check_solutions.py` | 3 solutions, every step resolves |
| `check_skill_dependencies.py --include-legacy` | OK |
| `unittest discover -s scripts` | 190 tests, OK |
| agent-harness tests | 35 tests, OK |
| harness manifest `--check` | 18 manifests, no drift |
| `site/build.py --check` | up to date, 760 skills, 30 categories |
| `site/tests/test_deploy_workflows.py` | 38 tests, OK |
| `site/tests/test_network.py` | all graph assertions hold |
| `site/tests/test_compose.py` | all composition checks passed |
| `npm run lint:html` | clean |
| `npm run lint:secrets` | clean |
| `npx playwright test --workers=1 --retries=1` | 191 passed, 1 skipped, 0 failed |

## Limitations

- This is a procedure, not an executor. It does not run the import or authoring for the user.
- The `skill-creator` eval loop needs the Anthropic `claude` CLI and a browser. The draft scopes it to drafting and manual review.
- The external import remains the responsibility of `vendor-import` and `scripts/sync_vendor.py`. This skill adds the repository-specific checklist around them.
- The skill description and structure are local. It does not change the library layout.

## Promotion boundary

This skill is committed and pushed to `staging` only. It is not promoted to `main`. Promotion belongs to the maintainer.
