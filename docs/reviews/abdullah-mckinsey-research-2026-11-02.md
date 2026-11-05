# Review evidence: mckinsey-research import

Date: 2026-11-02. Branch `staging`, based on `c6249a7`.

## Repository gates

| Gate | Result |
| --- | --- |
| `scripts/lint_skills.py --self-test` | 9 cases, 0 failures |
| `scripts/lint_skills.py` | 739 linted, 0 errors, 2 vendored warnings, 33 baseline |
| `scripts/generate_index.py --check` | up to date, 740 skills |
| `scripts/sync_vendor.py --validate-manifest` | 40 sources, 0 problems |
| `scripts/sync_vendor.py --check --source abdullah-mckinsey-research` | no drift |
| `scripts/audit_third_party.py` | 506 markers, 0 unaccounted |
| `scripts/check_links.py` (default scope) | 2016 files, 2847 links, 0 unresolved |
| `scripts/check_links.py --path …` (new docs included) | 2026 files, 2856 links, 0 unresolved |
| `scripts/check_solutions.py` | 3 solutions, all steps resolve |
| `scripts/check_skill_dependencies.py --include-legacy` | 27 providers, 79 files, OK |
| `unittest discover -s scripts` | 190 tests, OK (85 adoption tests) |
| `github-repository-setup/scripts/test_bundle.py` | 19 tests, OK |
| spec-driven-development tests | 76 tests, OK |
| openheart-analysis tests | 54 tests, OK |
| agent-harness tests | 35 tests, OK |
| harness manifest `--check` | 18 manifests, no drift |
| `site/build.py --check` | up to date, 758 skills, 30 categories |
| `site/tests/test_compose.py` | all checks passed |
| `site/tests/test_network.py` | all graph assertions hold |
| `site/tests/test_deploy_workflows.py` | 38 tests, OK |
| `npm run lint:html` | clean |
| `npm run lint:secrets` | clean |

## Import completeness

`--validate-manifest` checks metadata presence, not declaration contents,
authenticity or rights. The byte comparison below establishes that the imported
content matches the pinned source. The pinned checkout (`140ecedf5741`) and the
imported `source/` agree on all 21 selected files: no missing, no extra, no hash
mismatch. `source/data` is absent. The negative cases (missing, extra, changed
byte) each exit 1 on a real copy under `.omo/evidence/staging-promotion`; the
vendored tree hash is unchanged afterwards. The script is retained at
`.omo/evidence/check_reference_import.py` and its output at
`.omo/evidence/staging-promotion/abdullah-completeness.txt` (both gitignored).

The authored skill is a local addition inside the legacy `skills/research-ops`
domain. It is recorded as an exception in
`skills/ALIREZAREZVANI_CLAUDE_SKILLS_ATTRIBUTION.md` and
`docs/third-party-inventory.json` under `local_additions`.

## Functional QA

The isolated QA subagent failed to start. Stages A, B and C were executed
manually from the authored skill text and are recorded in the gitignored
`.omo/evidence/mckinsey-qa/transcript.md`.

Stage A asked for the output language and the 18-field intake in one message. It
started no analysis and wrote no file. The 18-field schema is verified by
inspection, not by an agent run.

- Stage B produced a scope summary and stopped at `AWAITING SCOPE CONFIRMATION`.
  It predates the full/light/skipped coverage rule and did not enumerate
  coverage; that rule is verified by inspection, not by the manual run.
- Stage C wrote `01-tam.md`, `12-synthesis.md` and a self-contained HTML report
  outside `skills/`. Both Markdown outputs meet the 500-word floor: 676 words and
  623 words. The reference tree hash was unchanged during the QA run. It changed
  later only because the generated attribution was regenerated, not because the
  QA wrote into it.

Stages B and C are a manual walkthrough, not an agent execution. They show that
the instructions describe the scope gate, the artifact boundary and the output
floor. They do not prove agent execution, agent enforcement of the 500-word
floor, synthesis-failure handling, a full twelve-analysis run, or live source
quality. The outputs are a workflow sample, not an agent transcript.

### Retained observables

Before Stage C, `.omo/evidence/mckinsey-qa/artifacts/` was empty. After:

| Artifact | Size | Words |
| --- | ---: | ---: |
| `.omo/evidence/mckinsey-qa/artifacts/research/2026-11-02-specialty-coffee-riyadh.html` | 1,934 bytes | n/a |
| `.omo/evidence/mckinsey-qa/artifacts/research/specialty-coffee-riyadh/01-tam.md` | 3,898 bytes | 676 |
| `.omo/evidence/mckinsey-qa/artifacts/research/specialty-coffee-riyadh/12-synthesis.md` | 3,773 bytes | 623 |

The reference tree digest is `aa57929b…fadf3b0`. The QA did not write there; the
digest changed after the QA only because the generated attribution was
regenerated. `git status --porcelain` has no `.omo` entry.

No-copy check: 73 paragraphs of at least 120 characters, 0 matches in the
authored skill; the template is 576 bytes with 0 whole-file matches.

Adaptive coverage: "expansion" means analysis 11 (market entry). Any analysis not
named in a stage row runs in full unless the Light/Skip column names it. A full
analysis writes its own file and meets the 500-word floor; a light analysis does
not write a separate file and does not need the floor; a skipped analysis is
listed at the scope gate.

## Browser suite

Current tree after the layout fix, `npx playwright test --workers=1 --retries=1`:

- 191 passed
- 1 skipped
- 0 failed
- 14.2 minutes

Baseline worktree at `c6249a7`, same command, with `site/node_modules`
symlinked:

- 191 passed
- 1 skipped
- 0 failed
- 13.7 minutes

The failure set is empty on both sides. The import introduces no new browser
failure. One test is skipped on both sides. The later failure-reporting change
does not alter the generated coordinates: `site/data.js` and `site/index.html`
are unchanged, so this comparison still applies. The attribution label change
after that run is text-only; the targeted content spec passed 12/12.

## Site layout

Adding one node moved the measured extents of communities 1 and 3 0.37 units into
each other. Increasing the packing margin made the overlap worse because the
frame clamp took over. `site/network.py` now alternates community-extent
separation with node separation until both hold on the rounded coordinates. It
also picks a deterministic direction when two community centres coincide, so the
pass cannot sit still. If the loop exhausts its eight rounds, it raises instead
of publishing coordinates that fail either guarantee. Three synthetic cases in
`site/tests/test_network.py` cover the node-spacing regression, the
coincident-centre case and an infeasible frame that must fail loudly.

## Known limitations

- As of the pinned commit, the upstream has no standalone licence file. The
  import records the README declaration as evidence and says so in the
  attribution.
- The upstream description is 1,619 characters, so the upstream skill is a
  read-only reference and the routable skill is authored.
- The author name is self-declared from the upstream metadata and commit. It is
  not independently verified.
- The authored skill instructs the executing agent to escape research text before
  rendering HTML and forbids scripts, event handlers, iframes, external
  stylesheets and uncited URLs. The repository provides no enforced renderer or
  sandbox.
- `data/` is deliberately excluded as runtime state. Support `exclude` entries
  are literal names, not globs; `file_include` enforces the filter and
  `validate_manifest` rejects a path escape or a dangling symlink before probing
  the destination.
- The site attribution shows `MIT (declared; no upstream licence file) · manual
  pin`, so the qualifier survives the generated page.
- LOW: the importer's `file_include` matches basenames as well as paths, so a
  future `data/README.md` could be selected. `validate_manifest` rejects the
  resulting `data/` directory before a refresh PR. The pinned 21-file import is
  unaffected.
- The QA is a manual walkthrough, not an agent run. The full twelve-analysis
  workflow and live citation checks remain unverified.
- The sync workflow opens a PR and may auto-merge under its own rules; human
  review is not guaranteed.
- The manifest pins `ref` to the reviewed commit. A future upstream README
  change cannot be imported without a manual pin update.
- The manifest stores `license: MIT` as the declaration's name; every generated
  display adds the evidence qualifier.

## Maintainer acceptance

The repository owner requested the import. The declaration-only licence policy
and the `site/network.py` layout fix are included in the same commit because the
graph test fails without the fix. A reviewer should confirm both choices
explicitly rather than read the commit as settled policy.
