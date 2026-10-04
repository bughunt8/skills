# Review and approval protocol

## Claims

`lint` is structural. It checks section/table presence, per-row EARS syntax, ID references, coverage, dependency cycles, path safety, test markers where requested, and a limited implementation-detail heuristic. It cannot establish requirements quality, assertion correctness, real test execution, code compliance, security, or deterministic generation.

`analyze` records the reviewer's claims and content hashes. It is not a semantic analysis engine. `gate` checks fail-closed conditions against those local records, then selects at most one dependency-ready task or reports post-build structural review. JSON with `"authority": "human"` is not identity authentication. Before using it, confirm that the named human really authorized this reviewed state through the project's trusted approval channel. Never create approval on that person's behalf.

The checker assumes a trusted local filesystem and trusted installed skill scripts. It strictly rejects symlink components and multiply hardlinked checked files, including otherwise legitimate cp-al checkouts or linked package-store files. Use regular independent files rather than weakening those guards. It also rejects unsafe paths, overwrite attempts, and malformed feature IDs. It is not a sandbox against concurrent hostile writers, a signing system, or a tamper-proof storage service. Use protected PR review or signed external records where identity or storage integrity needs stronger enforcement.

## Manual review input

Copy the shape of [review.example.json](../examples/minimal/review.example.json), replacing the illustrative assessments with actual review results. It contains:

- `reviewer`, timezone-aware `reviewed_at`, and `phase`, either `pre-build` or `post-build`. Post-build also sets `task` to the reviewed task. Timestamps more than five minutes in the future fail.
- `base` identifies the reviewed baseline, such as a git commit, plus how it was established. `diff` describes compared range/worktree and relevant added/deleted/untracked files. For a new project, say there is no prior implementation and name the initial baseline honestly.
- `summary` states findings and limitations. `blockers` is a list; any nonempty list prevents analysis recording.
- `checks` has exactly scope, ears, traceability, contracts, security_positive, security_negative, tests, observability, simplicity, drift, ui. Each is a substantive assessment, not `true`, `pass`, or generic approval. Only contracts, observability, and ui may use a reasoned `N/A:`.
- Pre-build `scope_files` lists all task-owned implementation/tests plus other relevant changed code/config. Post-build includes only selected and completed tasks' owned files, not unstarted future files. Add other relevant changed files. Hashes bind bytes as present or explicitly missing before build. `implementation_files` is a nonempty subset. Humans inspect diff completeness, including new/deleted/untracked files.
- `evidence` lists existing project-relative evidence files. Add actual command logs, contract/integration test results, browser screenshots and keyboard records for applicable post-build work. Execution-log evidence is also included automatically in hash freshness.

Pre-build review may assess planned tests and design contracts without claiming execution or actual-code compliance. This allows real TDD to start later without a readiness deadlock. Post-build review requires selected task code/tests, named test declarations, and distinct Red/Green/Refactor evidence; it still needs human inspection and actual execution evidence.

Run `analyze --review <review-path>` only after appending blocked findings and resolving material contradictions with the human. A successful record creates `reviews/analysis-<content-id>.json` exclusively and appends CROSS_ANALYSIS. Existing identical analysis is refused, not overwritten. Never erase old failures or contradictions to make a gate pass. Record the chosen fix, owner, evidence, and resolution status in CROSS_ANALYSIS.

## Human authorization record

The named human authorizer creates a new immutable approval JSON in a trusted process after reviewing the exact analysis. An agent can explain this schema and calculate hashes but cannot fabricate approval. Preserve prior approval files unchanged; never refresh a timestamp or hash to rescue stale approval.

```json
{
  "decision": "approved",
  "authority": "human",
  "authorizer": "actual authorized human identity",
  "statement": "actual scope and limits authorized by this human",
  "approved_at": "timezone-aware ISO8601 timestamp",
  "analysis": ".specs/reviews/analysis-content-id.json",
  "snapshot": "the analysis snapshot hash",
  "analysis_hash": "SHA256 of that exact analysis file",
  "cross_analysis_hash": "SHA256 of the reviewed CROSS_ANALYSIS file",
  "task": "TASK-1",
  "completed": {}
}
```

This explanatory JSON is not runnable authorization and its placeholders deliberately fail validation. The checker has no `approve` or automatic authorizer command. The authorizer's actual statement should identify verified phase approvals, the selected task, and any prerequisite module readiness. A pre-build approval authorizes exactly its `task`; a different requested task is rejected.

For previously completed tasks, `completed` maps each task ID to `{"path": "evidence/task-1-verified.txt", "sha256": "verification file SHA256", "analysis": ".specs/reviews/analysis-<id>.json", "analysis_hash": "post-build analysis file SHA256"}`. TASKS marks that task completed and references the same verification file with distinct Red, Green, Refactor, and Verification evidence paths. The task-specific post-build analysis binds current owned code/tests, Red/Green/Refactor evidence, and a normalized hash of the full task definition row. Changing Files, Tests, Depends, Verify, Cwd, Exit, Done, or ID references invalidates that receipt even when execution-log progress is allowed. The checker requires complete predecessor evidence and rejects a map disagreeing with TASKS. Humans determine whether evidence is truthful.

Use pre-build analysis with `gate --purpose build --task TASK-1` and post-build analysis with `gate --purpose verify --task TASK-1`. The latter reports reviewed structure and execution evidence paths, not semantic implementation completion. The gate rejects missing authority, stale specs/mappings/contracts, changed review evidence/code/tests or expected missing files, edited analysis, absent/changed CROSS_ANALYSIS, approval hash mismatch, wrong phase, and incomplete dependencies.

## Freshness and stopping

Snapshots hash whole authoritative files and shared contract files plus INDEX/CAPABILITY_MAP when present. Completed predecessor reviews allow later TASKS log updates, but require other authoritative docs, predecessor code/tests, and execution evidence to remain fresh. Review records bind reviewed code/test scope and evidence. Approval binds analysis bytes and CROSS_ANALYSIS bytes. Binary evidence such as PNG screenshots is hashed by bytes, limited to 20 MB per file. Changes outside declared scope are not detected; humans must compare actual diff scope and choose reviewed paths.

Adding an analysis entry or a new contradiction changes CROSS_ANALYSIS, so prior authorization becomes stale. Update TASKS only with genuine task results, then obtain a fresh review/authorization for the next task. Do not auto-edit approved documents to match code. A material contradiction always halts for user choice.

If a later task changes a file also owned by a completed predecessor, the predecessor's receipt becomes stale. Recovery requires rerunning its relevant tests, a fresh task-specific post-build review against the new shared file, and renewed human verification recorded in a new verification evidence file. Update its receipt and obtain fresh downstream authorization. Do not automatically reuse old verification just because the earlier tests or file name are unchanged. Local hashes cannot authenticate whether a human actually reverified the behavior.

Earlier `/constitution`, `/spec`, `/plan`, `/tasks`, and CAPABILITY_MAP approvals remain trusted human-channel requirements. The checker enforces only the final build/verify record, not those earlier decisions. Reviewer and authorizer equality requires a recorded `self_review_policy`, but local text cannot authenticate either identity.

The tests simulate approval records to prove positive/negative gate behavior. They are labelled test fixtures, live only in test temporary projects, and cannot authorize real work. The supplied green example has no real approval or Red-Green-Refactor history.
