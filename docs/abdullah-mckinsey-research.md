# Integration report: Abdullah4AI/mckinsey-research

## What was integrated

`Abdullah4AI/mckinsey-research` is a single skill at a repository root. It runs
twelve market and strategy analyses and renders one HTML report. The repository
imports it as a read-only reference and adds an authored, routable skill that
adapts the workflow.

| Item | Value |
| --- | --- |
| Upstream | <https://github.com/Abdullah4AI/mckinsey-research> |
| Author | Abdullah AlRashoudi (@Abdullah4AI) |
| Pinned commit | [`140ecedf57414521bf55fc485e140d151cfb44fd`](https://github.com/Abdullah4AI/mckinsey-research/commit/140ecedf57414521bf55fc485e140d151cfb44fd) |
| Reference | `docs/reference-sources/abdullah-mckinsey-research/source/` |
| Authored skill | `skills/research-ops/skills/mckinsey-research/` |
| Manifest source | `abdullah-mckinsey-research` in `skills/vendor.manifest.json` |
| Imported | 21 files: `SKILL.md`, `README.md`, six reference documents, twelve prompt files, `templates/report.html` |
| Excluded | `data/reports.jsonl`, `data/feedback.json` (runtime state) |

The manifest pins `ref` to the same full SHA, so a future upstream README change
cannot be imported without a manual pin update.

## Why a reference and an authored skill

Two upstream properties make a verbatim vendored skill impossible under this
repository's rules:

1. **No standalone licence file.** As of 2026-11-02, none of the nine commits
   reachable from `main` contains a `LICENSE` or `COPYING` file. The GitHub
   repository metadata field reports `license: null`; the dedicated `/license`
   endpoint returns HTTP 404. The only statement is the final section of
   `README.md`, which says `MIT`. The importer therefore records
   `license_evidence_path: README.md`, copies that file verbatim to
   `LICENSE.upstream` behind a header that calls it a declaration, and labels the
   attribution as unverified. No MIT text or copyright line is invented.
2. **Description length.** The upstream `SKILL.md` description is 1,619
   characters. SK006 caps descriptions at 1,024, vendored files must not be
   edited, and a new baseline exception is forbidden. The upstream file stays
   outside `skills/`; the authored skill is the routable surface.

The same split already exists for `docs/reference-sources/addyosmani-sdd/source/`
and `skills/engineering/spec-driven-development/`.

## Decisions

- `docs/adr/0001-licence-evidence-for-declared-only-upstreams.md` records the
  licence-evidence mechanism and the rejected alternatives.
- `GLOSSARY.md` fixes the terms reference source, authored skill, licence
  evidence and vendored source.
- `skills/engineering/vendor-import/SKILL.md` now documents the evidence path and
  replaces its hardlink negative case with a real copy under `/tmp`.
- `CONTRIBUTING.md`, `README.md` and `AGENTS.md` accept recorded evidence as an
  alternative to a licence file.

## Verification

```text
python3 scripts/sync_vendor.py --validate-manifest
  40 vendored source(s) checked, 0 problem(s)

python3 scripts/sync_vendor.py --check --source abdullah-mckinsey-research
  upstream commit 140ecedf5741 (unchanged), no drift detected

Completeness check (pinned checkout vs imported source/):
  expected 21 imported 21 missing 0 extra 0 mismatch 0
  COMPLETE
  source/data absent
```

The importer tests in `scripts/test_sync_adoption.py` cover the successful
declaration import, mutual exclusion, missing input, path escape, symlink
rejection, unchanged `license_path` mode, a present-but-excluded support path, a
refused path escape in that exclusion, normalization before probing, and a
dangling excluded symlink. The full suite passes.

`--validate-manifest` checks metadata presence, not declaration contents,
authenticity or rights. The byte comparison above establishes that the imported
content matches the pinned source. The author name is self-declared from the
upstream metadata and commit; it is not independently verified.

The authored skill instructs the executing agent to escape research text before
rendering HTML and forbids scripts, event handlers, iframes, external stylesheets
and uncited URLs. The repository provides no enforced renderer or sandbox.

## Open item

Ask upstream to add a `LICENSE` file with a named copyright holder. If it does,
change the manifest from `license_evidence_path` to `license_path` and re-run
`--sync`. Until then, the attribution says what the evidence is and what it is
not.
