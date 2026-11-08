# Review evidence: skill-creator import

Date: 2026-11-08. Branch: `staging`. Base before the import: `f61075b`.

## Scope

The repository did not contain the Anthropic `skill-creator`. This import adds it as a vendored skill.

| Item | Value |
| --- | --- |
| Upstream | <https://github.com/anthropics/claude-plugins-official> |
| Upstream path | `plugins/skill-creator/skills/skill-creator/` |
| Pin | `0412be76f50ab4f4f8abff3753efa9269fbbca5b` |
| Licence | Apache-2.0 |
| Upstream files | 18, about 272 KB, no symlinks |
| Destination | `skills/engineering/skill-creator/` |
| Manifest id | `skill-creator` |
| Mapping | `kind: "skill"`, `from: "plugins/skill-creator/skills/skill-creator"`, `to: ""` |

The whole skill directory is vendored, including `scripts/`, `agents/`, `references/`, `assets/` and `eval-viewer/`, so its internal links keep resolving. The nested Apache-2.0 `LICENSE.txt` and the repository-root `LICENSE` are both preserved.

## Generated metadata

- `skills/engineering/skill-creator/ATTRIBUTION.md`
- `skills/engineering/skill-creator/LICENSE.upstream`
- `skills/engineering/skill-creator/PROVENANCE.md`
- `skills/engineering/skill-creator/.vendor-owned.json`
- `THIRD_PARTY_NOTICES.md`
- the `README.md` generated index

## Counts

| Value | Before | After |
| --- | ---: | ---: |
| Repository skills | 740 | 741 |
| Directories | 28 | 28 |
| Linted | 739 | 740 |
| Site skills | 758 | 759 |
| Site categories | 30 | 30 |
| Site communities | 91 | 92 |
| Solutions | 61 | 61 |

`site/tests/library-size.mjs` now records 759 skills, 30 categories and 61 solutions. `AGENTS.md` records 741 skill files, 28 directories and 740 linted. The `engineering` harness manifest was regenerated because the new skill belongs to that domain.

## Local validation

| Check | Result |
| --- | --- |
| `lint_skills.py --self-test` | 9 cases, 0 failures |
| `lint_skills.py` | 740 linted, 0 errors, 2 vendored warnings, 33 baseline |
| `generate_index.py --check` | up to date |
| `sync_vendor.py --validate-manifest` | 41 sources, 0 problems |
| `sync_vendor.py --check --source skill-creator` | no drift |
| `audit_third_party.py` | 0 unaccounted |
| `check_links.py` | 0 unresolved |
| `check_links.py --scope vendored` | 0 unresolved |
| `check_solutions.py` | 3 solutions, every step resolves |
| `check_skill_dependencies.py --include-legacy` | OK |
| `unittest discover -s scripts` | 190 tests, OK |
| agent-harness tests | 35 tests, OK |
| harness manifest `--check` | 18 manifests, no drift |
| `site/build.py --check` | up to date, 759 skills, 30 categories |
| `site/tests/test_deploy_workflows.py` | 38 tests, OK |
| `site/tests/test_network.py` | all graph assertions hold |
| `site/tests/test_compose.py` | all composition checks passed |
| `npm run lint:html` | clean |
| `npm run lint:secrets` | clean after removing generated `site/tests/__pycache__` |
| `npx playwright test --workers=1 --retries=1` | 191 passed, 1 skipped, 0 failed |

`--validate-manifest` checks declarations and records, not licence rights.

## Use in this repository

The `repo-skill-updater` draft at `.omo/drafts/repo-skill-updater/SKILL.md` points to this skill for the draft and review loop. The full eval loop in the vendored skill calls the Anthropic `claude` CLI and expects a browser; this repository does not install that toolchain, so the draft scopes it to drafting and manual review.

## Limitations

- The skill is designed for Claude Code and Claude.ai. The eval loop and description optimizer need the `claude` CLI; the viewer needs a browser.
- The `present_files` packaging step applies only to a host that provides that tool.
- The vendored scripts are content. This repository does not install their Python dependencies or run them in CI.
- The upstream root `LICENSE` is Apache-2.0. The skill directory also carries its own Apache-2.0 `LICENSE.txt`.

## Promotion boundary

This import is committed and pushed to `staging` only. It is not promoted to `main`. Promotion belongs to the maintainer.
