## Ticket and outcome

Refs #ISSUE_NUMBER

<!-- Replace the example reference with a real issue.
For non-default-branch PRs, keep Refs and add a Development link where available.
Use Closes only when default-branch merge satisfies the agreed completion policy. -->

State the change, scope, and excluded work.

## Acceptance and traceability

Map each criterion to its requirement/ADR, changed files, test, and result.
Link follow-up issues for gaps. Do not mark incomplete criteria as passed.
Include Epic, Feature and Story IDs. For UI changes, link the UI/UX flow,
wireframe screen, and design-system tokens/components. Record affected
TOGAF ADM decisions and the TDD red/green evidence or approved exception.
List affected architecture coverage IDs, NFR thresholds and decision changes.
Separate accepted, implemented and verified status; link the reviewed impact
set and disclose unresolved/deferred dependencies instead of claiming readiness.

## Verification evidence

- Tested head SHA:
- Commands and exit codes:
- Actual output or sanitized durable artifact/run URL:
- Failure-case tests:
- NFR/load/security/recovery or AI-evaluation results, where applicable:
- Evidence environment and revision; stale evidence requiring renewal:
- Integration/deployment verification still required:

## Architecture and risk

State affected boundaries, security/data impact, ADR changes, migration risks,
and rollback steps. Use not applicable with a reason where appropriate.

## Independent review

- [ ] An independent reviewer examined the latest relevant revision.
- [ ] Blocking findings are resolved and affected tests rerun.
- [ ] Required CI checks pass; no self-approval or self-merge.
- [ ] Documentation, traceability, and follow-up tickets are current.

## Completion and release

State integration branch, agreed issue-closure boundary, and release owner.
This PR does not authorize production promotion.
