# Attribution

## Where the idea comes from

This skill implements an approach taken from **[archify](https://github.com/tt-a1i/archify)**
by **tt-a1i**, examined at commit
[`ed7f4d4b48d4424d36edfed8043de3de8dea6b45`](https://github.com/tt-a1i/archify/tree/ed7f4d4b48d4424d36edfed8043de3de8dea6b45)
(6 September 2026).

- **Upstream licence:** MIT
- **Upstream copyright:** Copyright (c) 2026 tt-a1i (Archify), and
  Copyright (c) 2025 Cocoon AI
- **archify's own attribution:** its `SKILL.md` records
  `based_on: Cocoon-AI/architecture-diagram-generator (MIT, v1.0)`

Both copyright holders are named because archify is itself a derivative. Crediting
only the repository you happened to find, and dropping the notice it inherited, is
how an attribution chain quietly gets laundered one hop at a time.

## What was taken, and what was not

**Taken — the design, which is not copyrightable but is absolutely borrowed:**

- Author a diagram as a small, validated JSON intermediate representation rather
  than as markup in a diagramming DSL
- Render to a single standalone HTML artifact with inline SVG, so the output has
  no runtime dependency and survives without a toolchain
- Support architecture, workflow, sequence, data-flow and lifecycle from one
  document format
- Ship dark and light themes and an interactive viewer in the artifact itself

**Not taken — nothing was copied:**

- No source file, function, or fragment of archify's code. Every script here was
  written for this repository. archify is roughly 193 files of JavaScript
  (`.mjs`); this is three Python modules on the standard library.
- No HTML template, CSS, or theme values. `templates/theme.css` and
  `templates/viewer.html` are original.
- No schema file. `schemas/diagram.schema.json` and the document shape it
  describes were designed here and differ from archify's JSON-IR.
- **No brand-mark or icon data.** See below.

The two projects are therefore not drop-in compatible, and a document written for
one will not render in the other.

## Why the brand marks were deliberately left out

archify bundles vector brand marks for technologies and services, generated from
[Simple Icons](https://github.com/simple-icons/simple-icons). Its
`THIRD_PARTY_NOTICES.md` is admirably honest that the collection's CC0 licence
does not flow through to the individual marks, and records per-mark terms that
include:

| Mark | Recorded licence | Problem for this repository |
| --- | --- | --- |
| Vue.js | `CC-BY-NC-SA-4.0` | **Non-commercial.** Incompatible with commercial use of an MIT-licensed library. |
| Jenkins | `CC-BY-SA-3.0` | Share-alike obligations on redistribution. |
| Rust | `CC-BY-SA-4.0` | Share-alike obligations on redistribution. |
| Angular | `CC-BY-4.0` | Attribution obligations per mark. |
| Apache Airflow, Apache Kafka | `Apache-2.0` plus ASF trademark policy | Trademark policy applies separately from the licence. |
| OpenAI | no licence, brand guidelines only | Use governed entirely by current brand guidelines. |

This repository is MIT and is intended to be usable commercially, including on
client work. Vendoring a non-commercial, share-alike asset into it would quietly
attach conditions to the whole library that its licence does not declare. That is
a real problem rather than a theoretical one, so the marks are simply absent.

Nodes here carry an optional `tech` text label instead. It costs a logo and buys
a diagram anyone can ship.

## No upstream code is redistributed

Because nothing was copied, this directory does not redistribute archify and does
not include a copy of archify's MIT licence text; there is no upstream code here
for that licence to govern. The attribution above exists because the design debt
is real and worth stating plainly, not because MIT compels it in the absence of
copied code.

If tt-a1i considers any part of this an derivative requiring the notice preserved
in-tree, open an issue and the MIT text will be added here.

## Related upstream reading

archify's own documents are worth reading directly, and are better than a summary
of them:

- [`SKILL.md`](https://github.com/tt-a1i/archify/blob/main/archify/SKILL.md)
- [`DESIGN.md`](https://github.com/tt-a1i/archify/blob/main/DESIGN.md)
- [`THIRD_PARTY_NOTICES.md`](https://github.com/tt-a1i/archify/blob/main/THIRD_PARTY_NOTICES.md)

If you want archify's full feature set — Mermaid import, PNG, JPEG, WebP and WebM
export, brand marks, architecture deltas between two revisions, visual regression
checking — use archify. It does considerably more than this skill does. This skill
covers the core output with no dependencies and no licence encumbrance.
