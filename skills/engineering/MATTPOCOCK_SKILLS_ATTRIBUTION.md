# mattpocock/skills attribution

Historical imports and remaining local derivatives derive from
[mattpocock/skills](https://github.com/mattpocock/skills).
An earlier record used the common pin
[`6654f6b`](https://github.com/mattpocock/skills/tree/6654f6b60cd9d5be8b54c6fafe44346dabeb3b76),
but the migration audit found that most old native bodies match other historical
commits. The originating pins of the locally extended `caveman` and
`write-a-skill` remain unresolved, not verified at that common pin.
See the [migration audit](../../docs/migrations/matt-v1.3.1/dependency-audit.md)
for exact body matches and source URLs.

The 27 stable v1.3.1 skills now use per-directory importer-generated attribution,
MIT copies and provenance at
[`24fe0ef`](https://github.com/mattpocock/skills/tree/24fe0ef7737efae15c87225755e9f6f5965e4888).
This historical notice remains with the preserved local derivatives and legacy
archives; it does not override those managed records.

- **Original author:** Matt Pocock ([@mattpocock](https://github.com/mattpocock))
- **Original copyright:** Copyright (c) 2026 Matt Pocock
- **Original licence:** MIT, reproduced verbatim in
  [MATTPOCOCK_SKILLS_LICENSE](MATTPOCOCK_SKILLS_LICENSE)

## Why this file exists

Several skills below state in their own text that Matt Pocock's content, voice or workflow is
"preserved verbatim" under MIT. `skills/engineering/caveman` says "Matt's voice preserved
verbatim". `skills/engineering/write-a-skill` says "Matt's voice and 3-phase workflow preserved
verbatim". Both declare `original_license: MIT` in frontmatter.

The MIT licence requires that its copyright notice and permission notice be included in all
copies or substantial portions of the software. Naming the author in prose and linking to their
repository is credit, and credit is good, but it is not that notice. No copy of the upstream
licence existed anywhere in this repository until an independent adversarial review of
[pull request #18](https://github.com/bughunt8/skills/pull/18) pointed it out. That was the most
serious licensing defect found, and this file plus
[MATTPOCOCK_SKILLS_LICENSE](MATTPOCOCK_SKILLS_LICENSE) is the correction.

## Historical derived-skill list

Under `skills/engineering/`:

- [`ask-matt`](ask-matt/)
- [`caveman`](caveman/)
- [`code-review`](code-review/)
- [`grill-with-docs`](grill-with-docs/)
- [`implement`](implement/)
- [`improve-codebase-architecture`](improve-codebase-architecture/)
- [`setup-matt-pocock-skills`](setup-matt-pocock-skills/)
- [`to-spec`](to-spec/)
- [`to-tickets`](to-tickets/)
- [`triage`](triage/)
- [`wayfinder`](wayfinder/)
- [`write-a-skill`](write-a-skill/)

Under `skills/productivity/`:

- `grill-me`
- `grilling`
- `handoff`
- `to-questionnaire`
- `wait-what`
- `writing-for-agents`

Several of these are derivative rather than verbatim: they keep the upstream voice and workflow
and add local tooling, references and wrappers. Each says so in its own header. The MIT licence
permits that. It still requires this notice.

## Scope of this record

This file covers the upstream copyright and permission notice, which is what MIT requires. It
does not assert that every skill listed is a byte-for-byte copy, nor that the local additions
are Matt Pocock's work. They are not.

If any attribution here is wrong, or if the author would prefer these skills removed, open an
issue. Attribution reports are handled ahead of everything else in this repository.

## Tracking

Recorded as `mattpocock-skills` in
[`docs/third-party-inventory.json`](../../docs/third-party-inventory.json) and rendered into
[`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md).
[`scripts/audit_third_party.py`](../../scripts/audit_third_party.py) fails CI if this record and
the tree fall out of step. The stable suite is now managed through
[`skills/vendor.manifest.json`](../vendor.manifest.json). The legacy inventory
retains the two local derivatives and script-produced archives rather than
misrepresenting them as exact current-release imports.
