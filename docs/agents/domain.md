# Domain documentation

Engineering skills consume the project's glossary and ADRs while exploring a
codebase. Vocabulary is separate from behavioral specifications and technical
design.

## Before exploring

- Read root `GLOSSARY.md` if present.
- If root `GLOSSARY-MAP.md` exists, read the glossaries relevant to the topic.
- Read affected ADRs in `docs/adr/`, preserving established context-specific
  locations when a project has several bounded contexts.

Absent glossary or ADR files are not a setup failure. Proceed without inventing
content. Active `domain-modeling` creates terms and decisions lazily when they
actually resolve; reading vocabulary does not invoke that skill.

This repository uses a single-context convention, a future root `GLOSSARY.md`
and the existing ADR location. The upgrade changes consumer pointers only.
There was no root CONTEXT or GLOSSARY file to rename, and no domain map was
created.

## Naming migration

Matt v1.3.1 names domain vocabulary `GLOSSARY.md` and bounded-context maps
`GLOSSARY-MAP.md`. Inspect legacy `CONTEXT.md` or `CONTEXT-MAP.md` contents and
consumers before migrating an existing project. Rename only confirmed domain
files within approved scope, update consumers and preserve history.

Do not bulk-rename unrelated context documents. If both naming conventions have
maintained authorities, stop for the user's canonical-source choice rather than
merge or maintain two copies. A multi-context map requires actual multiple
bounded contexts, not merely a monorepo directory structure.

## Vocabulary and decisions

Use a defined domain term in issues, designs and tests rather than its rejected
synonyms. A missing term may indicate an unnecessary new concept or a genuine
gap to resolve through approved domain work.

Keep implementation constraints in TRD and ADRs. Keep behavioral EARS rules in
the canonical `.specs/` authority when that workflow is used. GitHub tickets and
PRD/design documents link to those rules instead of duplicating them.

Flag a conflict with an existing ADR explicitly and identify the decision to
reopen. Do not silently override it.

## Related governance

Read [invocation policy](../../.agents/invocation.md) for command reachability
and [the migration guide](../matt-pocock-v1.3.1.md) for sources and compatibility.
The policy path is plural `.agents/invocation.md`. This upgrade defines no
`GRAMMAR.md` file.
