# OpenHeart standalone skill integration

## Request and decision

The request is to read the OpenHeart application source, extract its workflow,
templates, reports and datasets/data schemas, then translate those into an
independent skill under `bughunt8/skills`. The requested outputs include ACT and
Mermaid diagrams. The application itself is not a skill.

The candidate is [openheart-analysis](../skills/engineering/openheart-analysis/SKILL.md).
It has no OpenHeart executable, server, Cargo or other-skill runtime dependency.
The agent performs source analysis; the standard-library Python tools validate
and serialize its model. This preserves the workflow and view categories, not
compiler-grade equivalence or binary compatibility.

## Source evidence and attribution

The reviewed upstream pin is
[`0bf962fc06e975e9ea7610242b8997b1391fec05`](https://github.com/AhmadHassan-BTed/OpenHeart/commit/0bf962fc06e975e9ea7610242b8997b1391fec05).
The [source map](../skills/engineering/openheart-analysis/references/source-map.md)
links the source files for every extracted contract. OpenHeart is authored by
Ahmad Hassan, B-Ted. Its MIT notice says `Copyright (c) 2026 OpenHeart Contributors`.
The importer preserves that notice verbatim and generates
[attribution](../skills/engineering/openheart-analysis/references/upstream/ATTRIBUTION.md)
and provenance. No author endorsement is implied.

The manifest uses a selected support snapshot, not a full application import and
not an upstream skill import. An immutable commit `ref` plus `expected_commit`
prevents branch movement from changing the reference or aborting the scheduled
multi-source refresh. Detached SHA checkout is regression tested. The native skill
stays outside the importer's read-only destination.

The copied source retains upstream trailing whitespace and end-of-file blank
lines to preserve byte fidelity. Authored-code whitespace checks exclude only
that immutable reference subtree; do not format the upstream snapshot.

## Extraction coverage

| Requested area | Integration |
| --- | --- |
| Workflow | Ten-stage source-to-SCPG semantic analysis checklist, explicit methods and evidence gates |
| Templates | Newly authored Markdown analysis and verification templates based on CLI/benchmark report contents |
| Reports | Normalized analysis JSON, machine report, bidirectional traceability and completed-report instructions |
| Data schemas | Bundled JSON Schema plus source record dictionary for tokens, AST, symbols, CFG, SSA/phi, calls, traceability, paths and UML |
| Datasets | Authored Python fixture, four pinned Java Observer inputs with independent declaration truth, automated/manual case inventory and external-dataset qualification plan |
| Diagram output | All 19 upstream categories plus AST; JSON/Mermaid/PlantUML; provisional activity ACT aliases |
| XMI | Classifier identity only, explicitly excluding members, relationships and other categories |
| Attribution and references | Commit-pinned original source examples, original MIT text, generated provenance/notices and source-to-skill map |
| Integration | Generated root index, agent guidance, A0 regression gate and regenerated catalogue/harness data |
| Adversarial review | Separate-model source audit and candidate review; findings and closure recorded below |

The original repo uses AST. ACT is only an upstream action-node UI badge, not an
artifact format. The output alias is provisional and must be clarified if the
user means another artifact.

## Fidelity boundaries

Some upstream advanced Mermaid outputs are synthetic. The pinned
[exporter](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/scpg/diagram/export/mermaid.rs)
contains fixed CDG content, a fabricated call-chain/self-cycle and one-second
timing bars. These are not translated as facts. Deployment, timing, runtime
objects, BDD results and recursion need actual evidence or remain uncomputed.

Only class, sequence and state use native diagram notation in the local
exporter. The remaining views are labelled graph approximations. JSON retains
the supporting semantic attributes. Binary layout, succinct storage, CRC-64,
memory mapping, incremental queries, GUI functions, compression and exact
compiler/solver guarantees are outside this skill's implementation.

The schema checks structure. Source checks validate hashes, line spans and
excerpts. External QA parsed Mermaid syntax; the skill and CI do not invoke
diagram renderers. None of these checks establishes the truth of an
inferred relationship. The standalone regression fixture is explicitly partial.
No real-project, whole-language or native-host behavioral benchmark is claimed.

## Verification and review

The source audit and initial adversarial review were performed by fresh Claude
Opus 5.5 agents, separate from the GPT author. Claude Code was attempted but its
CLI was not authenticated. Both reviews therefore used the Computer harness.
Different-model review was performed; cross-harness review was not.

Read the preserved [source audit](reviews/openheart-source-audit-0bf962f.md) and
[initial candidate review](reviews/openheart-adversarial-initial-2026-10-25.md).
The initial review is historical and its open findings do not describe the
corrected candidate. The closure matrix below identifies the fixes.

| Finding | Corrective change and regression evidence |
| --- | --- |
| P1-1, certainty/resolution laundering | Full node/edge record identity enforced across views; negative basis, resolution and parent probes |
| P2-1, unenforced provenance requirements | Trace/snapshot roles, nonblank evidence, derivation text and actual methods required |
| P2-2, XMI | Correct namespace URIs, model ID and invalid-control stripping; namespace assertions |
| P2-3, partial output | Validated ordinal types, temporary-directory export with cleanup and clear CLI errors |
| P2-4, line/encoding inventory | Editor-style LF lines, zero-line empty files and explicit UTF-8 contract |
| P2-5, invented member types | Omit absent type names and iterate fields/methods separately |
| P2-6, scheduled sync tripwire | Immutable SHA fetch, explicit manual cadence and generated metadata drift detection |
| P2-7, weak stage typing | Global and per-stage kind enums, minimal AST/callsite/BDD/derived attributes; remaining envelope limits documented |
| P2-8, missing translated datasets | Four original pinned Java inputs plus independent model and edge truth; scenarios explicitly manual or automated |
| P3, communication ordering | Ordinal prefixes in both diagram formats |
| P3, source safety and runtime | Duplicate keys, nonfinite/overflow numbers and unpaired surrogates rejected; scope/exclusions checked; linear parent-cycle detection |
| P3, misleading receipts | Machine checks prefilled, canonical model and exporter hashes recorded |
| P3, detached provenance and executable snapshots | Root-maintenance links qualified; pytest discovery excludes vendored executable references |
| P3, overstated tests and stale reasons | Actual newline injection, shuffled presentation tests, explicit stage reasons and short upstream project name |

The core skill regression suite has 54 passing tests. Repository script tests
have 180 passing tests, including the four immutable-pin tests. The previously
existing harness, GitHub setup, spec-driven-development and site-Python suites
passed 35, 19, 76 and 27 tests respectively before the final documentation
refresh. These are local receipts, not remote CI or semantic-accuracy scores.

Mermaid 11.12.0 parsed all 21 emitted Python fixture diagrams and the Java class
diagram. Extra native sequence/state syntax probes are run separately. Parsing
does not constitute visual rendering. PlantUML rendering and UML-tool XMI
interoperability were not run because those tools are unavailable.

The catalogue build, HTML lint and secret scan pass. A full local browser suite
returned 182 passed, one skipped and three failed. A targeted serial rerun passed
the desktop wheel and mobile hover-card tests; the mobile 120 ms long-task
budget still failed. The unmodified `origin/staging` baseline independently
failed that same mobile budget and the hover-card test in this sandbox.
No unrelated site behavior was changed or silently declared fixed. The new
catalogue total is explicitly updated from 545 to 546. Treat the browser timing
gate as unresolved, not a green deployment receipt.

The [final adversarial closure review](reviews/openheart-adversarial-closure-2026-10-25.md)
approved the corrected candidate within its stated limits, with no blocking P1
or P2 findings remaining. The reviewer independently reran the 54 core tests on
Python 3.12 and 3.14, four importer tests, 180 repository script tests, source
fidelity and live immutable-pin checks. All 46 selected source files and the
licence match upstream bytes.

The reviewer also compared each of the 34 other sources with the old and new
importers and found identical results. Five unrelated sources already drift or
abort with the old importer. Their maintenance is not silently claimed resolved
by this integration. The external pytest, jsonschema and Mermaid receipts were
performed by the author, not independently reproduced by the closure reviewer.

## Residual qualification limits

Full-record identity prevents a projection from upgrading certainty under a
reused ID. It does not find contradictory claims introduced under a new ID.
The validator cannot establish the truth of a source relationship, the honesty
of a trace role or the adequacy of an excerpt or derivation. A one-character
nonblank excerpt can be source-consistent without supporting the claimed fact.
These are semantic-review responsibilities, not compiler proofs.

Kind restrictions apply to stages, not every diagram projection. Class diagram
presentations omit generic structure and method parameters while preserving
signatures in JSON. UTF-8 decoding errors can omit the offending path. The
importer's historic pinned date records the last sync, not necessarily the
date a maintainer selected the revision. These limits are disclosed rather than
changed outside the bounded integration.

The portable-number regression has direct independent closure probes in
addition to its bundled tests. The reviewer noted that two bundled negative
cases also trigger ID-consistency checks; the independent CLI probes establish
overflow/NaN rejection directly. Bytecode and pytest caches are excluded from
the distributed package, which was extracted and passed all 54 tests again.

No remote CI, merge approval or deployment is claimed. Native-host semantic
accuracy, pinned CI renderer qualification and UML-consumer interoperability
remain open acceptance work, not verified delivery claims.

## Publication boundary

The reviewed implementation commit is
`ccf2e9e568c9ff1f2e1fc8f1518f913739127585`. After explicit user approval, the
feature branch was pushed and [draft PR #66](https://github.com/bughunt8/skills/pull/66)
was opened against `staging`. The remaining qualification work is tracked in
[issue #65](https://github.com/bughunt8/skills/issues/65), which stays open until
its acceptance evidence is verified.

Publication of this draft does not authorize merge, promotion to `main` or
deployment. The separate standalone package remains the reviewed v1.0.0 source.
