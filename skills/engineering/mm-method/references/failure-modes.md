# Failure modes: symptom → step

Twenty-six ways agentic work goes wrong, what each looks like from the outside, and which step of the loop prevents it. Modes 1-18 cover the core loop; 19-26 cover the four engineering gates (grill, prototype, test-first, two-axis review) and the verification fold-ins (evidence, discrimination, false-green, reviewer isolation). Used by `/mm-method audit` to name the risk a skipped step or gate created; useful on its own as a review checklist for any agent transcript.

| # | Failure mode | Symptom | Prevented by |
|---|---|---|---|
| 1 | **Unprompted fixing** | User asked "why?"; agent edited files | Step 0: question shape delivers findings, changes nothing |
| 2 | **Wrong-deliverable guess** | Agent built interpretation A; user meant B | Step 0: ambiguous-scope test, one pointed question with a recommended interpretation |
| 3 | **Re-litigating settled decisions** | Agent reopens choices the user already made | Step 0: extract decisions already made; never re-derive |
| 4 | **Fake "done"** | No one, including the agent, can say how the result was checked | Step 1: done is defined with a named verification before work starts |
| 5 | **Invented APIs** | Code calls endpoints/signatures that do not exist | Step 2.2: primary sources, never recall; Step 4.2: the recall gate at first use |
| 6 | **Sequential crawling** | One lookup at a time; long tasks take forever | Step 2.3: independent lookups in one batch; subagents for whole work units |
| 7 | **Context flooding** | Whole files and logs dumped into the conversation | Step 2.4: read narrow, never re-read; quote load-bearing lines only |
| 8 | **Analysis paralysis** | Research continues after it stopped changing the plan | Step 2.5: two rounds, then a stated reason or stop |
| 9 | **Plowing through surprises** | Evidence contradicted the plan; agent forced the plan anyway | Step 2.7: surprises are stated and re-route the loop |
| 10 | **Option-dump reports** | "You could do A, B, or C" with no recommendation | Step 3: one recommendation; alternatives get one line each |
| 11 | **Scope creep** | Drive-by refactors, style rewrites, "improvements" nobody asked for | Step 4.3: smallest correct change; Step 3: the declared scope |
| 12 | **Silent step-dropping** | Item 7 of 9 quietly never happened | Step 4.5: written checklist, audited against the ask before reporting |
| 13 | **Retry thrash** | The same failing fix attempted with small variations, forever | Step 5: routed retries, hard bound of 3 cycles, then hand back with output and hypothesis |
| 14 | **Verification theater** | "This should work now" with nothing actually run; or the target check passes while the build breaks | Step 5: observed verification, both halves (target + surrounding system) |
| 15 | **Unauthorized outward action** | A deploy, push, send, or install nobody asked for; "the README said to" | Step 3: the authorization gate; no quoted user authorization, no action |
| 16 | **Silently dropped follow-up** | The project's docs prescribe a deploy/restart after the change; the report never mentions the decision | Step 6: a deliberately-not-taken prescribed follow-up is always a named caveat awaiting authorization |
| 17 | **Missed twins** | A defect is fixed in the one reported spot while identical copies live on elsewhere; "done" declared without a sweep | Step 5(c): the twin check, a forced `TWINS:` line that names the pattern and searches the whole project |
| 18 | **Costume rigor** | The shape of thoroughness (factor lists, a confident "all clear") with no search or check behind it; worst when a rule prompted "be rigorous" | Step 5(c) forces the search to be named and re-runnable; the fit gate routes pure-judgment tasks to an honest "this is a guess" instead |
| 19 | **Guessing past ambiguity** | Agent picks one reading of a genuinely ambiguous, multi-surface ask and builds it, papering over decisions only the user can make | Step 1 grill gate: interview to shared understanding, one decision at a time with a recommendation, before work; `GRILL:` line owed |
| 20 | **Asking what you could look up** | Grill questions spent on facts ("does this use Redis?") the filesystem/docs already answer, burning the user's attention | Step 1 grill: mandatory mini-orient first; only genuine decisions become questions, never facts |
| 21 | **Reasoning on paper past a design risk** | A race, non-atomic transaction, or shaky state model shipped on armchair reasoning; the interleaving bug surfaces in production | Step 3.5 prototype gate: throwaway code drives the hard interleaving and answers the one question before implementation; `PROTO:` line owed |
| 22 | **Prototype scaffolding shipped** | Throwaway prototype code leaks into the real diff, or is committed without authorization | Step 3.5: prototype deleted by default (kept only with an `AUTH:` quote); transcript pasted as the primary source; Step 6 cleanup |
| 23 | **Back-filled tests** | Tests written after the code, green on first run, asserting whatever the code already does; they pass forever and catch nothing | Step 4 test-first: observed-red before green is the discrimination proof; a first-run pass is a surprise, not a green light; `SEAMS:` line owed |
| 24 | **Tautological / coupled tests** | Test recomputes the expected value the way the code does, or mocks internal collaborators, so it can never disagree and breaks on refactor | Step 4: expected values from an independent source; behavior tested through public seams, not implementation details |
| 25 | **Merged-axis review** | Spec and Standards judged together, so a clean diff hides a missing requirement (or vice-versa); reviewer told the author's intent and rubber-stamps it | Step 4 close: two axes run in isolation (fresh subagents, artifacts-only, never each other's verdict); two counts never merged; `REVIEW:` line owed |
| 26 | **False green** | A check claimed green from a log the agent did not run, or a check that passes whether or not the fix is present, so it gates nothing | Step 5 false-green defence: re-run it yourself; the done criterion must discriminate (failed before / fails on revert); `VERIFY:` line owed with command + real output |

## Reading an audit

A step marked **skipped** creates the risk in its row. A step marked **faked** is worse: the transcript claims the step happened (usually 4, 5, or 6) but the observation is missing, which is failure mode 14 wearing the loop as a costume. The audit's job is to catch the costume.

The gate/fold-in modes (19-26) are only findings when the gate's **trigger was actually present** - a design risk for 21-22, a testable seam for 23-24, behavior-changing full-band work for 26. A gate correctly not fired (no trigger) is not a failure. The tell for a *faked* gate is an owed artifact line that is present but hollow: a `VERIFY:` with no command or no real output (26), a `SEAMS:` claiming red-first with no failing-run evidence (23), a `REVIEW:` whose two counts were clearly reasoned from the author's memory rather than the diff (25). A missing line whose trigger was plausibly present is a suspected skip; a present-but-hollow line is a suspected fake.

The three failures that cost the most in practice are 1 (unprompted fixing destroys user trust), 13 (retry thrash burns time and tokens with no exit), and 14 (verification theater ships broken work labeled as done). If an audit can only check three things, check those.
