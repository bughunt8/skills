# Matt Pocock release tracking

The repository imports the stable Matt Pocock release through
`skills/vendor.manifest.json` and audits it in `.agents/skill-dependencies.json`.
`scripts/track_matt_release.py` updates the whole set together: pins, hashes,
source URLs, the legal resource, attribution, the dependency registry, docs, the
site and the harness inventories.

## Current release

<!-- BEGIN MATT RELEASE -->
| Release | `v1.3.1` |
| Commit | `24fe0ef7737efae15c87225755e9f6f5965e4888` |
| Providers | 27 |
| Files | 79 |
| Operative edges | 18 |
<!-- END MATT RELEASE -->

## Commands

```bash
# Report whether the latest stable tag differs from the pin
python3 scripts/track_matt_release.py --check

# Check a deliberate pre-release branch
python3 scripts/track_matt_release.py --check --ref main

# Apply a compatible release, regenerate, verify, and update the checkout
python3 scripts/track_matt_release.py --write
```

`--check` writes nothing and exits 0 for a current pin, 1 for an available
update, and 2 for a semantic or gate refusal. `--write` refuses a dirty tree,
applies the update in a temporary worktree, runs the checker and focused gates,
and copies back only after they pass. A copy-back failure restores the checkout.

## What the tracker updates

- Every `mattpocock-*` manifest source: `ref`, `pinned_commit`, `expected_commit`,
  `homepage` and `pinned_at`.
- `.agents/skill-dependencies.json`: `upstream_commit`, `release`, `release_ref`,
  the legal resource, every provider and file hash, every source URL, the
  declared counts and the regenerated `legacy_bindings`.
- Generated attribution: `LICENSE.upstream`, `ATTRIBUTION.md`, `PROVENANCE.md`
  and `THIRD_PARTY_NOTICES.md` through `sync_vendor.py`.
- `README.md`, `AGENTS.md`, `.agents/invocation.md` and
  `docs/legacy-harness-bindings.md` current-pin references.
- `site/index.html`, `site/data.js`, `site/intro.html`, the three mutable
  `site/tests/library-size.mjs` literals, and the harness inventories.

Historical documents keep their original pins: `docs/matt-pocock-v1.3.1.md`, the
setup migration references and `MATTPOCOCK_SKILLS_ATTRIBUTION.md`.

## Fail-closed points

The tracker refuses a release that:

- adds, removes or renames a provider;
- changes a provider path or invocation policy;
- changes the body evidence for an operative dependency edge;
- has no `LICENSE`, a symlink, an unreadable frontmatter, or no release tag.

Those changes need a human parser and graph review. Hash-only updates never
rewrite the graph.

## Staging workflow

`.github/workflows/sync-matt-release.yml` runs weekly and on demand. It checks
`staging`, runs the tracker `--check` and `--write`, runs the A0 and S1 gates in
the job, and opens or updates a PR against `staging`. It does not auto-merge.
A pull request created with `GITHUB_TOKEN` cannot trigger `a0-skills-checks` or
`s1-site-validate`, so the job runs the same checks itself.

## Tests

```bash
python3 scripts/track_matt_release.py --self-test
python3 -m unittest discover -s scripts -p 'test_track_matt_release.py' -v
python3 -m unittest discover -s scripts -p 'test_skill_dependencies.py' -v
```

The fixture tests use a local git upstream and a small manifest/registry. They
cover no-op, compatible update, provider-set change, invocation change, missing
license, library-size updates, docs updates and the workflow contract.
