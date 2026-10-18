- **NFR-007:** Maintenance automation MUST remain review-gated and MUST NOT merge its own PRs.
- **FR-008a:** Every maintenance workflow, including vendored refresh, site refresh, public
  intake, deletion, and production cleanup, MUST be prohibited from auto-merging its PR. A
  maintainer or code owner must perform the merge after review.
# Product requirements: semantic skill data maintenance

## Purpose and scope

This document declares the product requirements for maintaining the skill library as a
reproducible, semantically trustworthy data product. It governs how skills and their
attributions enter, change, and leave the repository, how semantic meaning and relationships
are recorded, and how the generated site data is rebuilt and promoted.

This PRD is normative for semantic metadata, source reconciliation, attribution and
provenance maintenance, deletion handling, relationship generation, documentation updates,
and staging or production rollout. `site/data.js`, rendered pages, README indexes,
attribution documents, and retention archives are derived outputs. They are never sources of
truth.

The current repository facts and operational commands remain in `README.md`,
`CONTRIBUTING.md`, `AGENTS.md`, `site/README.md`, and `site/DEPLOYMENT.md`. This document
defines the product contract those operational documents implement.

## Problem and context

The library combines locally authored skills, vendored collections, and pinned external site
sources. Existing category assignments mainly reflect directory layout. Existing graph
communities also use lexical similarity, so generic words such as `audit`, `ISO`,
`compliance`, and `security` can look like semantic relationships when they are not.

The repository already has separate maintenance paths for vendored sources and site sources.
The product requirement is one comprehensive, repeatable reconciliation outcome: every
discovered skill has valid provenance and reviewed semantics, every asserted relationship has
evidence, deletions are explicit and auditable, and generated data is reproducible.

## Goals

- Establish a strict semantic layer independent of directory names and inferred communities.
- Reconcile additions, updates, local deletions, upstream deletions, attribution, provenance,
  relationships, documentation, and generated site data in one idempotent process.
- Make public repository intake repeatable and reviewable through GitHub Actions.
- Preserve complete, source-bounded production snapshots when staging applies deletions first.
- Make stale, missing, ambiguous, malformed, or orphaned state fail closed.
- Keep staging deletion-complete while allowing production to defer deletions through an
  explicit generated retention overlay and later approved cleanup.

## Non-goals

- This PRD does not authorize production deployment during the initial implementation.
- It does not create an external database or hosting service.
- It does not treat keywords, folder names, or Louvain communities as semantic authority.
- It does not automatically merge externally sourced content or unreviewed semantic judgments.
- It does not delete a skill merely because a parser failed to find it.

## Users and stakeholders

- **Maintainer:** owns source acceptance, semantic review, deletion approval, and release safety.
- **Skill author:** supplies or updates public source material and explanatory context.
- **Maintenance automation:** discovers, validates, reconciles, generates, reports, and opens
  review pull requests. It never merges them.
- **Site visitor:** consumes the generated skill cards, search data, and explicitly labelled
  discovery relationships.

## User stories

- **US1:** As a maintainer, I can refresh an attributed source and receive one review PR that
  shows source changes, semantic changes, relationship changes, attribution changes, and
  generated output changes.
- **US2:** As a user, I can submit a public Git repository URL and an explicit subpath, after
  which automation proposes a complete, validated staging PR without merging it.
- **US3:** As a maintainer, I can intentionally delete a skill with a durable tombstone and
  see every derived consequence before staging deploys it.
- **US4:** As a maintainer, I can review deferred production deletions and approve a separate
  cleanup PR with evidence that remote files were removed.
- **US5:** As a visitor, I can distinguish evidence-backed semantic relationships from
  non-semantic discovery similarity.

## Functional requirements

- **FR-001:** The system MUST maintain one versioned repository-owned `site/semantics.json`
  record for every recursively discovered `SKILL.md` inside each approved source boundary.
- **FR-002:** Each semantic record MUST contain identity, source path, provenance, purpose,
  orthogonal facets for object, activity, lifecycle stage, framework, and audience, evidence
  with content hashes, and explicit relationships.
- **FR-003:** The semantic registry MUST have exact key parity with discovered live skill
  identities. Missing, duplicate, stale, orphaned, malformed, ambiguous, or unsupported
  records MUST fail validation.
- **FR-004:** Asserted relationships MUST be explicitly declared, target a valid identity,
  name a relationship type, and cite validated source evidence with its hash. Shared facets
  alone MUST NOT create asserted edges.
- **FR-005:** Lexical or similarity relationships MAY exist only in a separate labelled
  discovery layer. They MUST NOT affect taxonomy, semantic edges, deletion, attribution,
  retention, or release decisions.
- **FR-006:** Public intake MUST accept public Git repository URLs and an explicit starting
  subpath only. Discovery MUST recurse within that boundary and inspect relevant `README.md`
  files for collection context without expanding the import boundary.
- **FR-007:** Intake and maintenance automation MUST generate candidate semantics, but a
  repository maintainer or code owner MUST approve the reviewed semantic registry before its
  PR can merge.
- **FR-008:** Every source refresh, public intake, local deletion, and upstream deletion MUST
  use the same idempotent reconciliation contract and MUST open a review PR rather than merge.
- **FR-009:** Local and upstream skill deletion MUST require a permanent `.DELETED.json`
  tombstone at the former skill path. The tombstone MUST include schema version, skill name,
  canonical identity, former path, source repository and commit, date, reason, approver, and
  evidence.
- **FR-010:** A tombstone MUST block silent reintroduction at the same path. Reinstatement
  requires an explicit reviewed decision.
- **FR-011:** Empty skill-owned directories MAY be removed only after ownership and live-file
  checks pass. Unexpected content MUST fail closed.
- **FR-012:** Staging MUST apply approved deletions and deploy the reconciled result. Production
  promotion MUST defer deletions to a separate explicitly approved cleanup PR or workflow.
- **FR-013:** Production retention MUST be generated from approved tombstones not yet cleaned
  up in production. It MUST contain a complete last-approved, source-bounded skill snapshot,
  semantic record, licence, attribution, and referenced support files.
- **FR-014:** Production cleanup MUST use a `.PRODUCTION-CLEANUP.json` approval record beside
  the tombstone, regenerate and verify production artifacts, remove corresponding remote
  files, and record cleanup evidence.
- **FR-015:** The reconciler MUST update or validate provenance, attribution, folder structure,
  relationships, documentation, and generated `site/data.js` as one complete outcome.
- **FR-016:** Generated artifacts MUST be produced by scripts and MUST never be hand-edited.
- **FR-017:** Any mismatch in source pins, ownership, licence, provenance, semantic records,
  relationship endpoints, references, generated output, or cleanup state MUST block the PR.

## Non-functional requirements

- **NFR-001:** Reconciliation MUST be deterministic and idempotent from committed inputs.
- **NFR-002:** Reconciliation MUST be atomic at the repository-output level: a failed run MUST
  not leave pins, ownership, snapshots, generated files, or documentation partially updated.
- **NFR-003:** Every maintenance run MUST produce an auditable report of additions, changes,
  deletions, retained snapshots, relationship changes, and validation results.
- **NFR-004:** The system MUST preserve source licences, authorship, commit pins, and bounded
  provenance for every published or retained skill.
- **NFR-005:** Maintenance workflows MUST run their complete validation suite before opening a
  `GITHUB_TOKEN` pull request, because that token-created PR may not trigger normal CI.
- **NFR-006:** The system MUST fail closed rather than infer an answer for missing or ambiguous
  semantic evidence.

## Source and lifecycle contract

The source registry identifies the repository and approved subpath. Recursive parsing discovers
all `SKILL.md` files within that boundary and reads relevant README context. A source refresh
compares the pinned revision with the prior revision. A new intake begins as a candidate PR.
An intentional deletion first captures the production snapshot, then adds the tombstone and
reconciles staging. An upstream deletion follows the same tombstone path after ownership is
verified. All paths recalculate semantic records, evidence-backed relationships, discovery
similarity, documentation, and generated output.

## Semantic model

Identity answers which skill is being described. Provenance answers where it came from and at
which commit. Purpose answers the outcome it supports. Facets describe object, activity,
lifecycle stage, framework, and audience independently. Evidence identifies the source path,
kind, and content hash. Relationships are typed assertions, not consequences of vocabulary.

The allowed asserted relationship types are `explicit_reference`, `declared_bundle`,
`solution_membership`, `shared_object`, and `shared_activity`, each requiring a declaration
and evidence. `discovery_similarity` is non-semantic and separate. In particular, sharing
`ISO 27001`, `audit`, or `compliance` does not connect two skills unless a source explicitly
declares the relationship and identifies its evidence.

## Intake, deletion, and release policy

Public intake accepts only a public Git repository URL and explicit subpath. Automation may
prepare a candidate, but one maintainer or code-owner approval is required before merge.

Deletion is explicit. A `.DELETED.json` tombstone remains permanently at the former skill path
and contains full evidence. A complete source-owned snapshot is generated before staging
removes the live skill. Staging deploys the deletion. Production promotion carries additions,
updates, semantic changes, relationship changes, and coherent generated data, while retaining
the deleted skill through a generated production retention manifest. A later cleanup PR uses
`.PRODUCTION-CLEANUP.json` and explicit approval to remove remote files and record proof.

## Success criteria and acceptance

- Every live discovered skill has exactly one valid reviewed semantic record.
- No asserted edge exists without a typed declaration and hashed evidence.
- ISO, audit, compliance, security, GDPR, AI governance, quality, and unrelated engineering
  audit counterexamples pass negative-linkage tests.
- Re-running reconciliation with unchanged inputs produces no diff.
- Adding, updating, deleting locally, and deleting upstream each produce the expected complete
  diff and no stale derived records.
- Generated `site/data.js` and documentation match the reconciled source state.
- Staging deploys the deletion-complete artifact and verifies the deployed revision.
- Production retention and cleanup are reproducible, approved, and evidenced.
- Existing repository, site, provenance, licence, link, solution, and browser checks remain
  green.

## Traceability

Implementation tasks MUST cite this PRD's requirement IDs. Tests MUST name the requirement they
prove. The eventual implementation plan owns the task breakdown and dependency edges; a later
technical design may own detailed interfaces without duplicating this product contract.

## Open questions

Any unresolved semantic evidence is a blocking condition, not a default. Schema migrations,
source-boundary exceptions, and reinstatement decisions require explicit maintainer review and
must be recorded in the relevant pull request.

## Change log

- 2026-09-14: Declared the semantic data layer and complete skill-library maintenance lifecycle.
