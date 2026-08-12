# Upstream attribution

This skill is adapted from [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill), version 2.13.0, by [Next Level Builder](https://github.com/nextlevelbuilder).

The imported data and Python search engine are distributed under the MIT License. The complete upstream license and copyright notice are preserved in [LICENSE](LICENSE).

## Included components

- `SKILL.md` provides the agent workflow and searchable UI/UX reference.
- `data/` contains the upstream design guidance datasets.
- `scripts/` contains the standard-library-only Python search engine, design-system generator, data validator, and regression tests.

## Local layout

The upstream GitHub Copilot installer places its workflow under `.github/prompts/`. This repository organizes reusable skills by domain instead, so the equivalent self-contained skill lives at `skills/design/ui-ux-pro-max/`. Run its commands from this repository's root using the paths shown in `SKILL.md`.
