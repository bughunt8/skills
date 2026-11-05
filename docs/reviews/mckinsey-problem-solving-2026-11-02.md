# Review evidence: mckinsey-problem-solving import

Date: 2026-11-05. Import committed 2026-11-02.
Branch: `staging`. Base before the staging work: `9051b3f`. Validated code commit: `d756ae3`. The review record, the local-addition audit check and the predicate normalization are the follow-up commit.

## Scope

This document covers the `succtorlin/mckinsey-problem-solving-skill` import and the staging validation that followed it.

- `e716461` imports the skill.
- `c731aae` and `73ef584` record and correct the graph separation fix.
- `c6249a7` records the upstream description gap as a manifest limitation.
- `2ccd2e0` imports `Abdullah4AI/mckinsey-research`. Its own evidence is in [`abdullah-mckinsey-research-2026-11-02.md`](./abdullah-mckinsey-research-2026-11-02.md).
- `276a902` clarifies that third-party notices record upstream declarations, not verification.
- `368484b` pins the Playwright workflows to `ubuntu-24.04`.

The authored `skills/research-ops/skills/mckinsey-research` skill is a local
addition inside the legacy Alireza Rezvani import domain. The exception is
recorded in `skills/ALIREZAREZVANI_CLAUDE_SKILLS_ATTRIBUTION.md` and
`docs/third-party-inventory.json` under `local_additions`.

No promotion was performed. Only `staging` was pushed, for maintainer review.

## Upstream

- Repository: `https://github.com/succtorlin/mckinsey-problem-solving-skill`.
- Default branch: `main`.
- Reviewed pin: `c87cac1000720bb135d87888e9d4db50bd6f0fa3`.
- Layout: one skill at `skills/mckinsey-problem-solving/` plus three reference files.
- Size: 8 files, 40,051 bytes, no symlinks, no Markdown link leaving the skill directory.
- Licence: MIT. Both licence files say only `Copyright (c) 2026` with no named holder. The repository owner and commit author is Tony Zhang (`succtorlin`); the initial skill commit is authored by Manus.
- No `templates/` or `scripts/` directory exists upstream.
- Root `README.md` and `SECURITY.md` are not vendored; no skill link points at them.

## Import path

- One source in `skills/vendor.manifest.json`: flat `skill-collection` mapping, `from: "skills"`, `to: ""`, `dest: "skills/mckinsey-problem-solving"`.
- Imported only through `python3 scripts/sync_vendor.py --sync --source mckinsey-problem-solving`. No file was copied by hand.
- The vendored tree contains `SKILL.md`, `LICENSE.txt`, the three references and the generated `PROVENANCE.md`.
- Generated metadata: `ATTRIBUTION.md`, `LICENSE.upstream`, `.vendor-owned.json`, `THIRD_PARTY_NOTICES.md`, the README index row and the site attribution.
- Completeness: 5 expected, 5 imported, 0 missing, 0 extra, 0 mismatch. The negative cases for missing, extra and mismatch each report 1 and exit 1. The destination digest is unchanged before and after. The script and output are retained at `.omo/evidence/staging-promotion/check_mckinsey.py` and `.omo/evidence/staging-promotion/mckinsey-completeness.txt` (gitignored).
- Manifest validation: 40 sources, 0 problems. It checks declarations and records, not licence rights.
- Description gap: the upstream description does not name a "use instead" alternative. The vendored file is not edited; the gap is recorded in `limitations` and rendered into `ATTRIBUTION.md`.

## Site

- Category `mckinsey-problem-solving` is filed under `lead` and labelled "Structured problem solving".
- Site totals: 758 skills, 30 categories, 91 communities, 61 Solutions.
- Repository counts: 740 skill files, 28 directories, 739 linted.
- The graph separation cap increased from 20 to 80 passes. At 757 nodes the final separation did not converge in 20 passes; the closest pair was still 14.9186 before the write, below the 15.0 guarantee, and `site/tests/test_network.py` failed. The change does not lower `MIN_GAP`, change the `MIN_GAP + 0.6` target, or alter identity/evidence semantics. Reviewers should treat it as a behavior change included with the import.

## Reviews

- Momus: OKAY after three rounds.
- Metis: UNBLOCKED after four rounds and a throwaway end-to-end import.
- Standards: PASS. The description gap is a disclosed vendored limitation. The graph separation change is an accepted geometry fix. The final review also found the authored `research-ops/skills/mckinsey-research` skill inside the legacy Alireza import; the exception is recorded in the attribution and inventory. It found the attribution tier keyed to licence evidence rather than an immutable ref; `site/build.py` now keys the tier to the ref.
- Spec: PASS after the evidence bookkeeping was completed.
- Oracle for `mckinsey-problem-solving`: APPROVE, no blocking conditions. Verdict at `.omo/plans/oracle-mckinsey-problem-solving-final-verdict.md`.
- Oracle for `abdullah-mckinsey-research`: approve with conditions. The notices wording caveat is applied in `276a902`; maintainer acceptance is recorded for staging by the push. The ADR remains `Status: proposed` for the main merge decision.

## Local validation, 2026-11-05

All checks were run from the checkout root with the repository scripts.

| Check | Result |
| --- | --- |
| `python3 scripts/lint_skills.py --self-test` | 9 cases, 0 failures |
| `python3 scripts/lint_skills.py` | 739 linted, 0 errors, 2 vendored warnings, 33 baseline |
| `python3 scripts/generate_index.py --check` | up to date |
| `python3 scripts/sync_vendor.py --validate-manifest` | 40 sources, 0 problems |
| `python3 scripts/audit_third_party.py` | 506 markers, 0 unaccounted |
| `python3 scripts/check_links.py` | 2016 files, 2845 links, 0 unresolved |
| `python3 scripts/check_links.py --scope vendored` | 2008 files, 2623 links, 0 unresolved |
| `python3 scripts/check_solutions.py` | 3 solutions, every step resolves |
| `python3 scripts/check_skill_dependencies.py --include-legacy` | 27 providers, 79 files, OK |
| `python3 -m unittest discover -s scripts -p 'test_*.py'` | 190 tests, OK |
| agent-harness tests | 35 tests, OK |
| harness manifest `--check` | 18 manifests, no drift |
| `site/build.py --check` | up to date, 758 skills, 30 categories |
| `site/tests/test_deploy_workflows.py` | 38 tests, OK |
| `site/tests/test_network.py` | all graph assertions hold |
| `site/tests/test_compose.py` | all composition checks passed |
| `npm run lint:html` | clean |
| `npm run lint:secrets` | clean |
| `node scripts/prove-deploy-gate.mjs` | all cases passed; correct marker exits 0, wrong and missing markers exit 1 |
| `npx playwright test --workers=1 --retries=1` | 191 passed, 1 skipped, 0 failed |
| `npx playwright test tests/content.spec.js --workers=1 --retries=1` (after the attribution-tier fix) | 12 passed |

The recorded browser comparison from the import work is 191 passed, 1 skipped, 0 failed on both the import tree and the `9051b3f` base. The notices and runner-pin changes do not alter the generated site output. After the attribution-tier fix, the content spec passed 12/12.

## CI

`368484b` passed A0 skills checks, A1 site checks, and A2 site deploy staging. A2 includes upload and live revision verification.

The first push of `276a902` failed because `ubuntu-latest` resolved to Ubuntu 26.04 and Playwright 1.55.0 does not support Chromium there. `368484b` pins `s1-site-validate.yml`, `s3-site-verify.yml` and `m1-site-refresh-sources.yml` to `ubuntu-24.04`. The rerun passed.

## Promotion boundary

- No promotion was performed. `b1-site-promote-to-main.yml` was not run, `main` was not updated, and production was not touched.
- The unrelated production approval that has been waiting since 2026-10-04 remains outside this change.
- Open items for the maintainer: accept the declaration-only licence basis in the ADR, review the graph separation fix as a behavior change, and decide whether to promote.

## Commands

```bash
python3 scripts/lint_skills.py --self-test
python3 scripts/lint_skills.py
python3 scripts/generate_index.py --check
python3 scripts/sync_vendor.py --validate-manifest
python3 scripts/audit_third_party.py
python3 scripts/check_links.py
python3 scripts/check_links.py --scope vendored
python3 scripts/check_solutions.py
python3 scripts/check_skill_dependencies.py --include-legacy
python3 -m unittest discover -s scripts -p 'test_*.py'
HARNESS_SOURCE_ROOT="$PWD" python3 -m unittest discover -s skills/engineering/agent-harness/tests -p 'test_*.py'
python3 skills/engineering/agent-harness/skills/agent-harness/scripts/harness_manifest_builder.py --check --repo-root .
cd site && python3 build.py --check
python3 site/tests/test_deploy_workflows.py
cd site && python3 tests/test_network.py
cd site && python3 tests/test_compose.py
cd site && npm run lint:html
cd site && npm run lint:secrets
cd site && node scripts/prove-deploy-gate.mjs
cd site && npx playwright test --workers=1 --retries=1
```
