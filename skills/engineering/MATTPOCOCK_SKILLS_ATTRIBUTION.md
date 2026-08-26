# mattpocock/skills attribution

Skills in this repository derive from [mattpocock/skills](https://github.com/mattpocock/skills),
at commit
[`6654f6b`](https://github.com/mattpocock/skills/tree/6654f6b60cd9d5be8b54c6fafe44346dabeb3b76).

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

## Derived skills

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
the tree fall out of step. This import is not yet under the automated refresh in
[`skills/vendor.manifest.json`](../vendor.manifest.json); migrating it is item 5 of the backlog
in [`docs/ARCHITECTURE_REVIEW.md`](../../docs/ARCHITECTURE_REVIEW.md).
