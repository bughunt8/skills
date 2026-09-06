# Traceability Scheme

Answers one decision: **how a requirement stays connected to its design, screen, task, test, commit
and issue — cheaply enough to survive contact with a real sprint.**

The failure mode being engineered against is the one Atlassian names directly: "Documentation can go
stale." Every element below exists so that staleness becomes a **build failure** rather than a quiet
rot.

---

## 1. Five ID families, assigned once, never renumbered

| Family | Format | Lives in | Assigned by |
|---|---|---|---|
| Functional requirement | `FR-001` | `PRD.md` §8 | whoever writes the PRD |
| Non-functional requirement | `NFR-001` | `PRD.md` §9, realised in `TRD.md` §7 | whoever writes the PRD |
| User story | `US1` | `PRD.md` §7 | whoever writes the PRD |
| Screen | `SCR-001` | `WIREFRAME.md` §2 | whoever writes the wireframes |
| Decision | `ADR-0001` | `docs/adr/0001-*.md` | whoever makes the decision |
| Task | `T001` | `specs/NNN-slug/tasks.md`, optional | task generator |

`FR-`, `US` and priorities `P1..P3` follow spec-kit's template conventions; `NFR-` is this template's
extension so the ISO/IEC 25010 block in the TRD has something to hang off. Requirements are phrased
`System MUST …`.

**Numbers are never reused, even after a requirement is deleted.** Mark it `[withdrawn]` in place. This
is the same discipline ADRs use — monotonic numbering with no reuse.

---

## 2. One matrix, in `TRD.md` §4

| Req ID | Requirement (MUST) | Design section | Screen | Task(s) | Test | Issue | Status |
|---|---|---|---|---|---|---|---|
| FR-001 | System MUST reject malformed email | TRD §6.2 | SCR-001 | T012, T014 | `test/auth/login.spec.ts › FR-001 rejects invalid email` | #123 | done |
| NFR-002 | p95 < 200 ms at 100 rps | TRD §7.1 | — | T031 | `test/perf/latency.spec.ts` | #145 | in progress |

One table. Not one per document, not a separate spreadsheet. `scripts/validate_docs.py` treats this
table as the join key for the whole spine.

---

## 3. Wiring — all standard mechanics, no bespoke tooling

**Test names carry the requirement ID**, so coverage maps to requirements without a second tool:

```ts
describe('FR-001 email validation', () => {
  it('rejects an address with no domain', () => { /* … */ });
});
```

**Commit scopes carry the ID.** Legal under Conventional Commits, where a scope is "a noun describing a
section of the codebase":

```
feat(FR-001): add email validation
fix(NFR-002): cache token verification to cut p95
```

**PR bodies close issues and cite the spec.** GitHub's closing keywords are `close`/`closes`/`closed`,
`fix`/`fixes`/`fixed`, `resolve`/`resolves`/`resolved`, and they work across repositories
(`Fixes owner/repo#100`):

```markdown
Closes #123

Implements: PRD.md#fr-001
Design: TRD.md#62-public-api--contracts
Decision: docs/adr/0007-use-durable-objects-for-session-state.md
```

**Coverage is the floor, not the proof.** Enforce with `coverage.thresholds` plus `perFile: true` so a
single well-tested file cannot mask an untested one.

Sources: [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) ·
[using keywords in issues and pull requests](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/using-keywords-in-issues-and-pull-requests) ·
[Vitest coverage config](https://vitest.dev/config/coverage) ·
[Atlassian PRD](https://www.atlassian.com/agile/product-management/requirements)

---

## 4. What `validate_docs.py` enforces

| Check | Failure means |
|---|---|
| Required headings present in PRD / TRD / WIREFRAME / DESIGN | Someone deleted a section instead of filling it |
| ID formats match `FR-\d{3}`, `NFR-\d{3}`, `SCR-\d{3}`, `T\d{3}`, `ADR-\d{4}` | Ad-hoc numbering has crept in |
| Every `FR-`/`NFR-` in the PRD appears in the TRD matrix | A requirement has no design |
| Every matrix row's Req ID exists in the PRD | The matrix references a deleted requirement |
| Every `SCR-` cited in the PRD exists in WIREFRAME §2 | A screen was referenced but never specified |
| Every `docs/adr/…` link in the TRD resolves | A decision link rotted |
| No `[NEEDS CLARIFICATION: …]` markers remain | An unresolved spec is being shipped |
| No unfilled `TODO`/`<!-- TODO -->` placeholders in generated docs | Scaffold output was never completed |

Wire it into `docs-check.yml` so a PR that breaks the chain fails before review.

`scripts/traceability.py` is the complementary direction: it scans PRD IDs, `describe()` names in
tests, and commit scopes, then reports **orphans both ways** — requirements with no test, and tests
citing IDs that no longer exist.

---

## 5. Optional: generated tasks and issues

If spec-kit interop is enabled, tasks come from `specs/NNN-slug/tasks.md` in the format
`[ID] [P?] [Story] Description`, where `[P]` marks tasks that "Can run in parallel (different files, no
dependencies)" and `[Story]` ties the task to `US1`/`US2`/`US3`. Task descriptions include exact file
paths. Test tasks carry the instruction "**Write these tests FIRST, ensure they FAIL before
implementation**".

Generate issues rather than hand-copying them (`/speckit.taskstoissues`), and run a cross-artifact
consistency gate before implementation (`/speckit.analyze`) and again at the end (`/speckit.converge`).
Amazon Kiro's equivalents are **Sync Files**, which "Creates new tasks that map to new requirements"
and "automatically marks completed tasks", and per-task validation against acceptance criteria.

Keep this off by default. Atlassian's warning applies to task lists too: "Don't track the user stories
that come from project requirements in one system and defects in another."

Sources: [spec-kit tasks-template.md](https://github.com/github/spec-kit/blob/main/templates/tasks-template.md) ·
[github/spec-kit](https://github.com/github/spec-kit) ·
[Kiro specs best practices](https://kiro.dev/docs/specs/best-practices/)

---

## 6. Keeping the documents honest

Three rules, each sourced, that together stop the spine becoming ceremony:

1. **Update the design doc while the system is unshipped** — "If the designed system hasn't shipped
   yet, then definitely update the doc." After shipping, add amendments rather than rewriting.
2. **ADRs are immutable; only status changes.** A reversed decision gets a new ADR that supersedes the
   old one, never an edit.
3. **Delegate rather than duplicate.** Any fact that lives in `package.json`, CONTRIBUTING or the PR
   template is *referenced* from the other documents, never copied — because "copied versions, rule
   lists, and counts become stale."

Sources: [Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/) ·
[log4brains](https://github.com/thomvaill/log4brains) ·
[Fowler, Architecture Decision Record](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html) ·
[cloudflare/workers-sdk AGENTS.md](https://github.com/cloudflare/workers-sdk/blob/main/AGENTS.md)
