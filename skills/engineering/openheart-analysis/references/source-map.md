# Source extraction and attribution

This skill adapts concepts from OpenHeart by Ahmad Hassan, B-Ted, at commit
[`0bf962fc06e975e9ea7610242b8997b1391fec05`](https://github.com/AhmadHassan-BTed/OpenHeart/commit/0bf962fc06e975e9ea7610242b8997b1391fec05).
It is a separately authored skill, not an upstream skill or endorsed release.
The original MIT copyright line is `Copyright (c) 2026 OpenHeart Contributors`.
Do not replace that notice with the maintainer's name.

Selected source and examples are imported by the repository's
`scripts/sync_vendor.py` into `references/upstream`. Its generated attribution,
ownership and licence files remain read-only. The selection preserves evidence
needed to audit the translation, not an executable distribution of the full app.
The manifest uses an immutable commit `ref` and an `expected_commit` guard.
Upstream branch movement cannot break the scheduled refresh or silently change
this reference. Updating the reference is a manual reviewed change.

## Source-to-skill mapping

| Extracted subject | Pinned upstream evidence | Skill equivalent |
| --- | --- | --- |
| Ten-stage workflow, artifact names, CLI inventory | [src/main.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/main.rs) | workflow.md and ten stage graph slots |
| Source manifest and token records | [source.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/core/types/source.rs), [token.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/core/types/token.rs) | File inventory, evidence objects and ingestion attributes |
| AST, symbols and scopes | [ast.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/core/types/ast.rs), [symbol.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/core/types/symbol.rs) | Syntax/symbol graph records and attribute dictionary |
| CFG, SSA, phi, def-use, call sites and SCCs | [cfg.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/core/types/cfg.rs), [ssa.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/core/types/ssa.rs), [cg.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/core/types/cg.rs) | control_flow, data_flow and calls stages |
| Source/IR/UML traceability | [tra/types.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/tra/types.rs) | Evidence on every node/edge, bidirectional traceability report |
| Path headers, order, bounds and SAT metadata | [psa/types.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/psa/types.rs) | paths attributes and explicit solver/proof boundary |
| UML records, member records, scenarios and patterns | [uma/types.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/uma/types.rs) | UML dictionary and semantic projection rules |
| 19 categories, classifiers and relationship vocabulary | [web/diagrams/manifest.json](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/web/diagrams/manifest.json) | Local diagram catalogue and 19 category rules |
| GraphIR, node, edge, member and metadata shapes | [json.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/scpg/diagram/export/json.rs) | Versioned normalized JSON Schema, not a claim of interchange compatibility |
| Mermaid/PlantUML formats and dispatch | [mermaid.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/scpg/diagram/export/mermaid.rs), [plantuml.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/scpg/diagram/export/plantuml.rs), [factory.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/scpg/diagram/factory.rs) | Fresh evidence-only exporters, native class/sequence/state and labelled graph approximations |
| XMI output scope | [xmi.rs](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/scpg/diagram/export/xmi.rs) | Explicitly limited classifier-identity XMI |
| Report metrics and phantom/missing sets | [ruthless_verify.py](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/ruthless_verify.py) | REPORT/VALIDATION templates and independent benchmark recipe |
| External dataset references and GoF tests | [test_ruthless_popular_datasets.py](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/scripts/test_ruthless_popular_datasets.py) | Dataset inventory, no automatic acquisition or inherited accuracy claims |

## Source findings that constrain equivalence

The CLI collector accepts Java, Kotlin and Kotlin script files. This does not
establish equal semantic support for every `LangId` listed in the ingestion
registry. Language-wide accuracy remains unqualified without its own test run.
The skill can inspect other languages through the executing agent or an available
parser, but must record that method instead of inheriting upstream support claims.

The Mermaid exporter contains synthetic advanced diagrams at this pin. In
particular, `export_cdg_diagram` writes a fixed amount/saveOrder example;
`export_callgraph_diagram` links a hash-set iteration and adds a self-cycle;
`export_timing_diagram` assigns one-second durations and a fallback execution.
Deployment falls back to packages as nodes. These facts can be inspected in
the pinned [Mermaid exporter](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/scpg/diagram/export/mermaid.rs).
The skill deliberately refuses those behaviors.

The [timing extractor](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/uma/behavioral/timing_diagram.rs)
has no timing implementation. The
[object extractor](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/src/uma/structural/object_diagram.rs)
uses static allocation-related records, not a live heap snapshot.
Use evidence-insufficient statuses where source cannot establish the requested
runtime facts.

The repository uses AST, not ACT, as its syntax-tree term. ACT appears as an
action-node UI badge in its diagram manifest, not an artifact format. This skill adds a
documented provisional `ACT` activity alias solely to accommodate the user's
requested output name; it does not attribute that alias to OpenHeart.

The independent source audit also found constant JSON projections, fabricated
file paths and unconditional verification metadata. The JSON exporter never
receives the real CFG, SSA, call-graph or ROBDD artifacts. The local skill's
single shared graph and evidence-bearing model are deliberate departures from
that export architecture, not a claim to duplicate its output bytes.

## Deliberate non-equivalences

This package does not reproduce succinct balanced-parentheses storage,
rank/select indexes, memory mapping, CRC-64 binary integrity, incremental engine
queries, GUI editing, code-to-canvas navigation, live GitHub ingestion, measured
compression or exact solver behavior. No binary `.tca/.bpa/.sta/.cfa/.ssa/.cga/
.tra/.psa/.uma/.scpg` files are emitted. Renaming JSON to those extensions would
misrepresent the output.

The original source has no reusable Markdown report-template package. Its reports
are CLI logs, JSON response statistics and printed benchmark summaries. The two
bundled Markdown templates are newly authored adaptations of those outputs.
The schema is also newly authored, with explicit source spans and uncertainty
added to the upstream graph concepts.
