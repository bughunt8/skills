# The Document Spine

Answers one decision: **which sections go in PRD, TRD, WIREFRAME, DESIGN, ADRs and
`docs/architecture/`, and why those and not others.**

Each artifact answers exactly one question, owns one set of stable IDs, and is machine-checkable by
`scripts/validate_docs.py`.

| Question | Artifact | Owns |
|---|---|---|
| Why build it, for whom? | `PRD.md` | `FR-`/`NFR-` register, `US`, success criteria |
| How will it be built? | `TRD.md` | architecture, NFR realisation, traceability matrix |
| What did we decide, and why? | `docs/adr/NNNN-*.md` | immutable decision log |
| What is the architecture context? | `docs/architecture/*.md` | TOGAF ADM-lite deliverables |
| What does it look like? | `WIREFRAME.md` | `SCR-` inventory, states, nav map |
| What are the visual rules? | `DESIGN.md` | design tokens + rationale |
| What must the agent know? | `AGENTS.md` | commands, TDD rule, doc authority |

---

## 1. PRD.md

Synthesised from four independent templates plus the agent-facing conventions of GitHub's spec-kit.

**Sections:** Summary (press-release style) · Problem & Context · Goals · Non-Goals · Users &
Personas · Success Metrics · User Stories · Functional Requirements · Non-Functional Requirements ·
Assumptions, Constraints, Dependencies · UX & Design References · Open Questions · Risks · Rollout
Plan · Traceability · Change Log.

**Three conventions that make it agent-usable rather than decorative:**

1. **`[NEEDS CLARIFICATION: …]` inline markers.** spec-kit's own template writes
   `FR-006 System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified -
   email/password, SSO, OAuth?]`. Greppable, so CI can fail a PR that ships an unresolved spec.
2. **Stable IDs assigned once, never renumbered.** `FR-001`, `NFR-001`, `US1`, priorities `P1..P3`.
   Functional requirements are phrased `System MUST …`. `NFR-` is not part of spec-kit — it is this
   template's extension for the ISO/IEC 25010 block in the TRD.
3. **Link, don't inline.** Atlassian: "We embed a lot of links within our product requirements
   documents… It helps abstract out the complexity and progressively disclose the information to the
   reader as needed."

**Non-goals need the sharpest definition available**, and it belongs in the template as a comment:
"Non-goals aren't negated goals like 'The system shouldn't crash', but rather things that could
reasonably be goals, but are explicitly chosen not to be goals."

**Weight.** Keep it lean by default. Atlassian: "Agile PRDs focus on shared understanding, customer
needs, and flexibility, avoiding overly detailed specs." Aha!: "Keep the PRD concise and clear",
"Prioritize flexibility and iteration over exhaustive details", and note that a PRD should "inspire
teammates with enough information to create elegant solutions" rather than prescribe exact
interactions. Only regulated domains (Aha! names healthcare) justify the heavyweight form.

Sections 1 and 13 come from Amazon's PR/FAQ, whose internal-FAQ list is effectively a business-risk
checklist — "What assumptions need to be true for this product to be successful" and "What are the
top three reasons this product will not succeed?"

Sources: [Atlassian PRD](https://www.atlassian.com/agile/product-management/requirements) ·
[Atlassian Confluence template](https://www.atlassian.com/software/confluence/templates/product-requirements) ·
[Aha! PRD template](https://www.aha.io/roadmapping/guide/templates/create/prd) ·
[Aha! what to include](https://www.aha.io/roadmapping/guide/requirements-management/what-is-a-good-product-requirements-document-template) ·
[ProductPlan](https://www.productplan.com/glossary/product-requirements-document) ·
[Working Backwards PR/FAQ](https://workingbackwards.com/resources/working-backwards-pr-faq/) ·
[spec-kit spec-template.md](https://github.com/github/spec-kit/blob/main/templates/spec-template.md)

---

## 2. TRD.md

Backbone from Google's design-doc guidance: **Context and scope · Goals and non-goals · The actual
design · Alternatives considered · Cross-cutting concerns**, with sub-topics for system-context
diagram, APIs, data storage, degree of constraint. Two of its rules go in the template verbatim:
"one should withstand the temptation to copy-paste formal interface or data definitions into the
doc", and "Design docs should rarely contain code."

Mandatory **Abstract**, **Introduction**, **Security Considerations** and a normative-vs-informative
**References** split come from RFC 7322, which requires all three of those sections in every
published RFC.

Operational NFR sections follow Uber's RFC template: Service SLAs · Service dependencies · Load &
performance testing · Multi-datacenter concerns · Security considerations · Testing & rollout ·
Metrics & monitoring · Customer support considerations.

**NFRs are organised by the nine ISO/IEC 25010:2023 quality characteristics.** Two placements catch
people out and must be pre-filled as comments in the template:

| Characteristic | Sub-characteristics |
|---|---|
| Functional Suitability | Completeness, Appropriateness, Correctness |
| Performance Efficiency | Time Behaviour, Capacity, Resource Utilization |
| Compatibility | Co-Existence, Interoperability |
| Interaction Capability | Recognisability, Learnability, Operability, User Error Protection, Engagement, Inclusivity, Assistance, Self-Descriptiveness |
| Reliability | Faultlessness, Fault Tolerance, **Availability**, Recoverability |
| Security | Confidentiality, Integrity, Non-Repudiation, Accountability, Authenticity, Resistance |
| Maintainability | Modularity, Reusability, Analysability, Modifiability |
| Flexibility | Testability, Adaptability, **Scalability**, Installability, Replaceability |
| Safety | Operational Constraints, Risk Identification, Fail Safe, Hazard Warning, Safe Integration |

**Availability sits under Reliability. Scalability sits under Flexibility** (formerly Portability).
Compliance is *not* one of the nine — file it under constraints.

**Length.** Google: "The sweet spot for a larger project seems to be around 10-20ish pages", and
"it is absolutely possible to write a 1-3 page 'mini design doc'… especially helpful for incremental
improvements or sub tasks in an agile project."

**The anti-pattern, verbatim, because it is the common failure:** a doc that "basically says 'This is
how we are going to implement it' without going into trade-offs, alternatives, and explaining
decision making… would probably have been a better idea to write the actual program right away."

**Maintenance rule:** "If the designed system hasn't shipped yet, then definitely update the doc."
After shipping, add amendments and ADRs rather than rewriting history.

**Section 4 is load-bearing** — the single traceability matrix. See `traceability_scheme.md`.

Sources: [Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/) ·
[RFC 7322](https://datatracker.ietf.org/doc/html/rfc7322) ·
[Uber RFCs via Pragmatic Engineer](https://blog.pragmaticengineer.com/scaling-engineering-teams-via-writing-things-down-rfcs/) ·
[ISO/IEC 25010 overview](https://iso25000.com/index.php/en/iso-25000-standards/iso-25010) ·
[arc42 ISO 25010 breakdown](https://quality.arc42.org/standards/iso-25010) ·
[RFC vs ADR](https://candost.blog/adrs-rfcs-differences-when-which/)

---

## 3. TOGAF ADM → `docs/architecture/`

**The framing that makes TOGAF survivable in a code repo** is The Open Group's own: the ADM "does
not: Mandate that the steps must be performed in the sequence shown; Mandate a 'waterfall' process…
Specify the duration of any phase or cycle of architecture development", and "Rather than viewing the
ADM graphic as a process model, it is helpful to view it as a reference model."

The same guide collapses the phases into three verbs — **Understand** (A–D), **Specify** (E–F),
**Govern** (G–H) — and maps Capability Architectures to delivery sprints: "These may align to
delivery sprints… They are sufficiently detailed to be handed to developers for action." Teach the
three-verb collapse, not the ten-phase circle.

Deliverable mapping. Enterprise-only artifacts are deliberately excluded.

| ADM phase | Kept in repo | Where | Dropped |
|---|---|---|---|
| Preliminary | Architecture Principles | `docs/architecture/principles.md` | Organizational Model, Tailored Framework |
| A: Vision | Architecture Vision, Statement of Architecture Work | `docs/architecture/vision.md` | Communications Plan, Capability Assessment |
| B–D | Architecture Definition Document, Requirements Specification | `TRD.md` §5–§7 | full Business Architecture |
| E–F | Architecture Roadmap, Implementation & Migration Plan | `docs/architecture/roadmap.md`, `TRD.md` §11 | Implementation Governance Model |
| G–H | Architecture Contract (as CI gates + CODEOWNERS), Change Request | `docs/adr/`, GitHub issues | formal contracts, Compliance Assessment |
| Requirements Mgmt | Architecture Requirements Specification, Requirements Impact Assessment | `PRD.md` register; PR description | — |

`docs/architecture/` **is** the Architecture Repository for a single-repo project. State that in
`docs/index.md` — it is the conceptual bridge users miss. The standard's own tailoring licence:
"organizations will customize it during adoption, and deliberately choose some elements, customize
some, exclude some, and create others."

Sources: [Enabling Enterprise Agility G20F](https://pubs.opengroup.org/togaf-standard/guides/enabling-enterprise-agility/) ·
[TOGAF Pocket Guide Ch.7 deliverables](https://pubs.opengroup.org/pocket-guides/togaf-pocket-guide/main/chap07.html) ·
[TOGAF ADM contents](https://pubs.opengroup.org/togaf-standard/adm/) ·
[TOGAF Introduction Ch.1](https://pubs.opengroup.org/togaf-standard/introduction/chap01.html) ·
[What is new in the 10th Edition](https://www.opengroup.org/togaf/new-version) ·
[Open Agile Architecture C208](https://pubs.opengroup.org/architecture/o-aa-standard-single/)

---

## 4. ADRs — `docs/adr/NNNN-imperative-verb-phrase.md`

Use **MADR** headings — Context and Problem Statement · Decision Drivers · Considered Options ·
Decision Outcome · Consequences · Confirmation · Pros and Cons of the Options · More Information —
plus two fields from The Open Group's own O-AA ADR template: **Decision scope** and **Decision
type**. That combination is both current and TOGAF-native, which matters when the surrounding
workflow is ADM-based. O-AA is also the citation for justifying ADRs upward: "An Architecture
Decision Record (ADR) provides an Agile and lightweight way of doing this", and "Intentional
architecture should be simple, focused, and compact because: It is likely to evolve, so investing in
a detailed model would be wasteful."

Two rules for the template header:

- **An ADR is immutable. Only its status changes.**
- Records live "in the source repository of the code base to which they apply", "written in a
  lightweight markup language, such as markdown, so they can be easily read and diffed just like any
  code", one file each, "numbered in a monotonic sequence as part of their file name".

Nygard's original five fields — Title, Context, Decision, Status, Consequences — remain the minimum;
Context "describes the forces at play, including technological, political, social, and project local"
and is value-neutral; Decision is "stated in full sentences, with active voice. 'We will …'";
Consequences record positive, negative and neutral. "The whole document should be one or two pages
long."

Directory choice: `docs/adr/`. Other defensible options seen in the wild are `doc/adr`,
`doc/architecture/decisions` and `decisions/`. Note the known limit: "Storing them in a product
repository won't work for ADRs that cover a broader ecosystem than a single code base."

Sources: [Nygard, Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) ·
[Fowler, Architecture Decision Record](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html) ·
[MADR](https://adr.github.io/madr/) ·
[adr-tools](https://github.com/npryce/adr-tools) ·
[log4brains](https://github.com/thomvaill/log4brains) ·
[O-AA](https://pubs.opengroup.org/architecture/o-aa-standard-single/) ·
[joelparkerhenderson/architecture-decision-record](https://github.com/joelparkerhenderson/architecture-decision-record)

---

## 5. DESIGN.md — follow the Google Labs `design.md` specification

Google open-sourced this format for exactly this purpose: "DESIGN.md gives agents a persistent,
structured understanding of a design system", and "Instead of guessing intent, AI agents can know
exactly what a color is for, and can validate their choices against WCAG accessibility rules."

**Why the decision is close to free:**

- **Lintable in CI.** `npx @google/design.md lint DESIGN.md` exits 1 on errors. Eleven rules,
  including `contrast-ratio` — component `backgroundColor`/`textColor` pairs below WCAG AA 4.5:1 —
  plus `broken-ref`, `missing-primary`, `orphaned-tokens`, `missing-typography`, `section-order`,
  `unknown-key`, `token-like-ignored`. A design system that fails accessibility breaks the build.
- **Exports to the standards.** `export --format dtcg` emits W3C Design Tokens Format Module JSON;
  `css-tailwind` emits a Tailwind theme. Not a dead end.
- **Already wired into this skill library.** The `stitch-*` skills read a project `DESIGN.md` for
  token fidelity, mapping `colors.*`, `typography.*`, `spacing.*` to CSS variables.

**Structure:** optional YAML frontmatter carrying machine-readable tokens (`version`, `name`,
`description`, `colors`, `typography`, `rounded`, `spacing`, `components`) plus a markdown body in a
**fixed section order the linter enforces**: Overview · Colors · Typography · Layout · Elevation &
Depth · Shapes · Components · Do's and Don'ts. All sections use `##`. Sections may be omitted but
present ones must keep that sequence.

Token rules: colors "must start with `#` followed by a hex color code in the SRGB color space", at
least the `primary` palette must be defined, dimension units are `px`/`em`/`rem`, and references are
wrapped in curly braces — `{colors.primary-60}`, `{rounded.md}`. Typography defines 9–15 levels
(`headline`, `display`, `body`, `label`, `caption`).

**The spec is at version `alpha`** and does not yet cover motion, breakpoints or states. Extend
*after* the canonical sections so `section-order` still passes: **Motion** (DTCG `duration` and
`cubicBezier` types) · **Breakpoints** · **States** (default/hover/active/focus-visible/disabled/
loading/error/empty) · **Accessibility** · **Token Export**.

Accessibility numbers to encode: text contrast "at least 4.5:1", large text (≥18pt, or ≥14pt bold)
"at least 3:1", and computed values "should not be rounded (e.g., 4.499:1 would not meet the 4.5:1
threshold)".

DTCG syntax for the export path: an object with a `$value` property is a token, `$type` is
case-sensitive and inherits from "the closest parent group with a `$type` property", and "Tools MUST
NOT attempt to guess the type of a token by inspecting the contents of its value."

Sources: [Google blog on DESIGN.md](https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-design-md/) ·
[google-labs-code/design.md](https://github.com/google-labs-code/design.md) ·
[design.md spec](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md) ·
[DTCG Format Module 2025.10](https://www.designtokens.org/tr/2025.10/format/) ·
[DTCG stable-version announcement](https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/) ·
[WCAG 2.2 SC 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum) ·
[Style Dictionary DTCG support](https://styledictionary.com/info/dtcg/)

---

## 6. WIREFRAME.md

**Sections:** Conventions · Screen Inventory · Navigation Map · per-screen specification · Shared
Patterns · Interaction Flows · Open Questions · Change Log.

**Notation, in priority order:**

1. **Wireloom** fenced blocks for screen layouts — "A Markdown extension for UI wireframes. Describe
   a screen in a few indented lines. Get a clean SVG mockup that renders anywhere Markdown does."
   Its rationale is this exact use case: "Because Wireloom sources are plain text, they live in git,
   diff cleanly, review in PRs, and version alongside the feature spec", it is "Low-fidelity by
   design, [so] the aesthetic reads as a wireframe, not a finished UI", and it is explicitly
   agent-authored — "give it the grammar reference in `AGENTS.md`". Its
   `annotation … target="signin-btn"` mechanism is why every interactive element needs a stable id.
2. **Mermaid** `flowchart LR` for the navigation map and key journeys. Two gotchas for the template
   comments: a lowercase `end` used as a node label breaks the flowchart, and a node starting with
   `o` or `x` needs a space or a capital.
3. Monospace ASCII as the fallback when Wireloom is not installed.

Each screen block enumerates states and responsive behaviour **by reference** to
`DESIGN.md ## Breakpoints` and `## States`. The two documents interlock rather than duplicate.

Keeping wireframes out of the PRD is the sourced position, not a preference: Atlassian says to *link*
design explorations to the PRD, and ProductPlan explicitly excludes pixel-perfect wireframes, keeping
the PRD to "the overall user workflow".

Sources: [Wireloom](https://github.com/StardockCorp/Wireloom) ·
[Mermaid flowchart syntax](https://mermaid.ai/open-source/syntax/flowchart.html) ·
[GitHub creating diagrams](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams) ·
[design.md spec](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md) ·
[Atlassian PRD](https://www.atlassian.com/agile/product-management/requirements) ·
[ProductPlan](https://www.productplan.com/glossary/product-requirements-document)

---

## 7. TDD — written in three places, once each

- **`CONTRIBUTING.md`** carries the human rule, citing the canonical three steps: "Write a test for
  the next bit of functionality you want to add. Write the functional code until the test passes.
  Refactor both new and old code to make it well structured." Weighting follows the Testing Trophy —
  Static, Unit, Integration, E2E; "Write tests. Not too many. Mostly integration." The investment
  principle is worth quoting: "it's all about getting a good return on your investment where 'return'
  is 'confidence' and 'investment' is 'time'."
- **`AGENTS.md`** carries the executable form: exact commands plus the imperative that works on
  agents — "**Write these tests FIRST, ensure they FAIL before implementation**". Complement with
  Anthropic's framing: "Give Claude a check it can run" and "Have Claude show evidence rather than
  asserting success."
- **`vitest.config.ts`** carries enforcement: `coverage.thresholds` with `perFile: true`. A negative
  threshold is treated as the maximum number of uncovered items allowed — a useful ratchet for
  legacy code.

Sources: [Fowler, TDD](https://martinfowler.com/bliki/TestDrivenDevelopment.html) ·
[Kent C. Dodds, Testing Trophy](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications) ·
[spec-kit tasks-template.md](https://github.com/github/spec-kit/blob/main/templates/tasks-template.md) ·
[Anthropic Claude Code best practices](https://www.anthropic.com/engineering/claude-code-best-practices) ·
[Vitest coverage config](https://vitest.dev/config/coverage) ·
[Playwright installation](https://playwright.dev/docs/intro)

---

## 8. AGENTS.md — and the discipline that keeps it useful

The spec mandates no schema: "AGENTS.md is just standard Markdown", "Use any headings you like; the
agent simply parses the text you provide." Resolution is nearest-file: "Agents automatically read the
nearest file in the directory tree, so the closest one takes precedence", and "explicit user chat
prompts override everything." It is stewarded by the Agentic AI Foundation under the Linux
Foundation and read by Codex, Cursor, Copilot coding agent, Gemini CLI, Windsurf, Cline, Zed, Aider,
Jules, Factory, goose, opencode, Devin and others.

**Anthropic's editorial rules are the binding constraint. Put them in the template header:**

- "Keep it concise. For each line, ask: 'Would removing this cause Claude to make mistakes?' If not,
  cut it."
- "Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"
- Emphasise **only one line** with "IMPORTANT".

Target under 200 lines. Include: bash commands the agent cannot guess, non-default style rules,
testing instructions, repo etiquette, architectural decisions, environment quirks, gotchas. Exclude:
anything derivable from code, standard language conventions, detailed API docs, frequently-changing
info, file-by-file descriptions.

**Two patterns to copy from production repos:**

1. **One source of truth plus thin adapters.** `CLAUDE.md` contains the single line `@AGENTS.md` —
   Claude Code's documented import mechanism, and it avoids Windows `core.symlinks` breakage that a
   symlink introduces. Copilot already reads AGENTS.md with nearest-file precedence, so
   `.github/copilot-instructions.md` is only needed for reviewer-specific tuning.
2. **Directory-scoped second files.** A `.github/AGENTS.md` containing *only* GitHub Actions security
   rules, so workflow edits get the right constraints without bloating the root file.

**Delegate rather than duplicate.** The stated reason from a repo that does this well: "copied
versions, rule lists, and counts become stale." AGENTS.md should say "read CONTRIBUTING", "read the
PR template", "`package.json` is authoritative for commands".

Sources: [agents.md](https://agents.md/) ·
[openai/agents.md](https://github.com/openai/agents.md) ·
[Anthropic Claude Code best practices](https://www.anthropic.com/engineering/claude-code-best-practices) ·
[Claude Code memory](https://docs.anthropic.com/en/docs/claude-code/memory) ·
[Copilot custom instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot) ·
[Cursor rules](https://cursor.com/docs/context/rules)

---

## 9. Optional spec-kit interop

Emit per-feature `specs/NNN-slug/{spec.md, plan.md, research.md, data-model.md, contracts/,
tasks.md}` only when the user asks. spec-kit's phases are Phase 0 research, Phase 1 design, Phase 2
tasks, with a Constitution Check before Phase 0 and re-checked after Phase 1. Commands are now
namespaced: `/speckit.constitution`, `/speckit.specify`, `/speckit.clarify`, `/speckit.plan`,
`/speckit.checklist`, `/speckit.tasks`, `/speckit.analyze`, `/speckit.implement`,
`/speckit.taskstoissues`, `/speckit.converge`.

The boundary matters: `/speckit.specify` should "focus on the 'what' and 'why,' not the tech stack",
while `/speckit.plan` is where you "provide your tech stack and architecture choices" — the same
split as PRD vs TRD. Amazon Kiro's equivalent is `.kiro/specs/<feature>/{requirements.md, design.md,
tasks.md}`.

**Default to off.** Two competing task lists is worse than one.

Sources: [github/spec-kit](https://github.com/github/spec-kit) ·
[spec-kit plan-template.md](https://github.com/github/spec-kit/blob/main/templates/plan-template.md) ·
[spec-kit tasks-template.md](https://github.com/github/spec-kit/blob/main/templates/tasks-template.md) ·
[Spec Kit quickstart](https://github.github.com/spec-kit/quickstart.html) ·
[Kiro specs](https://kiro.dev/docs/specs/) ·
[Kiro specs best practices](https://kiro.dev/docs/specs/best-practices/)
