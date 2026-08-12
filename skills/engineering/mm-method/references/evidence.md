# Evidence standard (binding)

"Observed" and "verified" enforce nothing as adjectives. This file makes them checkable. The loop cites this from Step 2 (capture as you go) and Step 5 (verify by observation); read it before your first verification claim on full-band work. Adapted for generic coding from the debug-pipeline2 evidence standard (see repo `THIRD_PARTY_NOTICES.md`).

## What an evidence item is

A claim that will appear in the report, or that gates a verification, must be backed by an item a fresh reader could reproduce:

- **claim** - one falsifiable sentence. "The cache works" is not a claim. "`GET /items` returns a 200 with 3 rows on the second call without hitting the DB (query log empty)" is.
- **command / action** - the exact, copy-pasteable command, request, or click-path that produced the result. A secret is referenced by its env-var name, never its value.
- **output** - the real output, verbatim (the last lines that carry the verdict: exit code, pass/fail counts, the rendered value, the row). Never a paraphrase, never "it worked".
- **when** - a timestamp/run context, needed only when you compare two samples (a before/after, or two runs); a single one-off check does not need it.

You do not need JSON files or hashes for ordinary coding work - that ceremony belongs to long-running audit protocols. You *do* always need three things for any claim that reaches the report: the command, its real output, and reproducibility. The optional part is only the timestamp/run context above.

## Rejected as evidence

- Recollection or paraphrase ("tests pass", "the endpoint returns the user").
- "Should", "presumably", "appears to", "likely", "I believe" - **inside an evidence item.** (These words are correct, even required, when you are explicitly reporting a hypothesis, a low-confidence answer, or a caveat - they are banned only when dressing a guess as evidence.)
- A summary with no command behind it.
- Inference from absence - **unless the absence is captured**: the empty result set *plus* the query/command that produced it.
- A screenshot with no capture context.
- Reading a log that some other step (or agent) produced and treating it as your own verification. Re-run it.

## Negative evidence: a behavior-changing check must be able to fail

This applies to the done criterion of **coding, full-band work that adds or changes observable behavior.** It does NOT apply to no-behavior-change work (refactor, perf, dependency bump, config/type-only, docs), to half-(b) regression checks (which are supposed to pass before and after), to Question/assessment-shape work (nothing to revert), or to Small-band and trivial work. Where it does not apply, say so on the `VERIFY:` line - never manufacture a discriminating check, and never edit a good check to force it red. Under a non-coding domain adapter the stand-in is the adapter's own falsification rule (none if it has none).

Where it does apply: a check is only trustworthy once it has been seen to fail. A test that is green whether or not the fix is present proves nothing.

- **In TDD (Step 4):** the observed-red step *is* the negative test - you watched the test fail for the right reason before writing code.
- **For a bug fix:** the reproduction test must fail *because the bug is present*, then pass once fixed. If it is green before your change, it does not test the bug.
- **For a verification you did not write as a test** (a script, a manual check): confirm it returns false when you revert the change or inject the broken condition, at least once. A check with no demonstrated failure mode gates nothing.

## False green

The most dangerous outcome is a check that passes while the system is broken. Two rules prevent it:

1. **Re-execute, do not review.** The verifier runs the check itself and reproduces the output. Reading a passing log another step generated is not verification.
2. **Prove the check discriminates.** See "negative evidence" above. A control that cannot fail is not a control.

(Both apply to any non-trivial task; trivial-band work relies on its single obvious check.)

## Unverifiable is a first-class outcome

If something cannot be run - no runtime, needs credentials, needs human eyes, external system down - say exactly that, in the report, labelled unverified. An honest "could not verify (needs staging credentials)" is correct; an unverified claim dressed as observed is failure mode 6.
