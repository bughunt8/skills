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

**Most of what is indexed under this name is itself imported from elsewhere.**
Of the skills attributed to `bughunt8/skills` on this page, all but one are
vendored from other projects — the host repository is largely an aggregator, and
only `start-github-repo` is original to it.

Every upstream project is listed below. The page's list is generated from
`skills/vendor.manifest.json` and `docs/third-party-inventory.json` on every
build, so an import that is not in this table fails CI. Where an upstream has no
public repository URL, the link points at the licence file vendored with it.

| Upstream project | Author | Licence | Import |
| --- | --- | --- | --- |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | Addy Osmani | MIT | refreshed |
| [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd) | Ayoub Ghriss (@ayghri) | MIT | refreshed |
| [backnotprop/pstack](https://github.com/backnotprop/pstack) | Lauren Tan (@backnotprop, "poteto") | MIT | refreshed |
| [bhubanmm/togaf-advisor](https://github.com/bhubanmm/togaf-advisor) | Bhuban | MIT | hand-copied |
| [borahanmirzaii/alirezarezvani-claude-skills](https://github.com/borahanmirzaii/alirezarezvani-claude-skills) | Alireza Rezvani and contributors | MIT | hand-copied |
| [collab-proof](https://github.com/bughunt8/skills/blob/main/skills/engineering/collab-proof/LICENSE) | dong7812 | MIT | hand-copied |
| [deeparchi-ai/togaf-skill](https://github.com/deeparchi-ai/togaf-skill) | DeepArchi | MIT | hand-copied |
| [DogInfantry/claude-skill-management-consultant-B1](https://github.com/DogInfantry/claude-skill-management-consultant-B1) | DogInfantry | Apache-2.0 | hand-copied |
| [domelic/github-repository-setup](https://github.com/domelic/github-repository-setup) | Damir Omelic | MIT | hand-copied |
| [explainer-graphic](https://github.com/bughunt8/skills/blob/main/skills/productivity/explainer-graphic/LICENSE) | Silicon Valley Academy | MIT | hand-copied |
| [Forward-Future/loop-library](https://github.com/Forward-Future/loop-library) | Forward Future | MIT | hand-copied |
| [google-labs-code/stitch-skills](https://github.com/google-labs-code/stitch-skills) | Google Labs and contributors | Apache-2.0 | hand-copied |
| [humanlayer/skills](https://github.com/humanlayer/skills) | HumanLayer and contributors; `show-me` credited to Dex Horthy | MIT | refreshed |
| [jamesrochabrun/skills](https://github.com/jamesrochabrun/skills) | James Rochabrun | MIT | hand-copied |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | Leonxlnx | MIT | hand-copied |
| [mattpocock/skills](https://github.com/mattpocock/skills) | Matt Pocock (@mattpocock) | MIT | refreshed |
| [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) | Microsoft Corporation | MIT | hand-copied |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Next Level Builder | MIT | hand-copied |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Paul Bakaus | Apache-2.0 | hand-copied |
| [playwright-pro](https://github.com/bughunt8/skills/blob/main/skills/engineering-team/playwright-pro/LICENSE) | Reza Rezvani | MIT | hand-copied |
| [Remotivated/job-hunt-skills](https://github.com/Remotivated/job-hunt-skills) | Remotivated | MIT | refreshed |
| [self-improving-agent](https://github.com/bughunt8/skills/blob/main/skills/engineering-team/self-improving-agent/LICENSE) | Reza Rezvani | MIT | hand-copied |
| [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) | VoltAgent | MIT | hand-copied |

"Refreshed" imports are commit-pinned in `skills/vendor.manifest.json` and updated
on a schedule; "hand-copied" imports predate that manifest and are recorded in
`docs/third-party-inventory.json`. The per-skill attribution and licence files
travel inside the vendored trees, and the authoritative record is
[the host repository's `THIRD_PARTY_NOTICES.md`](https://github.com/bughunt8/skills/blob/main/THIRD_PARTY_NOTICES.md).

### haowjy/creative-writing-skills

- Repository: <https://github.com/haowjy/creative-writing-skills>
- Licence: Apache-2.0
- Indexed path: `cw/skills/` (its own `.claude-plugin/marketplace.json` declares
  `source: './cw'` as the plugin root; the top-level `skills/` tree is a partial
  copy in a different frontmatter format)
- Note: the build deduplicates by the **content hash of `SKILL.md`**, not by
  name, so each skill appears once and two different skills that merely share a
  name are both kept.

### eternityspring/shuohao-skills

- Repository: <https://github.com/eternityspring/shuohao-skills>
- Licence: Apache-2.0, with a `NOTICE` file in the upstream repository
- Indexed path: `skills/`

## Runtime libraries

### vis-network

- Source: <https://github.com/visjs/vis-network>
- Version: 9.1.6
- Licence: MIT and Apache-2.0 (dual-licensed)
- Path: `site/lib/vis-network.min.js`
- Use: Self-hosted graph visualization engine powering the standalone constellation intro at `site/intro.html`.

The graph workspace itself has no runtime JavaScript dependencies. Previous releases
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
