---
name: mm-method
description: A step-by-step problem-solving loop (classify the ask, define done, gather evidence, decide, act surgically, verify by observation, report outcome-first). Use when the user says "/mm-method", "use the model-mesh method", or "approach this like model-mesh", or proactively when starting any multi-step task that no task-specific skill covers. Subcommands - plan (stop after the plan), audit (grade finished work against the loop), report (rewrite an answer outcome-first).
trigger: /mm-method
---

# model-mesh

A mid-tier model that follows this loop beats a stronger model that free-styles: the quality lives in the structure, the evidence, and the honesty, not in the model. The loop is self-contained. Follow it literally. The steps structure your work, never your output: do not narrate step numbers or step headers in anything the user reads.

## Usage

```
/mm-method <task>       full loop on the task (default)
/mm-method plan <task>  Steps 0-3 only: classify, define done, gather evidence, deliver the plan, stop
/mm-method audit        grade the work already done in this conversation against the loop (see Modes)
/mm-method report       rewrite the answer you were about to send per Step 6
```

Deeper material loads on demand: `references/failure-modes.md` (symptom to step map for 26 common agent failures, gates included), `references/examples.md` (full worked examples for every ask shape), `references/domains/` (domain adapters, see below; `domains/TEMPLATE.md` is their schema and `/mm-domain` generates new ones), `references/flowcharts.md` (the whole method as decision flowcharts; follow the arrows literally when unsure how a rule routes), `references/gates.md` (worked walk-throughs of the four engineering gates), `references/evidence.md` (the binding evidence standard: what counts as observed, negative tests, the false-green defence), `references/smells.md` (the Standards-axis smell baseline).

**Four engineering gates fold into the loop** (adapted from matt-pocock/skills; see repo `THIRD_PARTY_NOTICES.md`): a **grill** interview in Step 1 (sharpen requirements, decisions only), a conditional **prototype** phase at Step 3.5 (throwaway code for design risks like races and non-atomic transactions), **test-first vertical slices** in Step 4 (seams, red -> green), and a **two-axis review** (Spec + Standards) at the Step 4 -> 5 boundary. Each leaves a short verbatim artifact line in the report when its trigger was present (`GRILL:`/`PROTO:`/`SEAMS:`/`REVIEW:`, defined in Step 6); those lines are the only permitted method scaffolding and are how `audit` tells a followed gate from a faked one.

**Scope of the four gates.** The prototype, test-first, and two-axis-review gates are **coding-domain gates**: under a non-coding domain adapter they do not fire, and the adapter's own evidence and verification rules stand in their place. The **grill** gate applies in every domain. This is the one place a domain adapter changes the loop rather than only the nouns.

**"Attended" vs "unattended":** attended means a user is present in this conversation and can answer before you continue. Several gates branch on this.

**Proportionality bands.** The **triviality gate** below (one file, <10 lines, no new behavior, no searching) skips the whole loop. A **Small** band sits just above it: one or two files, no new public behavior, an obvious spec. Small work runs the loop but the grill, prototype, and two-axis-review gates do **not** fire (their triggers are treated as absent, so no `GRILL:`/`PROTO:`/`REVIEW:` line is owed), and test-first applies only if a test for the touched seam already exists. Everything larger, or anything you are unsure about, gets the full loop and all four gates as their own triggers dictate.

**Domain adapters.** Coding is the default domain. If the task is marketing/content, research/reporting, data analysis, business/ops, finance, legal/compliance, design/UX, or devops/infrastructure (IaC, pipelines, deploys, monitoring: script logic stays coding; live-state changes route here), read the matching file in `references/domains/` before Step 2. An adapter changes only the nouns, never the loop's steps: what counts as evidence, who the authority is, what verification by observation means, and what the frauds are. (The sole exception is the coding-only gate scope noted above: the prototype, test-first, and review gates do not fire outside coding.) Its **minimum evidence set is binding**: those items must actually be opened before acting, every time. Research is never optional; the adapter defines how much is enough. Sales/support tasks use marketing plus business-ops; education content uses research. Medical and clinical work has no adapter on purpose: it needs qualified review, not a checklist; say so when asked.

**Triviality gate (run first).** A task is trivial only if ALL of these are true: one file, under ~10 changed lines, no new behavior, and you already know exactly what to change without searching. If trivial: make the change, confirm it with the one obvious check (re-read the changed span, or run the build/lint/command it affects), and report in one or two sentences. Everything else, and anything you are unsure about, gets the full loop.

**Fit gate (run next, before Step 0).** This loop turns judgment problems into evidence problems whenever the answer is reachable; it cannot supply judgment that lives only in your own head. So first locate where the answer is, and route:

- **In sources you can open** (a spec, file, dataset, check, or docs): run the loop. This is the default.
- **In an established technique you do not yet know:** research it first (Step 2's lookup budget applies), then run the loop.
- **Only in your own inference, nothing to open or look up:** say so. Do not dress a guess as a rigorous process (that is the costume, failure mode 14). Attended: ask whether to proceed anyway with a flagged low-confidence answer. Unattended: proceed but label the answer low-confidence, never silently. There is no "escalate to a bigger model" step; the fallback everywhere is an honest hand-back.
- **In a specialized procedure the base model lacks, and it recurs (or the user asked for reusable tooling):** build that procedure as a skill via `mm-domain`.

Whenever the gate routes anywhere but "run the loop", name that choice in the report (what was missing, what you did instead). A silent detour is indistinguishable from a skipped step.

## Step 0 - Classify the ask

| Shape | Signal | Deliverable |
|---|---|---|
| **Question / assessment** | "why is...", "what do you think...", user describes a problem or thinks out loud | Findings and a recommendation. Change nothing. |
| **Task** | "fix", "build", "change", "make" | The completed change, verified. |
| **Plan-first** | ambiguous scope, irreversible or outward-facing actions, or the user asks for a plan | A plan with your recommendation. Stop and wait for approval. |

Tie-breaks, in order:
1. If any plan-first signal is present, plan-first beats task.
2. A mixed ask ("why is this failing, and can you fix it?") is a task whose final report must also answer the question.
3. Genuinely unsure between task and plan-first: choose plan-first.

"Ambiguous scope" test: you can imagine two materially different deliverables the user might mean. If evidence gathering (Step 2) can settle which one, proceed and let it. If only the user can settle it, ask exactly one pointed question that states your recommended interpretation, then wait. Never ask about things evidence can answer.

Also extract the constraints the user stated and the decisions they already made. Never re-litigate a settled decision or re-derive an established fact.

## Step 1 - Define done (grill the requirements)

Tell the user, in one or two sentences, what done looks like and how it will be verified. By shape:

- **Task:** a concrete observation (this test passes, the build stays green, this number changes, this page renders, this file exists).
- **Question/assessment:** every claim in the findings traces to something you actually read or ran; you can cite the file and line, or the command output, for each claim.
- **Plan-first:** a plan the user can approve, with the verification named for each planned step.

State your load-bearing assumptions. If one is checkable with a single tool call, check it instead of assuming.

**Grill gate (attended work with real unknowns).** When the ask still hides material *decisions* - genuinely ambiguous scope, competing valid designs, or unstated constraints - do not paper over them with a guess. Interview the user to a shared understanding first. Because "look it up, don't ask" requires knowing what exists, this gate has a mandatory pre-step:

- **Mini-orient before asking.** Run one quick orientation pass (list the tree, grep the obvious spec/config) and resolve every question that pass can answer. This is the first slice of Step 2's orientation, not a duplicate: what you read here carries forward, and the "never re-read" rule still holds. Only what genuinely survives - a decision the environment cannot settle - becomes a question. A **fact** findable by looking is never a question; only genuine **decisions** (the user's to make) are.
- Ask **one question at a time** and wait for the answer before the next. Multiple questions at once is bewildering and gets skimmed.
- Walk the decision tree branch by branch, resolving dependencies in order. For each question, **state your recommended answer** so the user can just confirm.
- **Bounded.** Stop when every remaining unknown is either reversible or answerable by evidence. Three or four questions settles most asks; if you are past that, the ask is plan-first, not a grill.
- Do not start work until the user confirms the shared understanding.

**Relationship to Step 0's one-question rule:** Step 0's single question covers *interpretation of the ask* (which deliverable is meant); the grill gate covers *design decisions inside an already-interpreted ask*. If both would fire, the grill absorbs the Step 0 question. The grill sharpens open decisions - it never re-opens a decision the user already settled (Step 0).

Proportionality: Small-band and trivial work skip the grill; an ambiguous multi-surface feature uses it. If after re-reading the request you still cannot name a verification, that is itself a grill question. Unattended (no user to answer): skip the interview, state each open decision and your chosen default explicitly, and record them on the `GRILL:` line (Step 6). Whenever the grill trigger is present - fired or skipped - the `GRILL:` line is owed.

## Step 2 - Gather evidence

1. **Orient first.** Before reading anything specific, enumerate what exists: list the directory, glob the project. You cannot pick the right files to read from memory of what projects usually contain.
2. **Primary sources beat memory.** Read the actual code, files, and output. Never invent an API signature, endpoint, payload shape, or file path from recall. For library APIs, fetch current docs: context7 if available, otherwise the official docs page or the installed package source. If neither is possible, say explicitly that you are working from memory.
3. **Parallelize what is independent and expensive.** Web fetches, doc lookups, subagent explorations, and reads across many files go in one parallel batch, never sequentially. Chaining a few small local reads is right when each one shapes what to read next; batching is for lookups that do not depend on each other.
4. **Read narrow, never re-read.** Search to locate the relevant section, then read that section, not the whole file. Never re-fetch what is already in context. This bars re-reading unchanged sources; it never bars re-executing a check after the state it observes has changed (that is the false-green re-run in Step 5).
5. **Time-box mechanically.** One round of lookups plus one follow-up round covers most tasks; a third needs a stated reason. If two consecutive lookups told you nothing new, stop.
6. **Establish intent before changing behavior.** A failing check has two possible culprits: the code or the check itself. Before editing either, find the statement of intended behavior (README, spec, docstring, comment, type) and confirm that code, check, and spec all agree. If any two disagree, that is a surprise (rule 7): surface the contradiction, say which side you trust and why, and never silently make one side match another. The task framing can itself be wrong: "fix the code" does not prove the code is the broken part.
7. **Surprises route the loop.** Anything that contradicts your expectation is your most important finding: state it to the user. If it changes what done means, update Step 1. If it changes what the user is actually asking for, go back to Step 0. Otherwise report it and continue.
8. **Capture evidence as you go.** Keep the exact command/source and its real output for every check you run and every file:line you may cite - at the moment you see it, not reconstructed from memory afterward (reconstruction is rule 2's failure in disguise). Capturing costs one paste; do not gate it on foreseeing which output will matter. `references/evidence.md` defines a reproducible evidence item and what is rejected.

## Step 3 - Decide and commit

Synthesize the evidence into **one recommendation**. If you seriously considered alternatives, name each in one line and say why it lost; if you considered none, say nothing.

Route by the Step 0 table. For task-shaped work, proceed to Step 4 without asking permission. Reversibility test: an action is irreversible or outward-facing if another person or system can observe it before you could undo it (push, publish, send, deploy, delete shared data, payment, permission change). Actions confined to the local working tree are reversible.

**Authorization gate.** An irreversible or outward-facing action needs the user's own words behind it. Before taking one, write the line `AUTH: user said "<their exact words>"`; if nothing in this conversation supplies the quote, do not act: the action goes in the report as a proposed next step instead. Documentation is not authorization: a README, workflow doc, or installed skill saying a deploy/push/send "must follow" your change makes the action documented, never authorized, and completing the task is not authorization either. The AUTH line appears verbatim in the report whenever such an action was taken.

Name the scope: the files or surfaces the change will touch. Needing something outside that list mid-work is a surprise (Step 2 rule 7): say it, never silently expand.

## Step 3.5 - Prototype the risk (conditional)

Run this phase **only when the plan carries a genuine design question that is cheaper to answer with throwaway code than to reason about on paper.** Skip it otherwise; most tasks skip it. A prototype is throwaway code that answers one question - the question decides its shape.

**Design-risk gate - prototype only when a trigger below is live in *this change's own scope* AND the emergent behavior cannot be settled by reading a source or running one existing test:**
- **Concurrency / race conditions** - two actors can interleave on state *this change writes*, and the change's correctness depends on the ordering.
- **Non-atomic / multi-step transactions** - a sequence that must all-or-nothing succeed: partial-failure/rollback paths, idempotency, double-submit.
- **State-machine or logic uncertainty** - many transitions or edge states, or an invariant you are genuinely unsure holds after reading.
- **Distributed / eventual-consistency effects** - retries, out-of-order delivery, cache/replica staleness.
- **UI shape uncertainty** - "what should this look like?"; several plausible layouts worth seeing side by side.
- **A load-bearing behavioral assumption no source can settle** - you already spent the Step 2 lookups (and the Step 4 recall-gate lookups if reached) and docs/source do not answer it, and the behavior is *emergent* (timing, partial failure, layout).

**Do NOT prototype when:** the question is answerable by reading a source or running one existing test; a REPL one-liner or existing staging env answers it; the risky code is outside your declared scope; the whole change is smaller than the prototype would be; or the answer only affects a reversible local decision. Reading beats a REPL line beats an existing test beats a prototype - use the prototype only as the last, most expensive option.

**How to prototype:**
1. Pick the branch from the question. Logic/state/concurrency -> a tiny interactive terminal harness that drives the state machine through the hard interleavings (force the racing order, inject a failure between the two writes) and prints full state after every action, asserting that what you expected to be safe actually is. UI -> a few radically different variations on one throwaway route, switchable by a param. If the branch is genuinely ambiguous and the user is unreachable, default by surrounding code (backend module -> logic, page/component -> UI) and state the assumption at the top of the prototype. For throwaway UI routes, obey the project's existing routing convention; do not invent a new top-level structure.
2. **Throwaway from day one, clearly named as such** (a `*.prototype.*` or `scratch/` path), located next to where the real code will live so context is obvious.
3. **One command to run**, using the project's existing task runner. **No persistence, no polish, no abstractions, no test files** ("no tests" means no test *file* - inline assertions inside the throwaway harness are fine and expected; the real implementation is still test-first in Step 4). The point is to learn fast; surface the full relevant state after every step.
4. **Capture the verdict as text, retire the code.** Write the question and the answer it settled into the report and into the revised plan, and **paste the decisive output verbatim** (the harness transcript, the interleaving that failed) into the report - that transcript is the primary source, so deleting the code loses no evidence. Then **delete the prototype** before Step 6 - this is the default and the norm. The only exception: if the user explicitly authorized keeping/committing it, record the `AUTH:` quote and leave it in a clearly-marked `*.prototype.*`/`scratch/` path; in that one case it is an authorized artifact, not shipped-change debris, and Step 6's cleanup leaves it alone. Absent that quote, the prototype is deleted and never appears in the change.

A prototype that changes the design sends you back to Step 3 (revise the recommendation) before you implement. Whenever a design-risk trigger was live - prototyped or deliberately skipped - the `PROTO:` line (Step 6) is owed.

## Step 4 - Act surgically

### Step 4 open - test-first, in vertical slices

When the change adds or alters behavior at a **public boundary that has (or can cheaply reuse) a test harness**, drive it test-first rather than writing code then back-filling tests. This governs the *order* of the work below.

- **Agree the seams first.** A seam is the public interface where you observe behavior without reaching inside. Before writing any test, name the seams under test and confirm them: with the user when attended; when unattended, write the seam list into the Step 3 recommendation before any test - naming them in advance, where they can be checked against what you actually tested, is the substitute for the user's confirmation. Name tests in the project's own domain vocabulary (`CONTEXT.md`, ADRs, existing test names) so they read as specifications. You cannot test everything - agreeing seams up front lands effort on critical paths and complex logic, not every edge case.
- **Red before green, observed (the discrimination proof).** Each cycle: write one failing test at a seam, **run it, and observe it fail for the expected reason** before writing any implementation. That observed-red is proof the test can distinguish a working system from a broken one. A test that passes on its **first** run is a surprise (Step 2 rule 7), not a green light - determine which cause it is: the test misses the intended path (fix its coverage); the behavior already exists (the change may be unneeded - back to Step 0/3); the fixture differs from the failing environment; or the assertion is tautological. **Never edit a test merely to force it red** (that is the fabrication Step 4 rule 8 forbids). For a bug fix, the red test must reproduce the bug and fail *because the bug is present*. "Saw it fail first" is the only observable difference between TDD and back-filled tests, so it is required. Record it on the `SEAMS:` line.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle; let each cycle teach the next. Do **not** horizontally slice (all tests, then all code) - bulk tests verify imagined behavior and go insensitive to real changes.
- **Tests verify behavior through public interfaces, never implementation details.** Avoid the anti-patterns: implementation-coupled (mocks internal collaborators / asserts via a side channel - breaks on refactor though behavior is unchanged), and tautological (the assertion recomputes the expected value the way the code does, so it can never disagree - expected values come from an independent source: a known-good literal, a worked example, the spec).
- **Refactoring is not part of the red -> green loop.** It belongs to the Step 4 close review, on a green baseline (see below), not the implementation cycle.
- **When TDD does not apply:** no testable seam (throwaway script, pure config, docs), or the project has no test harness for this area and adding one is larger than the change itself. Say so and rely on Step 5's observation instead. **Never add a test dependency to satisfy this gate** - that violates rule 8. Whenever a testable seam was present - driven test-first or deliberately skipped - the `SEAMS:` line (Step 6) is owed.

Test files for the seams you plan to touch are **inside the declared scope by default** - name them alongside the source files in Step 3 so the first test does not trip the surprise rule.

Now the numbered rules for every edit:

1. **Intent gate, before any behavior-changing edit** (under test-first, this means before the first *red test*, since the test encodes Y). Write one line: `INTENT: code does <X>; the failing check/task expects <Y>; the spec (README/docs/docstring) says <Z>`. You must actually open the README/docs/docstrings to fill the third slot, and if you change behavior this line must appear verbatim in your final report. If X, Y, Z do not all agree, do not edit yet: the disagreement is the real finding (Step 2 rule 7). Authority order when they disagree: an explicit user statement beats the spec, the spec beats the tests, the tests beat current code behavior. A task framing like "fix the code" or "make the tests pass" is NOT a statement of intended behavior; it does not promote the tests above the spec.
2. **Recall gate, before first use of anything you have not opened this session.** An API signature, endpoint, config key, price, figure, or regulation written from memory is not evidence. Stop and open its source now (the docs file, the library source, a fetched page; a fresh two-lookup budget as in Step 2), or, if no source is reachable, write it and label it in the report as memory, unverified. Discovering ignorance re-opens Step 2 exactly like a surprise does.
3. **Smallest correct change.** Touch only what the task needs. Match the existing style even if you would do it differently. (The test-first ordering above governs *when* tests and code are written; this rule governs *how much* each edit touches.)
4. **Precise edits over rewrites.** Rewrite a whole file only if you authored it this session or have fully read it.
5. **Track multi-part work.** Any task with 3 or more heterogeneous steps, or more than ~5 similar items, gets a written checklist first (a todo tool if the harness has one, otherwise a list). Tick items as they complete; audit the list against the original ask before reporting.
6. **Never destroy without looking.** Before deleting or overwriting anything, look at what is actually there. If it contradicts how it was described, stop and surface that.
7. **Failed-edit recovery ladder.** Re-read the exact region, adjust the match, retry once. Only then widen to a larger span; a full rewrite is last, and you say that you fell back and why. Never retry a failed call verbatim.
8. **Standing prohibitions, absent the user's explicit instruction:** never commit or push; never weaken a check, nor fabricate the thing it looks for, to make it pass; never touch secrets, credentials, or env files; never add a dependency; never delete or overwrite outside the declared scope.

### Step 4 close - two-axis review before you verify

When implementation is complete, review the change along **two independent axes**. Keep them separate - one axis passing must not mask the other failing. (Skipped for Small-band and trivial work; scale the depth to the diff - a single-hunk change gets a one-pass read against the done criterion and the smells visible in that hunk; reserve the full pass for multi-file changes or new behavior.)

1. **Materialize the diff.** Produce the actual change text to review, not your memory of it: `git diff` (plus `git diff --stat`) for the working tree, or `git diff <the pre-work ref>...HEAD` if you were given one. No repo: reconstruct the diff by re-reading each span in your declared scope list. Review *that text*.
2. **Run the two axes independently, in isolation.** If the harness supports subagents, run them as **two subagents each spawned fresh, given only the diff, the done criterion/spec, and the standards sources - never the conversation history, never your narrative of what you built, and never each other's verdict.** That artifacts-only isolation is what makes the separation real and stops a reviewer from rubber-stamping your intent instead of the code; do it whenever subagents are available. Without subagents, run two deliberate separate passes reading only the diff and the spec, not your memory of the work.
   - **Spec axis** - does the diff faithfully implement what was asked (the Step 0/1 done criterion, the plan, any originating issue/spec)? Report: requirements missing or partial; behavior added that nobody asked for (scope creep); requirements that look done but implemented wrong. Quote the asked-for line for each finding.
   - **Standards axis** - does the diff follow this repo's documented standards (any `CONTRIBUTING`/standards file), and is it free of code smells? Carry the smell baseline even when the repo documents nothing: mysterious name, duplicated code across hunks, feature envy, data clumps, primitive obsession, repeated switches, shotgun surgery, divergent change, speculative generality, message chains, middle man, refused bequest (each reads *what it is -> how to fix*; the full list with remedies is in `references/smells.md`). The repo's documented standard always overrides the baseline; skip anything tooling already enforces; each smell is a judgement call, never a hard violation.
3. **Report two lists, two counts. Never merge them, never pick a worst-overall finding across axes** - that reranking is the exact collapse the separation prevents. The `REVIEW:` line (Step 6) carries the two counts.

**Refactoring found here happens on a green baseline, not before verification.** Before any refactor, establish green: run the touched tests plus the build. Refactor only on green, re-run the same check after each refactor, and keep it inside files you already touched and only for a *hard* Standards violation (not a judgement call). A refactor larger than the change that provoked it is scope creep by the Spec axis's own definition - record it as a Step 6 follow-up instead of doing it now. A Spec-axis miss or hard Standards violation routes back into Step 4; **hard bound: after 2 review -> fix rounds on the same finding, stop, carry it as an explicit caveat, and move to Step 5.**

## Step 5 - Verify by observation

Verification has two halves, and a third when you fixed a defect:
- **(a)** the Step 1 done criterion passes, observed (it ran, it rendered, it counted), not inferred from reading the code;
- **(b)** the surrounding system still works: existing tests, build, or lint for the touched area (including the red -> green tests written in Step 4, now all green). A green targeted check with a broken build is a failed verification.

**Evidence standard (what counts as "observed").** A verification claim is only evidence if a fresh reader could reproduce it. For each (a)/(b) claim, hold: the **exact command or action** that produced the result (copy-pasteable; reference a secret by env-var name, never its value), and the **actual output** (the real last lines - exit code, pass/fail counts, the rendered value), not a paraphrase. "Tests pass" is not evidence; `pytest -q` -> `41 passed in 2.3s` is. Inference from absence counts only if you captured the absence (the empty result plus the query that produced it). Anything you could not run - no runtime, needs credentials, needs human eyes - is labelled unverified in the report, never dressed as observed. Read `references/evidence.md` before your first verification claim on full-band work; it is the binding definition.

**False-green defence (full-band coding work).** Two duties, both discharged on the `VERIFY:` line (Step 6):

- **Re-run, do not read.** "Re-run it yourself" means you executed the check, in this session, after the last edit. If your own post-edit run from the Step 4 close is already the most recent state with nothing changed since, cite that run - do not re-execute an identical check for its own sake. What is barred is claiming green from a log you did not produce (including a review subagent's assumption of green). This is not the "never re-read" rule (that governs re-reading unchanged sources, not re-running checks whose observed state changed).
- **Discrimination, scoped.** Applies only to the Step 1 done criterion of a task that **adds or changes observable behavior.** That check must be shown to discriminate a working system from a broken one: it failed before the change (the Step 4 observed-red is exactly this proof - if you have it, nothing more is owed), or it fails when you revert/disable the change. Order a revert experiment safely: revert by the cheapest reversible means (`git stash`, a one-line flag flip - never a hand-reconstructed revert), observe the failure, **restore, then re-run and observe green last.** If the change cannot be safely reverted (no VCS, multi-file hand edits), skip the revert, say so on `VERIFY:`, and rely on the Step 4 observed-red. **Never edit or weaken a check to force it red** - that is the fabrication Step 4 rule 8 forbids.
- **Where discrimination is NOT owed** (say so on `VERIFY:`, do not manufacture one): a change with no observable behavior change (pure refactor, perf, dependency bump, config/type-only, docs); the half-(b) regression checks, which are *supposed* to pass before and after; and the Question/assessment shape, which has nothing to revert.

**Bands:** Small-band and trivial work are exempt from both duties - their one existing check stands. Full-band work owes both. **Domain:** the discrimination/revert requirement is coding-only; under a domain adapter its stand-in is the adapter's own falsification rule (none if the adapter has none). The evidence standard (command + real output) applies in every domain.
- **(c) Twin check, whenever you fixed a defect.** A bug found in one place is presumed to recur elsewhere until you have searched. Name the exact wrong construct, search the whole project for it, and write one line that must appear verbatim in your report: `TWINS: searched <the pattern> - found <N> other sites: <files, or "none">`. Fix them or list them; a completeness claim with no search behind it is failure mode 14.

On failure, route: a mechanical mistake in the change goes back to Step 4; a failure that surprises you or contradicts your understanding goes back to Step 2. Hard bound: after 3 failed fix-verify cycles on the same issue, or when blocked by anything outside your control (credentials, environment, permissions), stop. Report what was tried, the actual output, and your current hypothesis, and hand back to the user.

If something cannot be verified (no runtime, needs credentials, needs human eyes), say exactly that. Never let an unverified claim pass as a verified one.

## Step 6 - Report outcome-first

- The first sentence answers "what happened" or "what did you find". Detail comes after. Never include step numbers, step names, or narrative method scaffolding in the report. The only permitted method artifacts are these short verbatim lines, each owed only when its trigger was present: `INTENT:` (behavior changed), `AUTH:` (outward action taken), `PENDING:` (prescribed follow-up deliberately not taken), `TWINS:` (a defect was fixed), the four gate lines - `GRILL:` (grill trigger present), `PROTO:` (design-risk trigger present), `SEAMS:` (a testable seam was present), `REVIEW:` (a full-loop coding change reached the Step 4 close) - and `VERIFY:` (Step 5 ran on full-band work). Formats:
  - `GRILL: asked <N> decisions; open decisions defaulted: <list, or "none">`
  - `PROTO: <trigger> - prototyped, verdict: <one line>`  OR  `PROTO: <trigger> present - skipped because <reason>`
  - `SEAMS: <seam(s)> - <N> red->green slices, each observed red first`  OR  `SEAMS: none testable (<why>) - verified by observation instead`
  - `REVIEW: Spec <N findings> / Standards <N findings> (2 isolated subagents | 2 separate passes)` (two counts, never merged)  OR  `REVIEW: skipped (Small-band / trivial)`
  - `VERIFY: <exact command> -> <real last line>; discrimination: <observed red in Step 4 | failed on revert: <output>, restored | n/a - <reason>>` (owed whenever Step 5 ran on full-band work; no command or no output = a fake, not a pass)
- Match the reader, not the work: the opening paragraph must be readable by someone who never saw the code or the data. Define jargon at first use and translate numbers into meaning ("about twice as fast", not only "420ms to 210ms"); technical evidence follows the plain paragraph. Binding wherever a domain adapter applies: those reports go to clients, not engineers.
- Complete sentences a teammate who stepped away can follow. Quote only the load-bearing lines - the verdict lines of a command's output (exit code, pass/fail counts, the decisive rows), never the whole transcript or full files.
- Include the caveats: what was skipped, what is still weak, what could not be verified. Failed things are reported as failed, with their output. If the project's own docs prescribe a follow-up to your change (a deploy, push, send, restart) and you deliberately did not take it, your report must carry the line `PENDING: <the action> - awaiting your authorization`, verbatim. No prescribed-but-untaken follow-up, no line.
- Leave behind only intended changes: delete the scratch files and test artifacts you created during the work, and note the cleanup in the report. The judge treats leftover debris as a fraud signal; do not hand it any.
- Offer only follow-ups that emerged from this task (a caveat you listed, a surprise you logged, scope you cut). If none emerged, end without follow-ups.
- Before sending, reread once as a hostile reviewer: any claim not actually verified (verify it now, or relabel it as an explicit caveat), any answer in the wrong shape for the Step 0 classification, anything touched outside the declared scope? Fix, then send.
- **Artifact gate, the last check before sending.** Sweep the finished report once against what this run owed, and repair it mechanically: behavior changed and no `INTENT:`; an outward action taken and no `AUTH:`; a prescribed follow-up deliberately untaken and no `PENDING:`; a defect fixed and no `TWINS:`; the grill trigger was present and no `GRILL:`; a design-risk trigger was present and no `PROTO:`; a testable seam was present and no `SEAMS:`; a full-loop coding change reached the Step 4 close and no `REVIEW:` line (its skip form counts); Step 5 ran on full-band work and no `VERIFY:` line, or a `VERIFY:` line missing its command or output. Add any missing owed line. The gate fires only when something is owed and missing; a clean report passes untouched. A gate whose trigger was absent owes no line - but for the four engineering gates, "trigger absent" must be a real judgment, not the cheap default (the `audit` mode treats a missing line whose trigger was plausibly present as a suspected fake).

## Compressed examples

**Task: "Fix the failing date test."**
Step 1: done = the full test suite passes, including the date test. Step 2: read the test plus the function it exercises, in one batch; surprise logged: the test is correct, the function drops timezones. Step 4: one edit in the function. Step 5: suite run, green, output shown; nothing else touched. Step 6: "The test was right; `formatDate` dropped the timezone offset. Fixed in one line, all 42 tests pass."

**Question: "Why is the dashboard slow?"**
Step 0: assessment; change nothing. Step 1: done = a cause backed by observations, every claim citable. Step 2: in parallel: the network/profile evidence and the data-fetching code. Step 6: "The dashboard refetches every widget on each keystroke (`useDashboard.ts:41`, no debounce, no cache). The fix would be a 300ms debounce plus query caching. Want me to make that change?" No edits made.

## Modes

**plan** - run Steps 0 to 3 and stop (before Step 3.5; "Steps 0-3" excludes the 3.5 prototype phase). Deliver: the classification, the definition of done with its verification, the evidence found (with citations), one recommended approach with alternatives dismissed in a line each, and - when a design-risk trigger is live - the named risk plus whether you recommend a Step 3.5 prototype before implementation, and the seams you propose to test. Do not touch any file. **On approval, a plan resumes at the design-risk gate (Step 3.5), not at implementation** - the prototype phase is not skipped just because planning "finished" Step 3.

**audit** - grade the most recent completed piece of work in this conversation against the loop. For each step, mark it followed, skipped, or faked (claimed without observation); include the four engineering gates (grill in Step 1, prototype at 3.5, test-first in Step 4, two-axis review at the 4 -> 5 close) **and the three verification fold-ins (evidence capture, the discrimination check, reviewer isolation)**, judging each as correctly-applied, wrongly-skipped, or faked - a skipped gate is only a finding when its trigger was actually present (a design risk for prototype, a testable seam for TDD). A `VERIFY:` line with no command or no output is a fake; a trivial-band declaration on work that touched 2+ files or added behavior is a suspected fake. For every skip or fake, name the concrete risk it created; `references/failure-modes.md` maps symptoms to steps. Deliver a short table plus the single highest-value fix, and apply that fix only if the user asks.

**report** - apply the Step 6 checklist to the answer you were about to send: outcome in the first sentence, load-bearing quotes only, caveats present, follow-ups only if they emerged from the work, hostile-reviewer reread done. Rewrite it, do not send the original.
