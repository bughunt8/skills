---
name: repo-skill-updater
description: "Add a new local skill or import an external skill repository into bughunt8/skills without changing the library's structure or generated-file contract. Use this skill whenever the user asks to add, import or integrate a skill or skill repo, even if they do not say 'skill'. Use skill-creator for the draft and review loop, write-a-skill for authoring craft, and vendor-import for the external import procedure. Not for editing a vendored tree, refreshing an existing source, or promoting staging to main."
---

# Repo skill updater

This skill is a decision layer and checklist. It does not replace `write-a-skill` or
`vendor-import`, and it does not add a second import path.

## When to use

Use this skill when the task is to add something new to the library:

- a new locally authored skill
- a new external skills repository
- a new reference tree that supports a skill

Do not use it for editing someone else's vendored tree, for refreshing an already
managed source, or for promoting `staging` to `main`.

## Read first

- `AGENTS.md`, especially "Adding a skill" and "Vendoring an external repository".
- `CONTRIBUTING.md`, especially the vendoring contract and the generated-file rules.
- `skills/engineering/write-a-skill/skills/write-a-skill/SKILL.md` for authoring craft.
- `skills/engineering/skill-creator/SKILL.md` for drafting and review. The full eval loop needs the Anthropic `claude` CLI and a browser, which this repository does not install.
- `skills/engineering/vendor-import/SKILL.md` for the external import procedure.
- `skills/pstack/unslop/SKILL.md` for every sentence you write.

## Decide the path

| Situation | Procedure |
| --- | --- |
| New local skill | Write it under `skills/<domain>/<skill-name>/SKILL.md`, then regenerate. |
| New external repository | Add one source to `skills/vendor.manifest.json`, then run the vendor sync. |
| New reference source | Add a `paths` entry with `kind: "support"`, select the subset with `file_include`, keep the relative distance, and verify links with `check_links.py --path`. |
| Refresh an existing source | Run `python3 scripts/sync_vendor.py --sync --source <id>` directly. This skill does not own refreshes. |
| Edit a vendored file | Do not edit. Send the change upstream, or exclude the skill and record why. |
| Promote staging | Do not perform it. Only the maintainer promotes. |

## Before either path

1. Work on `staging`. Confirm `git status` is clean before you start.
2. Check that the skill name is free. For a local skill, create it and run `python3 scripts/lint_skills.py`; SK007 reports a duplicate name across the whole library, including quoted names. For an external import, compare the upstream frontmatter names with the local names before adding the source. A grep pre-check is not reliable because frontmatter names may be quoted.
3. Decide whether the change adds a new domain. A new domain is a larger change: add a line to `docs/domain-descriptions.json`, add the category to a domain group in `site/domains.json`, and optionally add a `LABELS` entry in `site/build.py` for a display name. The build falls back to the directory name when no label exists, so the label is presentation, not a build prerequisite.
4. Read the existing skill that is closest to the task. Match its structure and prose.

## Local skill

1. Create `skills/<domain>/<skill-name>/SKILL.md`. The `SKILL.md` is the required entry point. Add subdirectories such as `references/`, `templates/`, `scripts/`, `tests/`, `assets/`, `examples/`, `schemas/` or `datasets/` inside that skill directory only when the skill needs them. Do not add a new top-level directory outside `skills/<domain>/<skill-name>/`. Vendored skills may carry other directories such as `agents/` or `eval-viewer/`; that is their layout, not a new local convention.
2. Keep the frontmatter minimal:

   ```yaml
   ---
   name: skill-name
   description: "What it does. Use when ... . Use <other skill> instead for ..."
   ---
   ```

   `name` must equal the directory name and be lowercase kebab-case. The description is at most 1024 characters and must say what the skill does, when to use it, and what to use instead.
3. Use the direct layout `skills/<domain>/<skill-name>/SKILL.md` unless the domain already uses a bundle. Do not put an authored skill inside a legacy imported bundle such as `skills/research-ops/skills/` without recording a `local_additions` entry in `docs/third-party-inventory.json` and the matching attribution file.
4. Use `skills/engineering/skill-creator/SKILL.md` for the draft and review loop. Keep test prompts, outputs and benchmark files in the gitignored `.omo/` workspace. Do not commit a generated `evals/` or `<skill>-workspace/` directory to the skill unless the repository adopts that convention. If you cannot run the eval loop, say so and use manual review instead.
5. If this is a new domain, add the category to `site/domains.json` and optionally add a `LABELS` entry in `site/build.py` before the site build. The build uses the directory name when no label exists.
6. Regenerate the generated files:

   ```bash
   python3 scripts/lint_skills.py
   python3 scripts/generate_index.py --write
   python3 skills/engineering/agent-harness/skills/agent-harness/scripts/harness_manifest_builder.py --all --repo-root . --no-timestamp --out-dir skills/engineering/agent-harness/skills/agent-harness/assets/harnesses
   (cd site && python3 build.py --write)
   ```

   Without `--out-dir`, the harness builder prints JSON and does not write the committed manifests.

7. Update the hand-maintained counts:
   - `site/tests/library-size.mjs`: transcribe the new site total, category count and solution count from `site/data.js` into the literals after the build. Do not import `data.js` in the test; the literal is the anti-shrink assertion.
   - `AGENTS.md`: read the repository total and directory count from the `README.md` generated header after `generate_index.py --write`, and the linted count from `lint_skills.py`'s `N skill(s) checked` line. Do not use `site/data.js` for these numbers.
8. Run the verification block at the end of this skill.
9. Commit with `feat(skills): add <name> to <domain>`. Push only when the user asks. Never promote.

## External repository

Follow `skills/engineering/vendor-import/SKILL.md` phase by phase. The mapping shapes you need are:

- Flat `skills/<skill>/SKILL.md`: one path entry, `from: "skills"`, `to: ""`, `kind: skill-collection`, `include: ["*"]`.
- Nested `skills/<category>/<skill>/SKILL.md`: one path entry per category.
- A single skill with bundled support directories: `from: "plugins/<plugin>/skills/<skill>"`, `to: ""`, `kind: "skill"`, destination `skills/<domain>/<skill>`. This is how `skill-creator` is imported.
- A support subtree only when a Markdown link points into it, mapped at the same relative distance.

For a support tree, use a `paths` entry with `kind: "support"`, map `from` the upstream support root to the destination at the same relative distance, and select the subset with `file_include`. Keep prose-only references out and record them in `limitations`. Verify the destination with `python3 scripts/check_links.py --path <dest>` and run the completeness check against the selected files.

The `kind: "skill"` shape is accepted by the manifest and the sync even though `vendor-import` Phase 2 documents the flat and nested collection shapes. Record the single-skill mapping explicitly in the plan.

The repository-specific additions around the vendor procedure are:

1. Add one source to `skills/vendor.manifest.json`. Do not add `expected_commit` for a new source; `vendor-import` says it blocks the all-source refresh. The manifest has older exceptions, including release-pinned Matt sources and `humanlayer-pr-credit-license`; do not copy that pattern without updating `vendor-import`. For a collection source, record name collisions in `exclude` and `exclude_reasons`; the local skill is canonical. For a single-skill `kind: "skill"` source, a name collision means do not import it.
2. Record the reviewed SHA in the plan before sync. Import only through `python3 scripts/sync_vendor.py --sync --source <id>`. The sync prints the fetched commit and rewrites `pinned_commit`. Compare the fetched commit with the reviewed SHA. If they differ, stop and review the upstream diff again. Do not rely on a later `--check`, which compares against the updated pin.
3. Run `python3 scripts/generate_index.py --write`. If the source adds a category, add it to `site/domains.json` and optionally to `LABELS` in `site/build.py` before `(cd site && python3 build.py --write)`. The build uses the directory name when no label exists.
4. Update the hand-maintained counts with the split from the local skill section: `site/data.js` for `library-size.mjs`, the README header and `lint_skills.py` for `AGENTS.md`.
5. Regenerate the harness inventories with `--all --repo-root . --no-timestamp --out-dir skills/engineering/agent-harness/skills/agent-harness/assets/harnesses`, then require `--check` to pass.
6. Prove completeness with a real byte copy, never a hardlink. A hardlink shares the inode and can mutate the vendored tree. For a single-skill `kind: "skill"` source, `UP` is the upstream skill directory and `DST` is the destination skill directory; compare the same relative tree, and ignore the destination root `PROVENANCE.md` as well as the other generated files. The vendor-import snippet's depth check assumes a collection layout. Project the upstream inventory through the same `file_include` selection before comparison so excluded files do not appear as missing. Ignore only importer-generated files. Run the positive case and the missing, extra and mismatch cases. The positive case is complete; each negative case must report one difference, exit 1, and leave the destination digest unchanged.
7. Run the verification block and commit with `feat(vendor): import <id>` locally. Write the Oracle brief and run the Oracle review. If Oracle finds must-fixes, add a follow-up commit; do not amend. Push only when the user asks. Never promote.

## Generated and hand-maintained files

Generated by scripts. Regenerate them; never hand-edit them.

- `README.md` block between `BEGIN GENERATED` and `END GENERATED`
- `THIRD_PARTY_NOTICES.md`
- every `PROVENANCE.md`
- every vendored `ATTRIBUTION.md`
- `LICENSE.upstream` and `.vendor-owned.json`
- `site/index.html`, `site/data.js`
- the 18 harness manifests, written by the harness builder

Hand-maintained data. Edit these deliberately and read the values from the stated source.

- `site/tests/library-size.mjs`, from `site/data.js`
- the three counts in `AGENTS.md`, from the README header and `lint_skills.py`
- `site/domains.json` and `LABELS` in `site/build.py`, when a category is new
- `site/intro.html` except its audited headline count; the rest is hand-written prose. `build.py --write` rewrites the headline and `--check` audits it. `lint:html` validates `index.html`, not `intro.html`.

## Verification

Run from the checkout root and report the actual output:

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
(cd site && python3 build.py --check)
python3 site/tests/test_deploy_workflows.py
python3 site/tests/test_network.py
python3 site/tests/test_compose.py
(cd site && npm ci)
(cd site && npm run lint:html)
(cd site && npm run lint:secrets)
(cd site && npx playwright test --workers=1 --retries=1)
```

For a local skill, run the vendored validator when it is present: `python3 skills/engineering/skill-creator/scripts/quick_validate.py skills/<domain>/<skill-name>`. The repository linter remains authoritative.
For an external source, run `python3 scripts/sync_vendor.py --check --source <id>` as a drift report. It exits 1 when upstream moved; it is not a blocking gate.
For a site-visible change, run the same command with `--workers=1 --retries=1` on a worktree at the pre-change commit for this task and on the change, then compare the pass, fail, skip and timeout sets.

For every failure, read the exact failing step and fix the data or the script. Do not lower a threshold, add a lint baseline entry, or edit a generated file to make a check pass. Remove local `__pycache__` before the secret scan if a test just created one; the scan flags compiled test fixtures.

## Evidence

Keep or record the evidence for the maintainer:

- the plan and its review receipts
- the exact gate results, including counts
- the completeness results, including exit codes and the destination digest
- the browser comparison against the base commit
- the Oracle verdict
- the commit on `staging`, if the user asked for a push, with no promotion

## Must not

- Do not copy external files by hand.
- Do not edit a vendored directory, `PROVENANCE.md`, `ATTRIBUTION.md`, `LICENSE.upstream`, `.vendor-owned.json`, `THIRD_PARTY_NOTICES.md`, or the generated `README.md` block.
- Do not add `expected_commit` to a new source without updating `vendor-import`. It aborts the all-source refresh. The manifest's existing guarded sources are exceptions, not a pattern to copy.
- Do not hand-edit `pinned_commit` or `pinned_at`; the sync writes them.
- Do not add a lint baseline entry for a violation you introduced.
- Do not invent a total, category count or community count. Read the site numbers from `site/data.js` and the repository numbers from the README header and `lint_skills.py`.
- Do not add an authored skill inside a legacy import without recording the exception.
- Do not add a new top-level directory outside `skills/<domain>/<skill-name>/`. Keep skill-creator's eval workspace in `.omo/`; do not commit a generated `evals/` or `<skill>-workspace/` unless the repository adopts one.
- Do not change `site/network.py` or `site/compose.py` identity or evidence semantics.
- Do not push, merge, deploy or promote on your own. Push `staging` only when the user asks. Promotion to `main` belongs to the maintainer.

## Failure handling

- Name collision: exclude the upstream skill and record the reason. The local skill stays canonical; do not rename it.
- Moved upstream pin: stop and review the upstream diff. Do not accept the new tree.
- Symlink or path escape: stop. The importer must reject it.
- Missing licence: use `license_evidence_path` and label the result as a declaration. Do not invent a licence file.
- Completeness mismatch: stop. Do not adjust the expected numbers.
- Site count or graph failure: fix the source data or the generator. Do not loosen the test.
