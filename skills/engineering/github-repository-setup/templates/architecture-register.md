# Architecture coverage register contract

Use one authoritative YAML register or equivalent structured TRD table. The
bundled checker supports the YAML contract below; equivalent formats need
equivalent reviewed checks, not a second competing register.

After plan approval, from the skill directory:

```sh
python3 scripts/architecture_register.py init /absolute/target/coverage.yml
python3 scripts/architecture_register.py check /absolute/target/coverage.yml --stage draft
python3 scripts/architecture_register.py check /absolute/target/coverage.yml --stage plan
python3 scripts/architecture_register.py check /absolute/target/coverage.yml --stage story --ids DS05 X07
python3 scripts/architecture_register.py check /absolute/target/coverage.yml --stage release --ids DS05 X07
```

Requires Python and PyYAML. `init` refuses overwrite and creates 97 unresolved
records from [the catalog](architecture-catalog.yml). It does not create parent
directories, install tools, approve a plan, enable CI or access the network.
`draft` checks structure; `plan` requires disposition and ownership, not that
every choice be settled. `story` and `release` require a nonempty human-reviewed
impact set; they do not infer impacts. Release scope must include all applicable
requirements of the release, including shared platform dependencies.

Each row has the following fields (illustrative draft, not approved):

```yaml
id: DS05
topic: Idempotency
applicability: applicable
decision_state: unresolved
rationale: Externally retried operations can duplicate side effects.
owner: Service owner to be confirmed
workload_constraints: Retry window and transaction boundary pending
requirements: [NFR-RETRY]
alternatives: [Unique constraint and replay record, External deduplication store]
selected_approach: ""
document: TRD.md#idempotency
approval: ""  # actual reviewer/date/decision record, never inferred
epic: ""
feature: ""
story: ""
tests: [Duplicate request with same key, Same key with different payload]
evidence: []  # each item: {reference, revision, environment, result}
implementation_state: not_started
impact: Blocks mutating-operation implementation until key/atomicity rules settle
revisit: Before dependent Story readiness
related_to: []
```

Allowed applicability: `pending`, `applicable`, `not_applicable`.
Allowed decision_state: `unresolved`, `accepted`, `deferred`, `rejected`,
`superseded`. Allowed implementation_state: `not_started`, `in_progress`,
`implemented`, `verified`, `not_applicable`.

Every nonpending disposition needs rationale and owner. Accepted decisions
need selected approach, authoritative document and real approval. Deferred
decisions need impact and revisit conditions. Rejected/superseded records link
to the alternative/current authority in document and explain the outcome.
Not-applicable is an explicit reviewed exclusion with rationale, not blank
coverage; its implementation state is not_applicable and evidence is not
required. Before Story/release readiness its approval is required too.

Keep all catalog IDs and exact topic names; append project topics as `CUSTOM-*`.
Use related_to for shared decisions, never delete overlapping rows. D03/P04
can reference one cache decision; DS07/AR07 can reference one event decision,
but each retains its viewpoint and applicability. Relationships are not status
inheritance. Do not count two related rows as two independently verified systems.

Verified applicable records require accepted decisions, tests and passing
evidence with a reference, tested revision and environment. Validate the
reference exists, output is authentic and revision is relevant during review:
the checker cannot establish those facts. Accepted does not mean implemented;
implemented does not mean verified. A change invalidating old evidence requires
renewed verification, not reuse of a stale green record.

At Story readiness, affected applicable decisions require accepted status,
FR/NFR mapping, Epic/Feature/Story references and tests. Related discovery
Stories can resolve pending choices without claiming implementation readiness.
At release readiness, applicable selected records also require verified status.
Do not pass an empty or selectively incomplete impact set to bypass blockers.
