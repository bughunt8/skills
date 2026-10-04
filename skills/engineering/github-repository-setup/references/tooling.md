# Tool and skill dependencies

Choose capabilities before transports. Do not install every available MCP
server. Record decisions in `docs/agents/tooling.md` and link it from README,
AGENTS.md, Agent.md, and Agent-Protocol.md. No Claude client is in scope.

## Capability matrix

| Capability | Requirement in this profile | Preferred integration | Acceptance evidence |
| --- | --- | --- | --- |
| Repository checkout, branch and worktree operations | Required | Git CLI in task worktree | Correct remote, branch/base SHA, isolated worktree |
| GitHub Issues, dependencies, PRs and CI results | Required | Existing `gh` CLI or approved GitHub MCP | Read target issue, PR diff and check results; approved write only in scoped test |
| CodeGraph repository navigation | Required setup for supported code projects; explicit blocked/N/A outcome otherwise | Pinned CodeGraph CLI plus approved client MCP | Fresh index, real symbol/caller, exclusion and refresh tests, client query |
| Language diagnostics and symbol navigation | Required language tooling for code projects; LSP recommended where supported | Client-native language service/LSP plus compiler/linter | Definition/reference query and an introduced-then-cleared diagnostic in a scratch fixture |
| Verification and TDD | Required | Existing test runner, compiler, linter and architecture checks | Real red/green test evidence and full merge gate |
| Browser interaction and accessibility checks | Required for UI behavior verification | Existing browser/E2E runner; MCP adapter optional | Target flow, keyboard/error/responsive checks and sanitized artifacts |
| Penpot design access | Conditional on Penpot being the approved design source | Official Penpot MCP, local or approved remote | Correct file/page inspection; approved isolated edit and exported evidence |
| Design-system component catalog | Conditional on the selected UI stack | Existing component docs/registry; MCP only if needed | Actual component/token match and code-side validation |
| GitHub Projects | Optional presentation | GitHub CLI/MCP/UI | Issue hierarchy remains authoritative without the board |

LSP is a client/language-server protocol, not an MCP server or a CodeGraph
replacement. Its language features include diagnostics and definition
navigation, whereas this profile uses CodeGraph for repository relationships.
Use a reviewed LSP-to-MCP bridge only if the selected agent cannot access
native language tooling; never add one simply because both protocols exist.
[LSP specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/).

Select the language service supported by the actual stack and agent. Record
its exact package/version, workspace root, configuration and command. Do not
introduce a second TypeScript/Python/etc. toolchain that disagrees with CI.
Diagnostics are feedback, not a substitute for executing tests or compilation.

## GitHub MCP

Use the official
[GitHub MCP server](https://github.com/github/github-mcp-server) when the
selected agent needs MCP access. The upstream supports hosted remote and
local configurations, selected toolsets/tools, and read-only mode.
Existing working `gh` access satisfies the capability; adding MCP is optional.

1. Confirm the GitHub host, approved client, auth policy and target repositories.
   Prefer existing authentication. Do not request broad new scopes merely to
   enable every server tool.
2. Choose supported remote or pinned local distribution. Record the hosted
   endpoint or immutable local version/image digest and transport in tooling docs.
   Keep credentials in the client secret store or runtime environment, never Git.
3. For research/review, enable read-only operations. For implementation,
   allow only needed issue/PR/repository tools; allow CI reads without enabling
   arbitrary workflow dispatch. Keep administration, merges and releases out
   of the worker's tool grant.
4. Check actual server help/docs before writing flags or headers. Local
   `--read-only` and `--toolsets` flags are not automatically remote settings.
   Feature-detect hierarchy/dependency operations and use a documented CLI/API
   fallback when an MCP version lacks them.
5. Verify identity and repository scope without exposing tokens. Read a known
   issue, linked PR, diff and CI run. Test authorized writes only in an
   approved issue/branch. Confirm a reviewer configuration cannot write.

Tool allowlists reduce exposure but do not replace token permissions or
repository rules. If CLI and MCP coexist, use the same issue identifiers,
authority rules and dispatcher. Neither tool is an alternative way around a
permission denied by the other.

## Penpot MCP

Require this only when the project actually uses Penpot. Otherwise record the
approved design source and export/review path; do not block a backend-only
project or install Penpot to satisfy a checkbox.

The [official Penpot MCP guide](https://help.penpot.app/mcp/) describes local
and remote connections and requires an active design-file connection.
Remote URLs may embed a `userToken`; the complete URL is therefore secret.
Never put it in docs, committed MCP config, screenshots, command history,
logs, or issue evidence.

1. Confirm the design workspace/file, editing scope, selected non-Claude
   client, data residency, and local versus remote choice.
2. Local: resolve a Penpot-compatible exact `@penpot/mcp` version rather than
   leaving `stable`/`latest` in repeatable setup. Check runtime requirements.
   Start the MCP and plugin servers in the approved environment. The guide's
   default local endpoints are `http://localhost:4401/mcp` and the plugin
   manifest `http://localhost:4400/manifest.json`; verify actual bound ports.
3. Remote: enable the account integration and use the client's secure
   connection flow for its key-bearing URL. Do not publish the URL or use an
   unreviewed global installer command containing the key.
4. Open the intended Penpot file and connect the plugin/MCP session. Confirm
   the focused page and owning browser tab; a healthy server alone does not
   prove a live design connection.
5. Start with read-only inspection of pages, components and tokens. Record
   file/page/component IDs and revision/export time in UI-UX.md,
   WIREFRAME.md and DESIGN-SYSTEM.md. Keep a reproducible repository snapshot
   or sanitized export reference so a later live edit cannot silently change
   an approved Story's design contract.
6. For an approved write test, use a designated scratch page/component and
   explicit scope. Inspect the result and obtain approval before destructive
   edits to shared design assets. Do not equate MCP connectivity with design
   approval or UI implementation correctness.

Penpot exports do not replace code accessibility tests, responsive testing,
or design-system conformance. Keep the selected browser and plugin connected
and disclose disconnected/unsupported cases rather than inventing designs.

## Companion skills

Skills are instructions, not services or proof of tool access. Resolve exact
installed names and inspect their resource paths before adding a dependency.

| Stage | Candidate skill in this library | Selection rule |
| --- | --- | --- |
| Unresolved setup decisions | `grilling` | Conditional interview before approval; see the process below |
| Domain decisions during grilling | `grill-with-docs` plus `domain-modeling` | Only when domain terms or ADRs need clarification; inspect their templates first |
| Agent conventions | `setup-matt-pocock-skills` | Required integration; apply AGENTS-only override and seed fallback |
| Missing document skeleton | `start-github-repo` in docs mode | Only when equivalent documents do not exist |
| Requirements and backlog | `to-spec`, `to-tickets` | Use approved PRD/requirements and preserve Epic/Feature/Story hierarchy |
| Ticket classification | `triage` | If installed, configure canonical role mappings; only maintainers grant readiness |
| Implementation and tests | `tdd` | Follow project commands and criterion-level evidence |
| Independent review | `code-review` | Run by an independent reviewer; not self-approval |
| Architecture and design | Existing TOGAF, design-system, UI/UX skills | Select one suitable installed skill per task; no blanket installation |

Do not invent an LSP, GitHub or Penpot "skill" to mean the corresponding
service is installed. If a listed companion is absent, record the gap and
use the document contract directly or obtain approval to install from a
reviewed, pinned source with license/provenance. Never import third-party
skills by undocumented copying.

The setup profile's approval and readiness gates take precedence over
companion shortcuts. In particular, `to-spec` may suggest publishing and
applying `ready-for-agent` immediately; here it must draft first unless
publication is already approved, and only maintainer-approved, unblocked,
testable Stories can become agent-ready. A spec is not automatically a
ready implementation ticket.

## Conditional grilling during setup

Use the installed skill whose exact name is `grilling`, not a guessed alias.
Load it when inspection leaves consequential choices unresolved: project
scope, Epic/Feature/Story boundaries, acceptance, ADM tailoring, agent
authority, branching/completion, design ownership, or tooling permissions.
If the repository and user instructions already settle them, skip the
interview and record that basis. Do not reopen the no-Claude/no-Plane choices.

1. Build a decision tree from the remaining choices and their dependencies.
   Separate facts to research from choices the user must make.
2. Research facts first. Ask only the current decision frontier, with a
   recommendation, trade-offs, and the effect on files or permissions.
   Do not ask downstream questions whose prerequisites are still open.
3. Wait for the user's answers and recompute the frontier. Keep completed
   branches settled; avoid repeated confirmations for unchanged scope.
4. Use `grill-with-docs` and `domain-modeling` if domain ambiguity or meaningful
   architectural trade-offs need capture. Inspect their linked format files
   before invoking them. If resources are missing, disclose the gap and
   draft the agreed glossary/ADR against the existing repository convention.
   Keep CONTEXT.md a domain glossary when that companion is in use; store
   implementation constraints in TRD/ADRs, not in the glossary.
5. Record decisions and unresolved blockers in the setup plan and relevant
   PRD/TRD, TOGAF-ADM, design or tooling documents. Require shared-understanding
   confirmation before applying newly decided settings. Do not grant an
   implementer wider permissions merely because an interview completed.

Stop when the decision frontier is empty or the user explicitly defers a
branch. Deferred decisions have an owner and blocking effect; never silently
replace them with invented answers. A change requiring fresh authority
returns to this process without reopening unrelated settled work.

## Tooling inventory and smoke tests

For each selected dependency record:

```text
Capability | required/conditional/optional | provider/package | exact version
Client + transport | configuration path | permissions + secret reference name
Owner | tested repository/worktree/design file | smoke command or operation
Evidence + revision | verified/blocked/deferred/N/A | fallback
```

Verify each required capability in the actual executing client. Listing an
MCP server in JSON or installing a language server binary is not sufficient.
Unapproved writes, inaccessible files, unsupported language servers, empty
graphs, or missing tools must appear in the handoff as gaps. Do not silently
turn off gates or expand credential scopes to make the status green.
