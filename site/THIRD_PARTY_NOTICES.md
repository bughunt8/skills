# Third-party notices

This repository builds a page that **indexes and describes** skills published in
other repositories. It does not redistribute their contents: each card shows a
skill's declared name and description and links to the repository it came from.

The descriptions shown on the page are read from each skill's own `SKILL.md`
frontmatter, so the words on a card are the author's own.

## Indexed sources

Recorded in machine-readable form in [`sources.json`](sources.json), which is the
single place a source is declared.

### bughunt8/skills

- Repository: <https://github.com/bughunt8/skills>
- Licence: MIT, with vendored third-party imports retaining their upstream
  licences. That repository maintains its own `THIRD_PARTY_NOTICES.md` and a
  `skills/vendor.manifest.json` pinning each import to an upstream commit.
- Indexed path: `skills/`

### haowjy/creative-writing-skills

- Repository: <https://github.com/haowjy/creative-writing-skills>
- Licence: Apache-2.0
- Indexed path: repository root
- Note: this repository mirrors the same skills into both `cw/skills/` and
  `skills/`. The build deduplicates by skill name, shallowest path winning, so
  each appears once.

### eternityspring/shuohao-skills

- Repository: <https://github.com/eternityspring/shuohao-skills>
- Licence: Apache-2.0, with a `NOTICE` file in the upstream repository
- Indexed path: `skills/`

## Runtime libraries

The graph workspace has no runtime JavaScript dependencies. Previous releases
included GSAP, ScrollTrigger and Lenis; those scripts have been removed from the
site bundle and are no longer loaded or redistributed with it. Their historical
attribution remains in repository history.

### Fonts

**Self-hosted** under `site/fonts/`, not loaded from Google Fonts.

- **Space Grotesk** by Florian Karsten — SIL Open Font License 1.1
- **Inter** by Rasmus Andersson — SIL Open Font License 1.1

Both are redistributed here as WOFF2, in the `latin` and `latin-ext` subsets only.
Google serves both as variable fonts, so one file covers each family's whole weight
range; the duplicate per-weight downloads were dropped after confirming the bytes
were identical.

The OFL permits redistribution and bundling, including in a commercial project,
provided the fonts are not sold on their own and the licence travels with them.
Neither font has been modified or renamed. Full licence text:
<https://openfontlicense.org/open-font-license-official-text/>.

CJK text in skill descriptions is not covered by either family and falls back to
the reader's system font by design; bundling a CJK face would add megabytes for a
handful of strings.

## Development-only dependencies

Used by CI and never served to a reader: `@playwright/test` (Apache-2.0),
`@axe-core/playwright` (MPL-2.0), and `html-validate` (MIT).

## Corrections

If you author one of the indexed skills and want an attribution corrected or your
work removed from the index, open an issue on this repository and it will be
actioned.
