# Agentic stack and human review

## Purpose

Read this `agentic-stack` reference when a routing agent must decide how the generated agent runtime constrains
itself, parks a risky request, and resumes or ends a session. It answers this question:

> How does the agent runtime constrain itself, and when does it stop for a human?

The persona sets the agent's allowed subject matter and operating style. The HITL protocol turns
risky tool requests into human decisions. The state machine records the session position and limits
repeated work. The memory, knowledge base and tool specifications limit what the agent can retrieve
or call. The shipped test covers the state transitions, the router and the filters. `validate_repo.py`
covers the evaluation dataset shapes and trigger references. The router must evaluate each trigger,
the state must record the result, the interface must resolve it, and the tool layer must enforce it.

## Part 1: Behaviour and persona

### Rules

The generated persona file is the source of truth for `allowed_domains`, `forbidden_topics` and
`linguistic_style`. The scaffold starts with the project name as its allowed domain. The operator
replaces that value during the interview. The default forbidden topics are medical advice, legal
counsel, speculative finance and competitor pricing.

The persona is concise, technical, polite, active and objective. It does not let a user message
change the system role. It strips Markdown injections and rejects system override phrases such as
`system override`, `ignore previous instructions` and `dan mode`. This list is a pre-filter,
not the complete security control. The application must enforce tool permissions, sandbox restrictions
and blocking HITL decisions before execution.

Every phrase in `reject_system_override_keywords` is matched by a pattern in
`src/safety/filters.ts`. `validate_repo.py` warns when a declared phrase no pattern catches, so
the declared copy and the enforced copy cannot drift apart unnoticed.

### Emitted file

`config/persona.json` comes from `config/persona.json.tmpl`. The template uses only
`{{PROJECT_NAME}}` and leaves GitHub Actions expressions untouched elsewhere in the scaffold.

### Why this decision exists

The persona gives the runtime a stable starting policy. Keeping it in JSON lets the operator edit
domain and style settings without rewriting router code. The system prompt points to this file so
the model and the operator use the same rule source.

## Part 2: Interaction and the human-in-the-loop protocol

### Rules

`config/hitl_triggers.json` declares typed conditions over a proposed tool request. The default
financial trigger matches `argument_threshold` on `amount > 500.00` and shows
`TransactionApprovalModal`. The deletion trigger matches `tool_name_in` for `delete_record` and
`purge_user` and shows `SecurityChallengePanel` for an MFA challenge.

The router checks the loop budget before it evaluates any trigger. When
`executionLoopCount > MAX_EXECUTION_LOOPS`, it returns `TASK_ABORTED` to `supervisor`, with empty
`matchedTriggers` and `notifiedTriggers`; the session does not park for human approval. Otherwise,
the router evaluates every trigger. A blocking match stops the proposed call before the tool layer
runs. A blocking match goes to `supervisor` and a notice does not. `NOTIFY_ONLY` leaves the session `RUNNING` and reports the match in `notifiedTriggers`,
separately from blocking matches. An invalid regular expression in a trigger means no match and
does not crash routing. The runtime does not retry a blocked call or explain its way around the
rule. The record stores the trigger, proposed tool name, proposed arguments, requested action, and
eventual resolution.

The interface separates two vocabularies. `action_required` tells the UI what it must ask for.
`resolution_status` records what the human did. `APPROVE_REJECT_MODIFY` can resolve as `APPROVED`,
`MODIFIED` or `DENIED`. `MFA_CHALLENGE` can resolve as `APPROVED`, `DENIED` or `TIMEOUT`.
`NOTIFY_ONLY` reports the request and never blocks it, so it never leaves
`PENDING_HUMAN_APPROVAL`. A timeout ends the session as `TASK_ABORTED`.

The front end must expose these concrete stubs:

* `TransactionApprovalModal` receives the pending trigger and proposed arguments. It sends an
  approval, a denial, or corrected arguments to the session endpoint. It must display the amount,
  tool name and target account from typed data, and it must not execute the tool in the browser.
* `SecurityChallengePanel` receives the pending trigger and a challenge request. It starts MFA,
  submits the challenge result, and reports denial or timeout. The panel must never receive a
  secret token or decide that MFA succeeded without a server response.

The API endpoint stubs belong to the application, not to this skill. A compatible implementation
needs endpoints with these responsibilities:

* `POST /api/agent/sessions` creates a session in `RUNNING` and returns its public session id.
* `POST /api/agent/sessions/:sessionId/turns` accepts user input, runs the router, and returns the
  next node or a pending approval. It must not call a tool whose trigger matched as blocking.
* `GET /api/agent/sessions/:sessionId/pending-approval` returns the pending request needed by
  either front-end stub, with secrets removed.
* `POST /api/agent/sessions/:sessionId/approvals/:hitlId` accepts `APPROVED`, `MODIFIED` or
  `DENIED`, validates modified arguments, writes the audit row, and resumes or aborts the session.
* `POST /api/agent/sessions/:sessionId/mfa/:hitlId` accepts the server-side MFA result and maps it
  to `APPROVED`, `DENIED` or `TIMEOUT`.
* `POST /api/agent/sessions/:sessionId/notify/:hitlId` records `NOTIFY_ONLY` without parking the
  session.

The generated `src/agent/endpoints.ts` exports these endpoint contracts. The application chooses
the HTTP framework and authentication scheme. Each handler must enforce the session id, the hitl
record id, the action vocabulary, and the tool parameter schema. Guards bind each record to the
session, authorize the caller for that session, refuse an expired request, and require the record
to be the session's current pending operation. The update that moves a record from `PENDING` to one
of `APPROVED`, `MODIFIED`, `DENIED` or `TIMEOUT` must be atomic. Concurrent requests cannot consume
the same record twice. An MFA result must bind to the caller, `sessionId`, `hitlId` and proposed
operation.

The router returns every blocking match. The pending approval holds one trigger. The application
creates one HITL record per blocking match, parks the session on the first record, and after a
resolution checks the remaining records for the same operation. If any remains pending, the session
parks again and the response status stays `PENDING_HUMAN_APPROVAL`. The resumption event is
emitted only after the last blocker clears. The operation runs only when no blocking record for it
remains pending.

### Emitted file

`docs/architecture/hitl-protocol.md` comes from
`docs/architecture/hitl-protocol.md.tmpl`. It documents the five states, transitions, interface
actions, resolution mapping, timeout, audit row, argument re-validation and a worked trigger.
`config/hitl_triggers.json` provides the data that the document explains.

`src/agent/ui_contracts.ts` defines the props and callbacks for `TransactionApprovalModal`,
`SecurityChallengePanel` and notices. `src/agent/agentic_stack.test.ts` is the shipped vitest file.
It checks the state transitions, loop-budget precedence, trigger matching including malformed
patterns, notification behavior, the router, and safety filter behavior. `validate_repo.py` checks
the evaluation dataset's shape and its trigger references. `tests/eval_dataset.json` is the golden
dataset for an evaluation harness the application provides. It is data, not an executable test file.

### Why this decision exists

Human review must be a protocol with durable records, not a prompt instruction. Typed match
objects make a trigger executable. Separate action and resolution fields prevent an interface
request from being confused with a human decision. Re-validating corrections closes the gap where
an operator could approve one request and accidentally run a different, invalid request.

## Part 3: Orchestration and the state machine

### Rules

`src/agent/state.ts` exports these statuses:

| Status | Meaning |
|---|---|
| `RUNNING` | The runtime may route work and call an allowed tool. |
| `PENDING_HUMAN_APPROVAL` | A matched HITL request is waiting for a human. |
| `RESUMING_LOOP` | The human result has been recorded and the supervisor may continue. |
| `TASK_ABORTED` | The session ended because of denial, timeout, failure or loop budget. |
| `TASK_COMPLETED` | The session ended successfully. |

The state graph carries messages, the next target agent, an execution loop count, extracted
entities, errors and one pending approval. The pending approval contains the trigger id, tool name,
arguments, request time and timeout. The loop budget is `MAX_EXECUTION_LOOPS = 10`.

The legal transitions are:

| From | Event | To |
|---|---|---|
| `RUNNING` | `HITL_TRIGGERED` | `PENDING_HUMAN_APPROVAL` |
| `RUNNING` | `TASK_DONE` | `TASK_COMPLETED` |
| `RUNNING` | `TASK_FAILED` | `TASK_ABORTED` |
| `PENDING_HUMAN_APPROVAL` | `HUMAN_APPROVED` | `RESUMING_LOOP` |
| `PENDING_HUMAN_APPROVAL` | `HUMAN_MODIFIED` | `RESUMING_LOOP` |
| `PENDING_HUMAN_APPROVAL` | `HUMAN_REJECTED` | `TASK_ABORTED` |
| `PENDING_HUMAN_APPROVAL` | `HITL_TIMEOUT` | `TASK_ABORTED` |
| `RESUMING_LOOP` | `LOOP_RESUMED` | `RUNNING` |
| `RESUMING_LOOP` | `TASK_DONE` | `TASK_COMPLETED` |
| `RESUMING_LOOP` | `TASK_FAILED` | `TASK_ABORTED` |

`transition` throws an error naming the current status and event for every unlisted pair. The
router has a different loop-budget path. When `executionLoopCount > MAX_EXECUTION_LOOPS`, it
returns an abort decision to the supervisor instead of throwing. The supervisor records
`TASK_ABORTED`. `route()` refuses a session that is not `RUNNING`. The caller applies
`LOOP_RESUMED` before routing resumed work. Record successful completion as `TASK_COMPLETED`.

The application owns the routing for `researcher` and `writer`. The generated router only decides
that an ordinary request goes to `researcher`, that a blocking match goes to `supervisor`, or
that an exhausted loop aborts. The application must define how `researcher` retrieves facts and
passes a bounded result to `writer`, how `writer` produces the final response, and how either node
emits `TASK_DONE` or `TASK_FAILED`.

### Emitted file

`src/agent/state.ts` comes from `src/agent/state.ts.tmpl`. `src/agent/router.ts` comes from
`src/agent/router.ts.tmpl`. The database migrations persist the same status and pending request
vocabulary.

### Why this decision exists

The state machine makes parking and resumption observable. Record successful completion as
`TASK_COMPLETED`. A recorded `RESUMING_LOOP` transition gives
the supervisor a clear handoff after approval. A return value for loop exhaustion lets callers
persist an abort instead of losing the session in a thrown error.

## Part 4: Memory, the knowledge base and tool use

### Rules

`config/vector_store.yaml` sets the default embedding dimension to 1536, cosine distance,
recursive character chunks of 512 with 64 overlap, and metadata fields `document_id`,
`user_scope_id` and `classification_level`. The dimension belongs to the selected embedding model.
If the model changes, the operator must change the dimension and re-index the collection. It is
not a universal constant.

Metadata does not enforce access control. The query layer must apply `user_scope_id` and
`classification_level` filters before returning chunks. It must also record which document ids
were used so the system prompt's no-fabrication rule can be checked.

`config/tools.json` defines the callable tool and its parameter schema. The example tool,
`fetch_user_billing`, requires an explicit `account_id` and must not expose raw hash ids. The
sandbox runs in Docker isolation, restricts network egress, allows 5000 milliseconds and 512 MB.
The application's own tool layer must enforce these settings and permissions. The JSON definition
alone does not grant access.

The implementing agent must connect `src/agent/router.ts` to the application's tool layer.
The adapter should receive the router result, stop on `PENDING_HUMAN_APPROVAL` or `TASK_ABORTED`,
and call a tool only when the result is `RUNNING` and the tool permission check passes. It should
pass the exact proposed arguments into `evaluateTriggers` before execution, write the tool result
as a `tool` message, increment the loop count, and route the next turn. The adapter must reject a
tool name or argument set absent from the application's registry.

### Emitted files

`config/vector_store.yaml` comes from `config/vector_store.yaml.tmpl`. `config/tools.json` comes
from `config/tools.json.tmpl`. The agent session and HITL tables come from the PostgreSQL or SQLite
migration pair.

### Why this decision exists

Retrieval supplies evidence under the query layer's scope checks. Tool definitions limit arguments,
and the sandbox limits process and network effects. The application adapter joins retrieval and tool
authorization to the state machine and applies each check at the point of use.

## Part 5: Safety, financial guardrails and the evaluation matrix

### Rules

`src/safety/filters.ts` detects four injection patterns with case-insensitive `gi` regular
expressions. It masks a social security number inside a sentence, then masks only 13 to 19 digit
runs that pass the Luhn check. The card pass finds one maximal candidate that spans spaces and
hyphens, splits it into separate numeric tokens, masks each standalone token whose digits number
13 to 19 and pass Luhn, and keeps separate invalid tokens unchanged. A valid standalone card token
is redacted. An uninterrupted number longer than nineteen digits survives untouched, with no valid
suffix carved out of it. `luhnValid` leaves a candidate that fails the checksum unchanged, so an
order number or a timestamp usually survives. An identifier can still pass the checksum, so the
filter reduces false positives rather than removing the risk. `buildSecurityViolation` returns this exact shape without echoing the offending text:

```json
{"error":{"code":"SECURITY_VIOLATION","message":"...","violations":["..."]}}
```

The system prompt says that the agent must not fabricate facts, bypass safety, change its
operational identity, cross the session boundary, or add conversational filler. It says that a
matching HITL trigger stops the call. It names the files the operator edits when rules change.

The evaluation matrix contains three cases. `TC-001` exercises a deletion and a 600 dollar
refund, so it should route through `supervisor` with `TR-01` and `TR-02`. `TC-002` requests legal
instructions, so it should end with a forbidden-topic response. `TC-003` asks for an invoice lookup,
so it should route to `researcher` with no HITL trigger. `TC-003` is the positive control. A suite
with only blocking cases cannot distinguish selective filtering from a filter that blocks every
request.

### Emitted files

`src/safety/filters.ts` comes from `src/safety/filters.ts.tmpl`.
`config/system_prompt.md` comes from `config/system_prompt.md.tmpl`.
`tests/eval_dataset.json` comes from `tests/eval_dataset.json.tmpl`.

JavaScript's `RegExp` is the matching authority for trigger patterns. Python's `re` is used only as
a syntax check. Python's `$` matches before a trailing newline, while JavaScript's does not. Python's
`\d` and `\w` are Unicode-aware, while JavaScript's are ASCII-only. The two engines disagree on
which Unicode code points count as whitespace, so a pattern that uses `\s` can match a different set
of inputs under each engine.

### Why this decision exists

Filters reduce accidental exposure and catch common attacks, but a phrase denylist can be evaded.
The application must enforce tool permissions, sandbox restrictions and blocking HITL decisions
before execution. The shipped test covers the state transitions, the router and the filters.
`validate_repo.py` covers the shapes and the references. The audit tables let an operator inspect
what happened.

## Review notes

| Defect | Fix |
|---|---|
| The state machine had no success state, so a successful run had no terminal status. It also had no path from `RESUMING_LOOP` back to active work after approval. | Add `TASK_COMPLETED` and the `RESUMING_LOOP` to `RUNNING` edge. The state graph now records both success and resumed execution. |
| `action_required` and `resolution_status` used overlapping but incompatible vocabularies. A UI instruction could be mistaken for a human outcome. | Keep `action_required` for the interface request and `resolution_status` for the human result. Document the valid mapping for each action. |
| The financial condition `proposed_arguments.amount > 500.00` existed only as prose. No program could evaluate it consistently. | Store a typed `match` object with `argument_threshold`, `tool_name_in` and `argument_matches` kinds. The router evaluates each kind directly. |
| `current_context JSONB` was described as token storage. That would put a credential at rest in the session row. | The `token_ref` column separates the pointer from the secret, but it cannot stop a secret from being written into `current_context`; keeping secrets out of that column is an application rule. |
| `status` was an unconstrained `VARCHAR`, so a typo or new value could enter the audit data. | Add a `CHECK` constraint listing `RUNNING`, `PENDING_HUMAN_APPROVAL`, `RESUMING_LOOP`, `TASK_ABORTED` and `TASK_COMPLETED`. |
| The loop guard told the router to throw an execution break. That exception could strand the session before the supervisor records an outcome. | Return an abort decision that names the loop budget. The supervisor ends the session as `TASK_ABORTED` without relying on exception recovery. |
| The social security number pattern was anchored to the entire string and had no multiline handling. It missed a number embedded in normal user text. | Use the unanchored word-boundary pattern `\b\d{3}-\d{2}-\d{4}\b` and replace matches inside the text. |
| A credit-card regex alone would redact order numbers and timestamps that happen to have many digits. | Find candidate runs, normalize spaces and hyphens, and apply `luhnValid` before replacing the run. |
| The system referred to a `SECURITY_VIOLATION` response but defined no payload contract. Callers could not parse or test it. | Define the exact `{ error: { code, message, violations } }` shape in `src/safety/filters.ts` and `config/system_prompt.md`, and do not echo user text. |
| `Record<string, any>` removed type checking from extracted state and tool arguments. | Use `Record<string, unknown>`. Consumers must narrow values before using them. |
| The state error field used `stringStep`, which reads like a typo and makes consumers guess at its meaning. | Rename the field to `step` and keep the error entry as `{ step, message }`. |
| The vector dimension `1536` was presented as a permanent system constant. A different embedding model could make stored vectors incompatible. | Treat the dimension as a property of the active embedding model. Change the configuration and re-index when the model changes. |
| `classification_level` in metadata suggested that metadata alone enforced row-level access. It did not. | Require the query layer to apply `classification_level` and `user_scope_id` filters before returning chunks. |
| The injection denylist was presented as a complete security boundary. Phrase matching is easy to evade. | Treat the denylist as a pre-filter. Enforce the boundary with tool permissions, the sandbox and the human-in-the-loop gate. |
| The evaluation suite contained only cases that should block. A filter that blocked every request could score as well as a selective filter. | Add `TC-003` as a positive control for an allowed invoice lookup routed to `researcher`. |
| `agent_sessions` had no `updated_at`, so an audit could not tell when a session last changed state. | The `updated_at` column records the last change. Every application mutation must set it because the schema has no trigger. |
| The prose named `NOTIFY_ONLY`, but the trigger data had only two action values and the HITL row did not preserve the requested action. | Define `NOTIFY_ONLY` in the action union and trigger examples, and add `action_required` to `hitl_records`. It records what the interface was asked to do. |
| The router evaluated triggers before the loop budget, so a runaway session with a destructive request parked for human approval instead of aborting. | Check the loop budget first and return `TASK_ABORTED` to `supervisor` before evaluating triggers. |
| `NOTIFY_ONLY` was accepted by the trigger vocabulary, but every match parked the session, so the code contradicted the documentation. | Leave the session `RUNNING` for notifying matches and report them separately from blocking matches. |
| `argument_matches` built a regular expression from configuration without handling an invalid pattern, so one broken trigger could crash routing. | Catch the regular-expression error, treat the pattern as no match, and reject the pattern during validation. |
| The trigger validator accepted an unknown `op`, a non-numeric threshold value, a non-string `tool_names` entry and a pattern that does not compile. | Validate the threshold operator and number, require string tool names, and compile-check the pattern. |
| The approval and MFA guards bound the record to the session but never authorized the caller for that session, so another authenticated caller could resolve somebody else's request. | Authorize the caller for the session before resolving the record. |
| The guards checked that the record was still pending in a separate read, which two concurrent requests can both pass. | Move the record from pending to resolved atomically and accept only the request that changes the pending row. |
| The router returned every blocking match while the pending approval held one trigger, so resolving one requirement could release an operation that another requirement still blocked. | Create one HITL record per blocking match, park on the first, and resume only after no blocking record for the operation remains pending. |
| The shipped test was excluded by the emitted Vitest configuration, so a standalone run of the tests did not prove the scaffold-level integration. | The emitted configuration includes `src/**/*.{test,spec}.ts` alongside the existing `test/` glob, and the scaffold-level run uses the repository's own configuration. |
| The protocol document and the system prompt parked every match while the router parked only blocking matches. | Both documents now say a trigger that requires a human decision blocks the call and that a notification-only trigger does not. |
| The router ignored the session status, so a pending or terminal session could be routed forward. | `route()` refuses a session that is not `RUNNING`, and the caller applies `LOOP_RESUMED` before routing resumed work. |
| The validator compiled patterns with Python's `re` while the router uses JavaScript's `RegExp`, so the two disagreed on named groups. | The validator checks a deliberately limited common syntax and rejects the constructs the two engines disagree on. JavaScript's `RegExp` is the matching authority. |
| The opt-in answer accepted a string, which is truthy, so the group was emitted when the operator asked for it to be off. | An answer whose schema entry carries `"type": "boolean"` must hold a real boolean, and a string, an integer, a list and a dict are refused. |
| The MFA contract had no challenge field and the browser appeared to decide the outcome. | The panel receives provider-neutral challenge data and submits an untrusted attempt, and the server records the resolution. |
| An absent argument matched an `argument_matches` pattern through its `"undefined"` string form. | The router checks that the argument is present before it tests the pattern. |
| A blank threshold argument coerced to zero. | A blank or whitespace-only string argument is treated as no match. |
| The card pass joined adjacent numbers into one oversized candidate, so two valid card numbers separated by a space both survived the filter. | Split numeric tokens inside the candidate and redact each valid standalone card token. |
| The validator compiled patterns with Python's `re` while the router uses JavaScript's `RegExp`, and the two disagree on a character class that starts with a bracket. | Use Python's `re` only for syntax checks and use JavaScript's `RegExp` as the matching authority. |
| A configured threshold of `10**400` passed the validator and became `Infinity` in JavaScript. | Bound integer thresholds at `2**53 - 1` so configured values remain representable in JavaScript. |
| The validator ran its agentic checks whenever any agentic-looking path existed, so unrelated repositories received false errors. | Run the checks only when `config/hitl_triggers.json` exists, then require every expected destination. |
| `worker-service` and `monorepo` were marked as agentic, so generic scaffolds received migrations, a Docker sandbox and agent safety files by default. | Set `agentic: true` only for `agent-service`; let every other profile opt in with `emit_agentic_stack`. |
| The source blueprint asked for API endpoint structures and front-end interface stubs, and the skill only described them. | Emit `src/agent/endpoints.ts` and `src/agent/ui_contracts.ts` with the required contracts. |
| The approval and MFA guards bound the record to the session but never authorized the caller for that session, so another authenticated caller could resolve somebody else's request. | Require the caller to be authorized for the session named in the path, refuse an expired request, and require the record to be the session's current pending operation. |
| The guards checked that the record was still pending in a separate read, which two concurrent requests can both pass. | Require the update from pending to resolved to be atomic. |
| The router returned every blocking match while the pending approval held one trigger, so resolving one requirement could release an operation that another requirement still blocked. | Create one HITL record per blocking match, park the session on the first, and park again while another record for the same operation is pending. |
| The card pass joined adjacent numbers into one oversized candidate, so two valid card numbers separated by a space both survived the filter. | Split the candidate on whitespace, redact each part that qualifies, and redact a run of neighbouring parts that qualifies as a whole. |
| The validator compiled patterns with Python's `re` while the router uses JavaScript's `RegExp`, and the two disagree on a character class that starts with a bracket. | Reject a class that begins with `]` after `[` or `[^`, and say that JavaScript's `RegExp` is the matching authority. |
| A configured threshold of `10**400` passed the validator and became `Infinity` in JavaScript. | Bound a configured integer at the JavaScript safe integer range and require a float to be finite. |
| The card pass stopped after the first standalone match, so a card written in groups survived beside another numeric token. | Redact a standalone card and a run of neighbouring groups, and rebuild the candidate from spans so a grouped card becomes one token. |
| Both resolution responses allowed only `RESUMING_LOOP` or `TASK_ABORTED`, so the parked status the multi-trigger rule needs could not be returned. | Allow `PENDING_HUMAN_APPROVAL` in both responses and emit the resumption event only after the last blocker clears. |
| The regex subset still accepted `[^]a]`, because Python reads a `]` after `[^` as a literal and JavaScript does not. | Reject a class that begins with `[^]` and add the case to the self-test. |
| The document said JavaScript's `\s` was ASCII-only. It matches Unicode whitespace, and the two engines disagree on which code points count as whitespace. | Name the difference correctly and keep JavaScript's `RegExp` as the matching authority. |
| The reference said a record moves to `RESOLVED`, which is not a stored status. | Name the four stored terminal resolutions: `APPROVED`, `MODIFIED`, `DENIED` and `TIMEOUT`. |

## What the skill emits

The scaffold emits fifteen destination paths for this group:

1. `config/persona.json`
2. `config/hitl_triggers.json`
3. `config/system_prompt.md`
4. `config/vector_store.yaml`
5. `config/tools.json`
6. `db/migrations/0001_create_agent_sessions.sql`
7. `db/migrations/0002_create_hitl_records.sql`
8. `src/agent/state.ts`
9. `src/agent/router.ts`
10. `src/agent/endpoints.ts`
11. `src/agent/ui_contracts.ts`
12. `src/agent/agentic_stack.test.ts`
13. `src/safety/filters.ts`
14. `tests/eval_dataset.json`
15. `docs/architecture/hitl-protocol.md`

The `agent-service` profile is the only profile with `agentic: true`. The other five profiles
receive the group only when the operator sets `emit_agentic_stack` to `true`; its default is
`false`. The `database` answer selects the migration dialect.

The two migration destinations are selected by the `database` answer, not by the profile.
PostgreSQL receives the PostgreSQL pair with UUID, JSONB and TIMESTAMPTZ types. SQLite receives
the SQLite pair with TEXT ids, JSON stored as TEXT and timestamp text. The other thirteen paths are
the same in both dialects. The scaffold owns the destination mapping for the generated files. The
application owns the implementation behind the endpoint and interface contracts.

Every application mutation must run this statement:

```sql
UPDATE agent_sessions SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE session_id = $2;
```

The schema has no trigger to enforce `updated_at`.

## What stays with the agent

The generated endpoint contracts and front-end interface contracts define the required data and
callbacks. The implementing agent provides the HTTP framework handlers, the UI components behind
`TransactionApprovalModal` and `SecurityChallengePanel`, the `researcher` and `writer` node
behaviour, the database client, the tool registry and the authentication scheme.

The implementing agent must route the `researcher` and `writer` nodes. `researcher` should gather
bounded evidence through the configured retrieval layer. `writer` should receive that evidence,
produce the response, and emit a terminal event. The agent must define failure handling for empty
retrieval, tool errors and invalid model output.

The implementing agent must wire `src/agent/router.ts` to the application's own tool layer. The
tool adapter must check permissions, evaluate triggers on the final proposed arguments, stop on a
pending or aborted result, run the sandboxed tool only after the checks pass, persist the tool
message, and increment the execution loop count. It must re-check authorization after a human
modifies arguments. The generated files define the contracts. They do not implement the handlers,
UI components, node behaviour, database client, tool registry or authentication scheme.

### Implementation follow-up list

These are the obligations the generated contracts state and the application must carry. The
scaffold does not implement them, and a repository that claims to be done while these are open
is claiming more than it has.

- Enforce the endpoint guards transactionally, so a caller who is not authorized for the session
  cannot resolve its record and two concurrent requests cannot consume the same approval.
- Give an operation a stable identity across its HITL records, so several blocking records can be
  tied to one proposed call.
- Invalidate the remaining approvals for an operation when a human correction changes its
  arguments, and re-evaluate the triggers against the corrected arguments.
- Process the timeout of a pending record, so an unanswered request ends the session as
  `TASK_ABORTED` rather than waiting for ever.
- Prevent a duplicate tool execution after a resolution, so a retried approval does not run the
  call twice.

| Control | Owner | Check |
|---|---|---|
| Domain and style | Persona file | The request stays inside the allowed domain and uses the configured style. |
| Injection pre-filter | Safety filter | The filter returns matching ids without treating the denylist as authorization. |
| Tool permission | Application tool layer | The tool registry rejects unknown names and invalid arguments. |
| Financial review | Router and supervisor | `argument_threshold` parks amounts above the configured limit. |
| Deletion review | Router and MFA service | `tool_name_in` parks destructive tool names until the challenge resolves. |
| Router precondition | Router and caller | `route()` accepts only `RUNNING`; the caller applies `LOOP_RESUMED` before routing resumed work. |
| Caller authorization | Application endpoint guards | The caller must be authorized for the session named by the request before resolving its HITL record. |
| Card masking | Safety filter | The card pass splits separate numeric tokens, redacts valid standalone cards, and leaves uninterrupted runs longer than nineteen digits untouched. |
| Endpoint contracts | `src/agent/endpoints.ts` | The application implements each declared method, path, request shape and guard. |
| Interface contracts | `src/agent/ui_contracts.ts` | The UI implements the declared props and callbacks without executing tools in the browser. |
| Retrieval scope | Knowledge query layer | The query applies user and classification filters before returning chunks. |
| Loop limit | State machine | The router returns `TASK_ABORTED` after the loop budget is exceeded. |
| Human audit | HITL records | The application stores the proposed request and human resolution. |
