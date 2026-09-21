# Repository structure and maintenance baseline

Read while drafting the final target tree. This is a selective adoption of
the [ops4life repository-structure reference](https://ops4life.github.io/github-repo-template/reference/repository-structure/),
not an instruction to clone or enable that template. Keep the document,
agent, tool and approval contracts already defined by this skill.

## Plan the baseline

For each row record `retain`, `create`, `merge`, `defer`, or `not applicable`,
with destination, purpose, owner, verification and reason. Existing equivalent
files satisfy the requirement. Inspect contents; filename presence is not
proof the control works.

| Item | Required decision and acceptance |
| --- | --- |
| `.editorconfig` | Define encoding, final newline, line endings and project indentation; preserve Makefile tabs and intentional Markdown hard breaks |
| `.gitattributes` | Distinguish text/binary and required line endings; inspect archive/export effects and test representative files before normalizing existing history |
| `.gitignore` | Exclude local secrets, dependencies, generated output and CodeGraph indexes; never blanket-ignore source directories such as an existing `site/` |
| `.env.example` | If environment configuration exists, document variable names, purpose, required/optional status and safe placeholders; no usable credentials |
| `README.md` | Quick start, supported runtime, real commands, final structure map, document links, setup status and no-Claude policy |
| `CONTRIBUTING.md` | Issue intake, Epic/Feature/Story decomposition, branch/PR flow, tests, review and completion policy; choose one canonical location |
| `SECURITY.md` | Supported versions, private reporting route and response ownership; verify route before publishing, never send vulnerability details to public issues |
| `SUPPORT.md` and `CODE_OF_CONDUCT.md` | Select if community/customer contribution needs them; name actual support and conduct contacts |
| `LICENSE` and third-party notices | Confirm licensing and copyright ownership; retain inherited notices and provenance, never replace authorship with the GitHub owner automatically |
| `CHANGELOG.md` | Decide manual or generated ownership and release format; generated files name their generator and input rather than accept hand edits |
| `.github/CODEOWNERS` or existing equivalent | Use one effective file with valid owners for code, agent policy, workflows, security, design and docs; retain the review-enforcement distinction |
| `.github/ISSUE_TEMPLATE/` | Agent Story/Task form plus proportionate bug, feature and documentation intake; see the intake contract below |
| `.github/pull_request_template.md` | Reuse this skill's acceptance, traceability, evidence, independent review and release contract |
| `.github/dependabot.yml` or existing updater | Configure actual ecosystems/directories and cadence, including Actions; reviewed update PRs, not automatic merges |
| Existing lint/config files | Preserve the formatter and language toolchain; add YAML, Markdown, merge-conflict, case-conflict and large-file checks where useful |
| Secret scanner configuration | Preserve default detectors, scan docs and tests, and narrowly justify any false-positive exception |

Commit code and repeatable configuration, not machine state. Keep lockfiles
according to the selected ecosystem; do not generate npm, pnpm and Yarn locks
for the same workspace. Do not mandate `setup.py` alongside `pyproject.toml`
or add Python dependencies just because the reference uses MkDocs.

Use `.yml` or `.yaml` consistently with the existing repository. Preserve
canonical casing such as README.md, AGENTS.md, Agent.md and Agent-Protocol.md;
the reference's lowercase guidance is not a reason to rename these contracts.
Keep SVG reviewable as text unless there is a project-specific reason not to.

## Code, tests and operational directories

Select by architecture, not template volume:

- Single package/service: retain or create `src/`, `tests/`, and `scripts/`
  only where actual source, test or repeatable command content belongs.
- Monorepo: use the established `apps/` and `packages/` or equivalent;
  document dependency boundaries, ownership and workspace-specific commands.
- Infrastructure/deployment: add `infra/` or `deploy/` only for approved
  infrastructure; keep environment definitions separate from secret values.
- Containers, `compose.yaml`, Makefile/task runner and development containers
  are conditional. Reuse real build/test commands and do not add a second
  competing command interface.

Record outputs, exclusions and generated-file ownership in the plan.
Do not reorganize a mature repository merely for visual consistency.

## Documentation navigation

Use this navigation when the volume warrants it:

```text
docs/
  index.md                 # entry point and links to canonical root contracts
  getting-started/          # reproducible setup and first verified change
  guides/                  # task-oriented contribution, testing and release guides
  reference/               # repository map, configuration and tooling reference
  architecture/            # seams, diagrams and established ADR location
  agents/                  # tracker, domain, tooling and protocol pointers
  runbooks/                # operational checks, recovery and rollback if applicable
  evidence/                # sanitized verification records
  assets/                  # owned/licensed diagrams and exported design evidence
```

Keep root PRD, TRD, TOGAF-ADM, TDD and design contracts authoritative.
Navigation pages link to them; they do not maintain competing copies.
Choose exactly one canonical contribution policy and one security policy,
even if the navigation links into `.github/` or the root.

MkDocs and `mkdocs.yml` are optional, not a new default runtime. If adopted,
pin documentation dependencies, validate internal links and strict builds,
ensure navigation exposes the root contracts, and check the publish artifact
for private evidence or credentials. Publishing remains separately approved.
Do not add a workflow that rewrites source URLs and pushes directly to a
protected branch during a documentation deployment.

## Contributor intake contract

Retain the agent-task form; add distinct intake forms when useful:

| Intake | Minimum fields | Routing |
| --- | --- | --- |
| Bug | Observed/expected result, reproduction, environment/version, impact, safe logs | Maintainer triage before assignment; a defect is not automatically agent-ready |
| Feature | User problem, outcome, alternatives, scope/non-goals | Link or propose Epic/Feature, then decompose into accepted Stories |
| Documentation | Affected page/section, current gap, audience and desired correction | Link the governing requirement or explain why not applicable |
| Agent Story/Task | This skill's requirement, scope, hierarchy, acceptance, evidence and risk contract | Require readiness and dispatcher grant |
| `.github/ISSUE_TEMPLATE/config.yml` | Deliberate blank-issue policy and verified support/private-security destinations | No placeholder URLs or assumed enabled Discussions/advisory features |

Do not require users to understand the architecture to report a bug.
Do not turn every incoming feature request into a ready Story. Keep public
templates free of credentials and requests for confidential customer data.

## Optional checks and automation

Decide each independently and record its approval and owner:

- Pre-commit hooks: useful local feedback, not mandatory extra infrastructure.
  Reuse existing hooks where present; pin external revisions and run equivalent
  read-only checks in CI because local hooks are bypassable. CI reports
  formatting failures; it does not auto-commit to a contributor's branch.
- CodeQL/dependency review: select supported languages, entitlements and
  event coverage. Required security checks must fail on errors; do not
  retain `continue-on-error` for a required scan.
- PR-title lint: align with the chosen squash/release convention. Do not
  duplicate commit lint without a reason or evaluate PR text as shell code.
- Release automation: choose manual, Release Please or semantic-release,
  not overlapping version writers. Confirm branches, package destinations,
  token permissions and human promotion gates before adding configuration.
- Cache cleanup: add only for an observed retention/quota need, scoped to
  repository caches and isolated from code execution.
- Dependency/hook refresh: scheduled review PRs are optional. Validate
  updated pins and their actual CI before merge; never use a broad workflow
  token merely because an upstream sample does.
- Auto-merge and stale closure: disabled by default. Branch names and bot
  identity alone do not authorize merging; elapsed inactivity does not prove
  acceptance. Preserve approved Stories, blockers and audit records.
- Template sync: opt-in, pinned-source, review-only changes through the
  repository's existing vendor/update mechanism. Protect the project plan,
  requirements, agent policy, code ownership, workflows, secrets configuration
  and authored docs. An ignore list alone is not a security boundary.

## Adoption safety checks

Never copy broad scanner exclusions for documentation, test directories or
credential-shaped strings. Use synthetic detector fixtures to prove coverage
of docs and tests, plus a narrow known false positive to prove an exception.
Do not put real secrets in fixtures or evidence.

Do not assume `pull_request_target` itself proves a vulnerability, but do not
copy it for ordinary PR validation. Use unprivileged PR checks on the intended
revision. Privileged metadata jobs must not execute untrusted code, install
its hooks, consume untrusted artifacts as commands, or auto-commit fixes.

If actual upstream files are later imported, follow the target repository's
vendor/provenance process, pin the commit, retain the upstream license and
notices, and review every changed trigger, permission and secret reference.
This skill adopts structure and policy through original instructions; it does
not vendor the ops4life implementation or enable its workflows.
