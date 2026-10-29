# Projection rules

Use the exact IDs in [diagram-catalog.json](../assets/diagram-catalog.json).
All projections contain canonical nodes and typed directed edges plus evidence.
The Mermaid/PlantUML files are presentations of that JSON. For unsupported native
notation, use a labelled approximation rather than claim UML conformance.

| ID | Required evidence | Mermaid presentation and important boundary |
| --- | --- | --- |
| class | Declared types, fields, signatures, extends/implements and type uses | `classDiagram`; child to parent generalization, implementer to interface realization |
| package | Namespace containment and imports/type uses across namespaces | Flowchart; distinguish containment from dependency |
| component | Build/module/service boundaries, interfaces and wiring | Flowchart approximation; packages alone do not establish runtime components |
| composite | Parts, ports and assembly connectors in a classifier | Flowchart approximation; distinguish owned parts from references |
| object | Explicit allocations or supplied runtime snapshot | Flowchart approximation; no inferred runtime slot values |
| deployment | Docker, IaC, manifests or supplied deployment facts | Flowchart approximation; never turn a package into a server |
| profile | Stereotype/metaclass definitions and extension declarations | Flowchart approximation; annotations alone are not UML profiles |
| sequence | A selected scenario, participants and ordered call sites | `sequenceDiagram`; edges require positive unique `ordinal` attributes |
| statemachine | State variables, guards, transitions and actions | `stateDiagram-v2`; do not invent Active/Uninitialized states |
| activity | Function or business workflow, decisions, loops and guards | Flowchart approximation; this produces provisional `ACT.*` aliases |
| usecase | Explicit actors, goals and system boundaries | Flowchart approximation; method names do not establish user goals |
| communication | Scenario participants and ordered messages | Flowchart approximation; ordinal labels, not fabricated temporal precision |
| interaction | Supported references to interaction scenarios and control flow | Flowchart approximation; do not rename methods as UML interaction frames |
| timing | Measured or explicitly specified state/time constraints | Flowchart approximation with labelled constraints; not measured latency or Gantt durations |
| cfg | Basic blocks and control edges for selected functions | Flowchart; label true/false, exception and loop-back edges |
| dfg | SSA definitions, uses and phi joins | Flowchart; data dependencies only |
| cdg | CFG postdominators and computed control-dependence edges | Flowchart; no placeholder conditions |
| callgraph | Actual call sites and candidate resolution | Flowchart; unresolved candidates labelled, recursion only if present |
| robdd | Explicit Boolean formula, variable order and computed decision nodes | Flowchart; false/true terminal and low/high edges; no fabricated #SAT |
| ast | Parsed or explicitly reconstructed syntax nodes and containment | Flowchart; additional skill view, not one of the upstream 19 |

## Semantic projection procedure

1. Select a supported scope and evidence-bearing stage records. Use their IDs.
   State whether nodes are declarations, inferred records or runtime observations
   in their `basis` field and attributes. Copy no synthetic upstream examples.
2. Form typed directed edges. Preserve evidence and explain derivations. Class
   relationship directions are `child -> parent`, `implementer -> interface`,
   `owner -> part`, `whole -> shared-part` and `user -> dependency`.
3. Populate member signatures for class nodes. Use visibility `+`, `-`, `#` or
   `~`; store type, static/final flags and exact signatures. The renderer prints
   member names and types. The JSON retains full signatures and flags.
4. Keep sequence ordinals in source/scenario order. Mark branching alternatives
   and asynchronous ordering in attributes and reports. The generic renderer
   emits a linear scenario only; `alt`, `loop`, activation and parallel fragments
   require a separately reviewed authored diagram and remain recorded in JSON.
5. Select status and reason. An evidence-insufficient graph contains no nodes or
   edges. A partial graph explains missing semantics. Never pad an empty model
   with dummy actors, servers, states, calls or execution times.

## Format limits

The deterministic exporter provides native Mermaid class, sequence and state
syntax. Other views use a typed labelled flowchart. PlantUML class, sequence and
state views use their corresponding notation; other projections use labelled
rectangle graphs. These are intentionally approximations, not all 14 native UML
notations. Parent hierarchy, guards, stereotypes, ports, timing constraints,
combined fragments and full member flags remain in JSON even where rendering
is lossy. Examine JSON for semantic review.
Class presentations also omit generic structure and method parameters; full
member signatures remain in JSON rather than being asserted as lossless text.

`analysis.json` is a local normalized extension, not byte-compatible OpenHeart
GraphIR. To exchange with that application, build and test a dedicated converter.
Do not claim an undocumented import contract.

XMI is not a full exporter here. The executable produces a class-only
`class.xmi` containing classifier identities and names, excluding members and
relationships, only when there is class data. It labels this loss in the report.
Other XMI projections are explicitly unsupported. XML well-formedness is not
UML/XMI interoperability validation.

Source labels are escaped into safe literal text by the exporter. It emits no
Mermaid `click`, HTML, init directives or PlantUML includes. Do not bypass that
boundary with raw diagram text from an analysed repository.
