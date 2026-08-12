# The four engineering gates - worked examples

Concrete walk-throughs of the grill (Step 1), prototype (Step 3.5), test-first (Step 4), and two-axis review (Step 4 close) gates. Each shows the trigger, the work, and the owed report line. Gate concepts adapted from matt-pocock/skills; evidence/negative-test and false-green discipline from debug-pipeline2 (see repo `THIRD_PARTY_NOTICES.md`).

Read the SKILL first; this file is the "show me" companion.

---

## Grill (Step 1) - decisions, not facts, one at a time

**Task:** "Add rate limiting to the API."

**Trigger present?** Yes - "rate limiting" hides several decisions (scope, limit, identity, over-limit behavior). Attended. Grill fires.

**Mini-orient first (resolve facts by looking, never ask):**
- List routes -> the API is `express` with an existing `middleware/` dir. (fact, found)
- Grep for an existing limiter -> none. (fact, found)
- Check for a shared store -> `redis` client already configured in `db/redis.ts`. (fact, found)

**Now the genuine decisions, one at a time, each with a recommendation:**
1. "Rate-limit all routes, or only the auth + write endpoints? *I recommend auth + writes only* - read-only GETs are cheap and limiting them hurts legit use." -> user: "auth + writes."
2. "Limit key: per-IP or per-authenticated-user? *I recommend per-user with per-IP fallback for unauthenticated routes.*" -> user: "per-user, IP fallback."
3. "Over-limit response: 429 with `Retry-After`, or silent drop? *I recommend 429 + `Retry-After`* - it's the standard and clients can back off." -> user: "429."

Stop - three decisions settled, remaining unknowns (exact numbers) are reversible config. Do not ask them; pick sane defaults and note them.

**Owed line:** `GRILL: asked 3 decisions; open decisions defaulted: limit=100/min per user (tunable via env)`

**Anti-example:** asking "does the project use Redis?" is a *fact* - you look that up, you never spend a question on it.

---

## Prototype (Step 3.5) - throwaway code answers one question

**Task:** "Let two workers claim jobs from the queue without ever double-processing one."

**Trigger present?** Yes - concurrency / race condition on state this change writes, and correctness depends on interleaving. Not answerable by reading alone. Prototype fires. (If a single `SELECT ... FOR UPDATE SKIP LOCKED` already existed and was documented, you would read it and skip.)

**The one question:** "Under real concurrency, does the single-statement `UPDATE jobs SET owner=? WHERE id=(SELECT id FROM jobs WHERE owner IS NULL ORDER BY id LIMIT 1)` ever let two workers claim the same row?"

**Throwaway harness** (next to the queue module, `queue/claim_race.prototype.ts`, one command to run). Header states the engine and isolation level (the answer depends on both): **Postgres 16, READ COMMITTED**. Seed **2** claimable jobs so starvation is visible, and loop the interleaving **200 times**, asserting each run:
- exactly one worker gets `rowCount === 1` for a given row (no double-claim), and
- both jobs eventually get claimed (no starvation).

**Verdict captured (pasted into the report):**
```
engine=postgres16 isolation=read_committed jobs=2 runs=200
double-claim events: 0/200   (one rowCount=1, one rowCount=0 every run)
starvation: 138/200 runs left job#2 unclaimed while a worker idle-looped
```
Decision: the guarded single-statement UPDATE **prevents double-claim** but the `LIMIT 1` subselect **starves** free jobs under contention. Switch the plan to `SELECT ... FOR UPDATE SKIP LOCKED`, which both serializes and lets each worker take a *different* free row. Fold that into the plan; **delete the prototype** (no AUTH quote to keep it). The transcript above is the primary source.

**Owed line:** `PROTO: race on job-claim - prototyped (pg16/read-committed, 200 runs), verdict: guarded UPDATE prevents double-claim but LIMIT-1 subselect starves; use FOR UPDATE SKIP LOCKED`

**Negative-gate example (do NOT prototype):** "Which of two button colors looks better?" on a reversible local style - that is a judgement, not an emergent-behavior risk; just pick one and move on.

---

## Test-first (Step 4) - seams, observed red, one slice

**Task:** the rate limiter from the grill example.

**Seam agreed:** the middleware's public behavior - "the 101st request in a window from one user gets a 429 with `Retry-After`." (Named in Step 3 / confirmed with user. Not the internal counter - that is an implementation detail.)

**Slice 1, red first:**
```
test: "allows 100 then 429s the 101st for one user"
run -> FAIL: expected 429, got 200 (limiter stubbed as pass-through)   # observed red, right reason - stub first so the failure is a clean assertion, not an import error
```
Implement the minimum: counter keyed by user in Redis, 429 past the limit.
```
run -> PASS
```
**Slice 2, red first:** "resets after the window elapses" -> run -> FAIL (no expiry) -> add TTL -> PASS.

**Test isolation (so Step 5 can re-run):** flush the limiter keyspace in `beforeEach`, and take the window length from the config constant the Standards axis extracts so the test sets it to 50ms rather than sleeping 60s. Without this, the suite passes once then 429s request 1 of the next run - and the false-green re-run would fail.

The 429 status and `Retry-After` header come from the user's confirmed decision and the HTTP spec - independent sources. The number 100 is our own default, so it is a *parameter* of the test, not evidence: the test asserts "the (N+1)th request 429s" with N read from config. No internal mock (no implementation coupling); no expected value recomputed from the code (no tautology).

**Owed line:** `SEAMS: rate-limit middleware (429 past limit; window reset) - 2 red->green slices, each observed red first`

**Escape example (full-band, genuinely no seam):** a one-off data-migration script in `scripts/` where the project has no harness for scripts and adding one is larger than the migration. Skip TDD, verify by running it against a copy and diffing row counts. `SEAMS: none testable (throwaway migration, no harness for scripts/) - verified by observation instead`. (A one-line copyright-year bump is *trivial-band* - it skips the whole loop and owes no line at all.)

---

## Two-axis review (Step 4 close) - Spec and Standards, kept apart

**Task:** the rate limiter, implementation complete.

1. **Materialize the diff:** `git diff --stat` ->
   ```
    middleware/rateLimit.ts      | 48 ++++++++++++
    middleware/rateLimit.test.ts | 40 +++++++++
    app.ts                       |  3 +
    3 files changed, 88 insertions(+), 3 deletions(-)
   ```
   Then read the full `git diff` text, not memory.
2. **Two isolated passes** (as two fresh subagents, each given only the materialized diff, the written done criterion + `GRILL:` decisions, `CONTRIBUTING.md`, and read-only repo access for context - never the conversation transcript, your narrative, or the other axis's verdict):
   - **Spec axis** (against the grill decisions): auth+writes only? yes. per-user + IP fallback? **IP fallback missing** - the diff keys straight off `req.user?.id`, so unauthenticated requests would key on `undefined`; there is no IP branch. Finding: requirement partial (a hypothesis from the diff, to be re-observed by running - not asserted as a runtime fact). Quote: "per-user, IP fallback."
   - **Standards axis:** a magic `100` and `60000` inline -> *mysterious value (magic literal)*; extract to named config. Duplicated key-building in two handlers -> *duplicated code*.
3. **Report, never merged:** `REVIEW: Spec 1 / Standards 2`.

The Spec-axis miss (IP fallback) is a hard miss -> route **back to Step 4**, add the fallback *as its own observed-red slice* (so the final `SEAMS:` line reads 3 slices, not 2 - gate lines are reconciled after a review->fix round, not written once), then re-review. The two Standards smells: establish green first (`npm test` passes), then extract the config constant and the shared key-builder on that green baseline, re-running the tests after. A refactor bigger than the fix would instead be filed as a follow-up, not done now.

**Then Step 5:** re-run the suite yourself and paste the real last line - do not treat the review's assumption of green as verification. No separate revert-check is owed here: slices 1 and 2 were observed red, which is the discrimination proof. `VERIFY: npm test -> 12 passing (0 pending) -> ...; discrimination: observed red in Step 4`. Report outcome-first.

---

## How the gates chain (one line)

grill sharpens the ask -> evidence -> plan names seams + any design risk -> (prototype settles the risk) -> test-first builds it red->green -> two-axis review catches spec/standards misses -> verify by observation with the false-green defence -> report with the four owed lines.
