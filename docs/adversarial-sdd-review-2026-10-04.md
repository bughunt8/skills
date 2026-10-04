# SDD candidate: final adversarial review (updated freeze)

- **Reviewer:** independent subagent. Read-only; no candidate edits, no remote writes.
- **Target:** `skill-candidates/sdd-20261004/spec-driven-development`.
- **Integrity:**
  - 37 files excluding caches; the file list matches the manifest exactly.
  - `sha256sum -c FREEZE.sha256` is all OK.
  - The manifest's own hash is `a9adf20571827b6a7f57b3ec5b127749f59c5601e43895df4d8e12712d4c48b5`, matching the parent's value.
- **Where tests ran:** all on copies under `/tmp/sddrev` (`final2/` for the frozen copy, `repo3/` for the repo-layout copy). Python 3.14.3.
- **Superseded:** the earlier version of this report covered freeze `58e87a55…`. That version's P1 test-evidence gap is now closed; see below.

## Verdict (bounded)

**Zero P1. Release-ready within the stated limits.**

- No behavioral P1 remains.
- The earlier test-evidence P1 is closed: the candidate's own suite (76 tests) now kills all 16 mutations that matter.
- Every earlier reproduction and every attack in the battery is blocked.
- The legitimate workflow passes end to end.
- The remaining items are P2 or explicitly accepted limits, and the docs state them honestly.

This verdict covers structural and gate behavior only. It does not claim:
- that the checker validates semantics, assertions, code correctness or human identity;
- that it enforces earlier phase approvals;
- that it detects changes outside the declared scope.

## Verification performed on this freeze

### 1. Suites and checks

**Suites:**
- Unit suite: **76 tests, OK**, run with a clean environment (`env PATH=/usr/bin:/bin`, `PYTHONDONTWRITEBYTECODE=1`).
- Example project tests: **4 tests, OK**.

**Example checks:**

| Check | Result |
| --- | --- |
| `lint --stage ready` | structural pass |
| `extract` (standalone) | `standalone-GWT` |
| `extract` in repo layout | `legacy-SpecParser` |

**README demo with physical temp path:** `scaffold` exits 0 and draft `lint --stage tasks` exits 2, both as documented.

**Commands never executed:** `sdd.py` has no subprocess, os.system or Popen use.

**Docs match the CLI:** the README `gate` examples include `--task` for both build and verify.

### 2. Targeted mutations (`/tmp/sddrev/targeted.py`)

Each mutation removes one guard. Guards are located by their error message, so line shifts don't matter. Line numbers below are in the frozen `sdd.py`.

**All 16 are killed by the candidate's own suite:**

| Line | Guard |
| --- | --- |
| 586 | Post-build scope excludes future-task files |
| 646 | Distinct Red/Green/Refactor evidence |
| 654 | Receipt analysis must be in the feature's `reviews/` |
| 656 | Receipt analysis hash |
| 661 | Receipt content and address integrity |
| 676 | Specs unchanged since the predecessor's post-build review |
| 679 | Predecessor code and tests unchanged |
| 683 | Predecessor execution evidence unchanged |
| 685 | Receipt's CROSS_ANALYSIS heading present |
| 761 | No re-authorizing an already-completed task |
| 464 | Task must list its invariant and observation tests |
| 470 | Files must include the task's test paths |
| 256 | Duplicate AC ID |
| 190 | Duplicate items in a list cell |
| 487 | Unknown execution status |
| 481 | Sparse Done text |

Per the parent's instruction, I did not repeat the full 118-guard sweep. The previous sweep's lower-value survivors (type and shape validation, and redundant guards such as the double `..` path check and the one-shall rule) are not release-relevant and remain as classified in the superseded report.

### 3. Attack battery (`/tmp/sddrev/battery.py`)

**The legitimate path passes**, and all 17 attacks are blocked:

| Attack | What it tries |
| --- | --- |
| `a_code` | Change predecessor code after its receipt |
| `a_redev` | Change predecessor Red evidence |
| `a_spec` | Change a spec after the receipt |
| `a_hash` | Wrong receipt analysis hash |
| `a_prebuild_receipt` | Use a pre-build analysis as the receipt |
| `a_outside_reviews` | Receipt analysis stored outside `reviews/` |
| `a_tampered_receipt` | Edit the receipt analysis file |
| `a_xa_missing` | Remove the receipt's CROSS_ANALYSIS heading |
| `a_already_completed` | Re-authorize a completed task |
| `a_dep_skip` | Skip a dependency |
| `a_task_mismatch` | `--task` differs from the approval |
| `a_verify_planned` | Post-build review of a planned task |
| `a_verify_no_task` | Post-build review naming no task |
| `a_same_rgr` | One file used as Red, Green and Refactor |
| `a_future_scope` | Future-task file in post-build scope |
| `a_verify_task_vs_review` | Verify approval task differs from the review's task |
| `a_bad_receipt_schema` | Receipt missing analysis fields |

### 4. Full lifecycle (`q1b.py`, `q2b.py`, `q5.py`)

**Passes:**
1. Build gate for TASK-1.
2. Task-scoped post-build review with TASK-2's tests still absent (no deadlock).
3. Binary PNG evidence.
4. Verify TASK-1.
5. TASK-1 receipt; build gate for TASK-2.
6. Post-build review and verify for TASK-2.

**Blocked, as intended:**
- changing the PNG makes the analysis stale;
- a mismatched `--task`;
- future-task scope;
- a pre-build receipt, or the old receipt format;
- changed predecessor code;
- an old TASK-1 receipt after TASK-2 changes a file both tasks own. Recovery through a fresh TASK-1 post-build review works.

**New P2-f fix verified:** editing a completed task's row in TASKS after its receipt gives "task definition changed since post-build review". Updating only the execution log is still allowed.

### 5. Earlier P2 probes (`q3b.py`, `q4.py`)

| Probe | Result |
| --- | --- |
| Privacy: `email,password`, `useremail`, `authorization`, `api_key`, `passwd`, `message_text` | Blocked |
| Privacy: `exclude=none` | Blocked |
| Privacy: negated policy wording | Blocked |
| Privacy: `email_hash` | Allowed (intended) |
| Plain unresolved open question | Blocked |
| `None:` followed by an open question | Blocked |
| What-not-how: Redis/REST, Postgres/gRPC | Blocked |
| What-not-how: "joins the waiting queue" (behavior wording) | Now passes |
| What-not-how: exclusion "No SQL" | Passes |
| Comment and prefix test names | Rejected |
| Nested, non-discoverable test functions | Rejected |
| Empty-body test functions | Accepted (explicit limit) |
| Heading injection into CROSS_ANALYSIS | Blocked (only the real `## Review <id>` heading appears) |
| Multiline reviewer field | Rejected |
| Hardlinked evidence | Rejected |
| Future timestamps | Rejected |
| Reviewer equals authorizer without `self_review_policy` | Rejected |
| Approval dated before its review | Rejected |

**Standalone and legacy parsers agree** on all five probe inputs:

| Input | Both modes |
| --- | --- |
| Normal | accept |
| Indented | accept |
| Single-word clauses | accept |
| And-continuations | accept |
| Reversed order | reject |

## Remaining P2 (non-blocking, bounded)

- **P2-r1 Renewed human verification is required by the docs only.** After a shared-file change, the checker accepts a fresh predecessor post-build review that reuses the *same* verification file. `review.md` L58 says renewed human verification in a *new* file is required, and it states plainly that local hashes cannot prove a human re-verified. That limit is honest.
  - Optional hardening: require the receipt's verification file to be newer than its post-build analysis, or not already bound in an earlier receipt.
- **P2-r2 Heuristics remain heuristics.** These are best-effort lexical checks, documented as such:
  - the sensitive field-name list for telemetry;
  - the "what not how" word list;
  - the AST-based test-name check.

## Accepted limitations (stated in SKILL, README, review and review-closure)

- Local approval JSON is not proof of who approved. Earlier phase approvals (constitution, spec, plan, tasks, capability map) are human-channel obligations; the checker enforces only the final build and verify records.
- Structural lint isn't semantic correctness. A declared test function, even with an empty body, proves nothing about assertions or execution; actual logs and human review are required.
- The EARS and "what not how" checks are lexical heuristics.
- Freshness hashes cover declared scope only, not undeclared repository changes.
- Strict rejection of symlinks and multiple hard links. Hardlinked checkouts are refused by design; macOS temp paths need the documented physical-path form.
- No formal-safety or deterministic-generation claim.

## Source and documentation consistency

- `references/source-analysis.md` cites all three sources with exact URLs:
  - Jaydoubleu: the LobeHub page and the GitHub tree
  - Zach Lloyd: the LinkedIn article and warpdotdev/common-skills
  - Addy Osmani: the GitHub `SKILL.md`
- Addy's "stop after the spec; approve in a later turn" rule matches the pinned snapshot `a06bc63`. I did not fetch the live page, per the no-external-tools constraint.
- The imported reference stays under `docs/reference-sources`, outside the skill-discovery root.
- Test and example approvals are labelled as simulated.

## Artifacts

All under `/tmp/sddrev`:

| Script | Purpose |
| --- | --- |
| `targeted.py` | Message-anchored mutation check |
| `battery.py` | Attack battery |
| `fixture3.py` | Fixture builder for this freeze |
| `q1b.py`, `q2b.py`, `q3b.py`, `q4.py`, `q5.py` | Lifecycle and P2 probes |

The earlier mutation harness and its outputs are in `/home/user/workspace`: `sdd_review_automut_harness.py` and `sdd_review_automut_final_frozen.txt` (the latter is for the superseded freeze).
