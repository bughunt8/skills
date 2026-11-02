# Source analysis: Abdullah4AI/mckinsey-research

This skill is an adaptation, not a copy. The upstream is a read-only reference at
`docs/reference-sources/abdullah-mckinsey-research/source/`, imported by
`scripts/sync_vendor.py` from a commit-pinned source.

## Upstream

| Field | Value |
| --- | --- |
| Repository | <https://github.com/Abdullah4AI/mckinsey-research> |
| Author | Abdullah AlRashoudi (@Abdullah4AI) |
| Commit | [`140ecedf57414521bf55fc485e140d151cfb44fd`](https://github.com/Abdullah4AI/mckinsey-research/commit/140ecedf57414521bf55fc485e140d151cfb44fd) |
| Licence | MIT declared in `README.md`; no standalone `LICENSE` file exists upstream |
| Imported | `SKILL.md`, `README.md`, `references/`, `templates/report.html` |
| Excluded | `data/` (runtime state, not instruction) |

As of 2026-11-02, none of the nine commits reachable from `main` contains a
`LICENSE` or `COPYING` file. The GitHub repository metadata field reports
`license: null`; the dedicated `/license` endpoint returns HTTP 404. The only
statement is the last section of `README.md`. The importer preserves that statement verbatim in
`LICENSE.upstream` and labels it as evidence, not as a standalone licence. The
manifest check records the declaration and provenance fields; it does not
authenticate the evidence or verify the right to license. The separate
completeness check compares the imported bytes with the pinned source.

## Why this is a reference, not a vendored skill

The upstream `SKILL.md` description is 1,619 characters, over this repository's
1,024-character SK006 limit. Vendored files are not edited, and adding a baseline
exception for a newly introduced violation is not allowed. The upstream file
therefore stays outside the linted `skills/` tree, and this authored skill is the
routable surface. That is the same split used for
`docs/reference-sources/addyosmani-sdd/source/` and
`skills/engineering/spec-driven-development/`.

## What the adaptation changes

- The twelve upstream analyses and their dependency order are preserved.
- The intake, scope confirmation, sanitisation, tool limits and artifact
  locations are restated in this skill's own words.
- The upstream `data/` state layer is replaced by the user's
  `artifacts/research/` workspace.
- The upstream prompt text is loaded from the reference at run time, not copied
  into this directory.

## Verification

```bash
python3 scripts/sync_vendor.py --validate-manifest
python3 scripts/sync_vendor.py --check --source abdullah-mckinsey-research
python3 scripts/check_links.py --path skills/research-ops/skills/mckinsey-research
```

The completeness check compares the pinned checkout with the imported tree and
must report 21 selected files, no missing, no extra and no mismatch. It also
asserts that `source/data` does not exist.

## Open item

Ask upstream to add a `LICENSE` file with a named copyright holder. If it does,
switch the manifest from `license_evidence_path` to `license_path` and regenerate
the attribution and licence copy.
