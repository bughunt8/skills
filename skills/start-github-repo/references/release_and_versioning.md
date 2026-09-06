# Release, Versioning and Licensing

Answers one decision: **which release tool, which changelog shape, and which license — as a single
coherent choice rather than four independent toggles.**

Read pinned versions from `assets/versions.json`. Never hardcode a version in prose.

---

## 1. Release tooling — pick one, then let it dictate the changelog

| Tool | Config | Action-native | Monorepo | Writes CHANGELOG.md | Version decided by |
|---|---|---|---|---|---|
| **changesets** | `.changeset/config.json` | yes | yes, by design | yes, per package | contributor-declared intent files |
| **release-please** | `release-please-config.json` + `.release-please-manifest.json` | yes | yes, via manifest | yes | Conventional Commits |
| **semantic-release** | `.releaserc.*` / `release.config.*` | runs in any CI | n.a. | via plugin | commit messages |
| **git-cliff** | `cliff.toml` | CLI or Action | yes | yes | configurable bump rules |
| **release-drafter** | `.github/release-drafter.yml` | yes | n.a. | **no** — emits a release body | PR labels |

**Default: changesets for TypeScript.** It is the only candidate designed for multi-package repos
with independent versions and internal-dependency propagation, it is the most actively released, and
pnpm reads and writes the same `.changeset/*.md` files natively.

**Alternative: release-please** when the repo is single-package or multi-language. Note that only
`feat`, `fix` and dependency commits are releasable — `chore` and `build` do not trigger a release —
and `Release-As:` is the override footer.

Survey split across 14 repos: changesets 2, release-please 2, hand-written 3, generated per-version
indexes 2, none at all 5. There is no dominant answer, which is exactly why the scaffolder must ask.

Sources: [changesets](https://github.com/changesets/changesets) ·
[changesets config options](https://github.com/changesets/changesets/blob/main/docs/config-file-options.md) ·
[changesets/action](https://github.com/changesets/action) ·
[pnpm + changesets](https://pnpm.io/it/using-changesets) ·
[release-please](https://github.com/googleapis/release-please) ·
[release-please-action](https://github.com/googleapis/release-please-action) ·
[semantic-release configuration](https://semantic-release.gitbook.io/semantic-release/usage/configuration) ·
[git-cliff configuration](https://git-cliff.org/docs/configuration) ·
[release-drafter](https://github.com/release-drafter/release-drafter)

---

## 2. CHANGELOG.md — and the coupling that trips people up

**changesets users conventionally keep no root `CHANGELOG.md`.** Two of the two surveyed changesets
repos do exactly that, keeping per-package changelogs only. So CHANGELOG and release tooling are
**one choice, not two**. Present these three coherent options:

1. **Hand-kept Keep a Changelog, no release automation** — best for applications and services.
2. **changesets with a generated root CHANGELOG** — single-package libraries.
3. **changesets with per-package changelogs only** — monorepos.

Keep a Changelog requirements: the file is `CHANGELOG.md`; the six section headings are **Added,
Changed, Deprecated, Removed, Fixed, Security**; keep a live `## [Unreleased]` section at the top so
cutting a release is a rename; latest version first; ISO 8601 dates (`## [1.2.0] - 2026-08-25`);
`[YANKED]` for withdrawn releases; bottom reference links against compare URLs
(`[1.2.0]: https://github.com/o/r/compare/v1.1.0...v1.2.0`, `[unreleased]: …/compare/v1.2.0...HEAD`);
and state whether the project follows SemVer.

Guiding principles worth keeping in the header comment: changelogs are "for humans not machines", an
entry for every version, same-type changes grouped, versions and sections linkable.

Source: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

---

## 3. Semantic Versioning

`MAJOR.MINOR.PATCH`, non-negative integers, no leading zeroes. A project using SemVer **must declare
a public API**.

The rule most new repos get wrong: **`0.y.z` is for initial development — "Anything MAY change at any
time. The public API SHOULD NOT be considered stable."** `1.0.0` is what defines the public API.
Scaffold at `0.1.0` and say so in the README status line.

Pre-release identifiers are hyphen-separated and lower-precedence than the release
(`1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0-rc.1 < 1.0.0`). Build metadata
after `+` is **ignored in precedence**.

Source: [semver.org](https://semver.org/)

---

## 4. Conventional Commits

```
<type>[optional scope][optional !]: <description>

[optional body]

[optional footer(s)]
```

`feat` must be used for features and `fix` for bug fixes. Scope is a noun in parentheses. Breaking
changes are signalled by `!` before the colon or a `BREAKING CHANGE:` footer — **uppercase is
mandatory**; `BREAKING-CHANGE` is synonymous. Footer tokens use `-` for whitespace (`Acked-by`).

Bump mapping: `fix:` → PATCH, `feat:` → MINOR, breaking → MAJOR. Other types carry no implicit
version effect.

The commitlint conventional type list: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`,
`refactor`, `revert`, `style`, `test`. Config file `commitlint.config.js`.

**Traceability use:** `feat(FR-001): add email validation` is legal, because a scope is "a noun
describing a section of the codebase". See `traceability_scheme.md`.

Sources: [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) ·
[commitlint config-conventional](https://github.com/conventional-changelog/commitlint/blob/master/%40commitlint/config-conventional/README.md)

---

## 5. Code of conduct

**Default to the pointer form.** In the survey, most repos with a CoC ship a 2–4 line file pointing
at an org or foundation CoC rather than inlining thousands of words.

If inlining, use the current Contributor Covenant. Its structure is Our Pledge · Encouraged Behaviors
· Restricted Behaviors · Other Restrictions · Reporting an Issue · Addressing and Repairing Harm ·
Scope · Attribution, with a four-tier enforcement ladder (Warning → Temporarily Limited Activities →
Temporary Suspension → Permanent Ban), each tier carrying Event / Consequence / **Repair**. The ladder
is explicitly "intended as a guideline".

**Two placeholders must be filled or the file is broken:** the reporting-contact placeholder in
"Reporting an Issue", and the editorial NOTE in "Addressing and Repairing Harm". `validate_repo.py`
fails on either remaining.

The newer Covenant differs from 2.1 in ways worth knowing when a reviewer asks: usable by non-software
communities, "Community Moderators" replaces "Project Maintainers", restorative rather than
retributive framing, Our Standards split into Encouraged/Restricted, and the pledge broadened.

Alternatives: Django's (Covenant plus impact-over-intent, sea-lioning/brigading/tone-policing, and
responsibility for AI-generated content), Rust's (Covenant-derived with a separate moderation policy),
Ubuntu's (value-principles plus leadership structure). Avoid Citizen Code of Conduct — effectively
unmaintained, and its canonical domain no longer resolves.

Sources: [Contributor Covenant 3.0](https://www.contributor-covenant.org/version/3/0/code_of_conduct/) ·
[Contributor Covenant repo](https://github.com/EthicalSource/contributor_covenant) ·
[Covenant FAQ](https://www.contributor-covenant.org/faq/) ·
[adding a code of conduct](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/adding-a-code-of-conduct-to-your-project) ·
[Django CoC](https://www.djangoproject.com/conduct/) ·
[Rust CoC](https://www.rust-lang.org/policies/code-of-conduct)

---

## 6. Licensing

Emit a `LICENSE` file plus the SPDX identifier in `package.json` and the README.

| License | One-line distinction |
|---|---|
| MIT | Permissive; the only condition is preserving the copyright/license notice |
| Apache-2.0 | Permissive **plus an express patent grant**; requires preserving notices and **stating changes**; no trademark rights |
| BSD-3-Clause | Like MIT plus a no-endorsement clause |
| MPL-2.0 | **File-level** copyleft; new files are not Modifications |
| AGPL-3.0 | Strong copyleft where **network use counts as distribution** |

**Apache-2.0 costs more than a file.** Redistributors must supply the license, **mark modified
files**, retain notices, and include a readable copy of any NOTICE attribution notices. If choosing
Apache-2.0, also emit `NOTICE` and per-file headers — either the full boilerplate or the short
`SPDX-License-Identifier: Apache-2.0`.

**Per-file SPDX tags** are one comment line containing the exact token `SPDX-License-Identifier:`
followed by an identifier or expression. Expressions support `AND`/`OR`/`WITH` and parentheses; `OR`
means recipient choice, which is how dual licensing is expressed. GNU licenses must use
`-only`/`-or-later` rather than `+`.

**REUSE compliance** (optional, for full machine-readable licensing): every license needs a plain-text
copy in a root `LICENSES/` directory named `<SPDX-ID>.txt`, and that directory must contain nothing
else; every covered file carries `SPDX-FileCopyrightText:` and `SPDX-License-Identifier:` headers;
uncommentable files get an adjacent `<file>.license`; `REUSE.toml` is the bulk mechanism and
`.reuse/dep5` is deprecated. Verify with `reuse lint`.

**SBOM:** GitHub exports SPDX from Insights → Dependency graph → Export SBOM, and via REST. CycloneDX
is the alternative format. Offer SBOM generation in the release workflow rather than by default.

Sources: [choosealicense](https://choosealicense.com/) ·
[license list](https://choosealicense.com/licenses/) ·
[SPDX license list](https://spdx.org/licenses/) ·
[SPDX handling license info](https://spdx.dev/learn/handling-license-info/) ·
[Apache-2.0 text](https://www.apache.org/licenses/LICENSE-2.0) ·
[ASF license FAQ](https://www.apache.org/foundation/license-faq.html) ·
[MPL 2.0 FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/) ·
[REUSE spec](https://reuse.software/spec/) ·
[reuse-tool](https://github.com/fsfe/reuse-tool) ·
[GitHub SBOM export](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/exporting-a-software-bill-of-materials-for-your-repository) ·
[CycloneDX](https://cyclonedx.org/specification/overview/)

---

## 7. Contribution licensing — DCO or CLA

Default: **neither**, because the license is both inbound and outbound and GitHub's terms make
"inbound = outbound" the explicit default.

Add a **DCO** when maintainers want a per-commit authorization representation. It requires a
`Signed-off-by:` line matching the author email (`git commit -s`), enforced by the DCO GitHub App,
and requires a **real name** — "not necessarily legal or passport, but the name you're known by".
Node.js switched from a CLA to a DCO.

Add a **CLA** only when you need an express patent grant under MIT, dual-license commercially, or may
need to relicense later. It adds administrative overhead and "can read as unfriendly".

Sources: [developercertificate.org](https://developercertificate.org/) ·
[CNCF DCO guidelines](https://github.com/cncf/foundation/blob/main/dco-guidelines.md) ·
[Open Source Guides: legal](https://opensource.guide/legal/)

---

## 8. CONTRIBUTING.md content

The most complete published checklist is CNCF's. Sections: Introduction · Ways to Contribute ·
Meetings · Find an Issue (`good first issue` / `help wanted`, and how to claim one) · Ask for Help ·
**Pull Request Lifecycle** (when to open, ready vs WIP signals, review timelines, ping etiquette,
stalled PRs, preferred size, closing for inactivity, when a merged PR ships) · **Development
Environment Setup** — the test is that someone can "set up, build, test and submit without asking" ·
**Pull Request Checklist** mirrored in the PR template, naming a single local command such as
`pnpm check`.

Add the TDD rule here (see `document_spine.md` §7) and the Conventional Commits format. Governance
templates (`GOVERNANCE.md`, `MAINTAINERS.md`, contributor ladder) exist but are for projects with
real multi-maintainer structure — 1 of 14 surveyed repos has GOVERNANCE.md. Leave them out by default.

Sources: [CNCF contributing guide howto](https://contribute.cncf.io/maintainers/templates/contributing/) ·
[CNCF project templates](https://contribute.cncf.io/projects/best-practices/templates/) ·
[cncf/project-template](https://github.com/cncf/project-template)

---

## 9. README

GitHub renders the README from `.github/` → root → `docs/` and truncates beyond 500 KiB.

Use **relative links** — "Absolute links may not work in clones of your repository"; a leading `/` is
relative to the repo root and link text must be on one line. GitHub auto-generates a table of
contents from headings via the Outline menu, so do not hand-maintain one below ~100 lines. Alerts are
`> [!NOTE|TIP|IMPORTANT|WARNING|CAUTION]`, limited to "one or two per article", and cannot be nested
or consecutive. Mermaid renders in fenced `mermaid` blocks.

standard-readme's required order, if following it strictly: Title · Banner · Badges · Short
Description (under 120 chars, own line, matching the package and GitHub descriptions) · Long
Description · Table of Contents · Security · Background · **Install** · **Usage** · Extra Sections ·
API · Maintainers · Thanks · **Contributing** · **License (must be last)**.

**The evidence-backed addition most READMEs omit is a purpose statement and a project status line.** A
study of 4,226 README sections across 393 repositories found "What" and "How" content very common
while many READMEs **lack purpose and status information**. Put both in the template.

Badges: shields.io, newline-delimited. Keep to CI status, license and package version. README length
in the survey ranged 30× — from 38 lines to 912 — so emit the short form and let it grow.

Sources: [about READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) ·
[basic writing and formatting syntax](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax) ·
[standard-readme spec](https://github.com/RichardLitt/standard-readme/blob/main/spec.md) ·
[shields.io badges](https://shields.io/badges) ·
[Categorizing the Content of GitHub README Files](https://arxiv.org/abs/1802.06997)
