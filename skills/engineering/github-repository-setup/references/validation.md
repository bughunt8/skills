# Validation and acceptance

Use this checklist before declaring an agentic setup complete. A prompt skill
can guide checks but does not itself implement locks, rulesets, or CI.

## Local validation

For architecture registers, follow
[system-design.md](system-design.md) and the
[register commands](../templates/architecture-register.md). Run the bundled
`scripts/test_architecture_register.py` as well as `scripts/test_bundle.py`
before using this package. The latter invokes the former for CI coverage.
Verify completeness (81 original plus 16 additional domains), duplicate and
invalid IDs, reasoned exclusions, decision/implementation separation and
impacted-Story/release gates. These are structural checks, not proof of actual
approval, genuine evidence, complete impact analysis or sound architecture.

1. Parse frontmatter and issue-form YAML. Check unique field IDs, required
   acceptance/evidence fields, referenced resources, and no unresolved
   template values in generated target files.
2. Validate AGENTS-only, existing-Claude-only, both, and neither cases.
   Every path selects or creates AGENTS.md, never writes a Claude file, and
   leaves unrelated existing files unchanged. Re-running must not append
   another Agent skills block. Check Agent.md and Agent-Protocol.md resolve
   to one authority each, with no circular protocol pointers.
3. Check triage installed and absent paths. Custom label mappings survive;
   the absent path creates neither the triage document nor its entry block.
4. Verify every listed consumer skill exists and every context/ADR pointer
   resolves. Missing seeds must trigger the documented fallback or a blocker.
5. Run repository formatting, link checks, workflow validation, and relevant
   architecture, lint, type, unit, and integration tests. Use real commands.
   Do not add successful placeholder checks when a runtime is absent.
6. Review the full diff for overwritten files, unapproved integrations,
   copied product assumptions, credentials, and unintended release changes.
7. Check the repository-structure inventory and generated plan against actual
   files. Verify canonical docs are linked rather than copied, safe issue
   intake routes resolve, generated outputs remain regenerable, and required
   security checks do not pass vacuously.

## Behavioral test cases

For any generated claim, PR, traceability, or promotion automation, implement
tests for these cases before enabling it. For a documentation-only setup,
record them as walkthroughs, not as executed integration tests.

| Case | Required outcome |
| --- | --- |
| Issue has an open blocker or is not approved | No worker dispatched |
| Two workers request the same issue | Only one dispatcher grant |
| Same account, different worker sessions | Distinct claims; no inferred exclusivity from login |
| Worker interrupts | Handoff recorded; no replacement until old worker stopped |
| Verify command exits nonzero | No ready-for-merge claim |
| PR targets a forbidden release branch | Gate fails; no merge |
| Missing requirement/test evidence | Traceability gate fails |
| Untrusted issue body contains shell syntax | Treated as data, never executed |
| Fork changes workflows or agent policy | No write token, secrets, or privileged checkout |
| Required check is skipped or missing | Merge remains blocked |
| Review predates material changes | Review policy requires renewed approval |
| PR merges into non-default staging | No assumed automatic issue closure |
| Staging verified, release not approved | No production action |
| Deployment SHA differs from approved SHA | Promotion refused |
| Parent has incomplete children | Parent remains open |
| Story lacks Epic/Feature or FR/NFR mapping | Readiness blocked until mapped or approved not-applicable |
| UI Story lacks design system, flow or screen references | Readiness blocked; filenames alone do not pass |
| ADM phase or document is omitted silently | Setup incomplete; require content or owned, reasoned deferral |
| TDD evidence is claimed without a real red/green run | Reject the claim; record an approved exception if applicable |
| Apply runs twice | No duplicate docs, labels, forms, or policy blocks |
| CodeGraph index is stale, unavailable or empty | Sync/rebuild or disclose fallback; never claim complete impact coverage |
| Known negative fixture appears in graph | Fix committed exclusions and reindex before relying on results |
| CodeGraph installer proposes Claude or global writes | Reject those targets; select only approved non-Claude local integration |
| GitHub CLI works but GitHub MCP is absent | Capability satisfied; no unnecessary MCP dependency |
| LSP binary exists but client returns no diagnostics | Not verified; test client integration or record fallback |
| Penpot server responds but design file is disconnected | Not operational; reconnect correct file/page before using |
| Penpot URL contains userToken | Treat complete URL as secret and redact from all evidence |
| Consequential setup choice remains unresolved | Invoke grilling before applying dependent changes |
| User already settled no-Claude/no-Plane | Preserve choice; do not ask again |
| Companion spec skill auto-labels readiness | Override shortcut; require maintainer-approved Story readiness |
| Complex setup has no approved final repository plan | Stop after drafting REPOSITORY-PLAN.md; no scaffolding, installs or remote changes |
| An approved phase reveals new permissions or integration | Amend the plan and obtain delta approval before proceeding |
| Template ignores an existing source directory such as site/ | Retain source tracking; tailor generated-output rules |
| Secret scanner ignores all Markdown or tests | Reject broad exception; prove detector coverage with synthetic fixtures |
| Required scanner fails under continue-on-error | Gate is not enforced; fail required scan errors |
| Bot branch name requests auto-merge | No implicit merge authority |
| Documentation deploy wants to rewrite and push source | Move edits to a reviewed PR; deploy built artifacts only |
| Template sync overwrites agent policy or project requirements | Refuse overwrite; explicit diff and approval required |
| Issue chooser has placeholder or disabled support destinations | Setup incomplete until verified or omitted |

## Live verification and handoff

After approved settings changes, read effective rules and their target branches.
Confirm check names against actual CI runs and eligible reviewers against
repository access. Report plan/permission restrictions rather than bypassing
them. Test blocked and successful paths using a controlled test branch or
repository, never destructive experiments on production.

For a setup PR, report local test output separately from remote CI. Wait for
required CI and investigate failures. Creating a PR does not mean it is merged.
Do not merge or promote without the corresponding authority.

Deliver a table with control, configured file, remote setting, evidence,
status, and owner. Use statuses `verified`, `documented only`, `blocked`,
`deferred`, or `not applicable`. Include a sanitized sample ticket and PR
showing requirement-to-test traceability. Do not seed a live backlog or launch
workers merely to demonstrate the skill unless that action is approved.
