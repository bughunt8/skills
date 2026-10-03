# EARS behavior requirements

EARS constrains requirement sentence structure to make behavior easier to discuss; the official patterns distinguish ubiquitous, state, event, optional, unwanted, and combined requirements. It does not choose an implementation or provide a proof of correctness. [Alistair Mavin's EARS guide](https://alistairmavin.com/ears/)

Use one atomic externally observable statement per REQ. The `Type` column describes the sentence, not the system's architecture. A noun phrase naming the system, a nonempty response, and the exact trigger keywords matter. The checker is case-insensitive for EARS text, but table headers and IDs follow the artifact contract.

| Type | Required form | Example |
| --- | --- | --- |
| ubiquitous | The system name shall response. | The preview service shall exclude message contents from observation records. |
| event | When trigger, the system name shall response. | When a caller submits valid text, the preview service shall return an accepted outcome. |
| state | While state, the system name shall response. | While preview is unavailable, the preview service shall reject new requests. |
| optional | Where included feature, the system name shall response. | Where offline preview is included, the preview service shall accept requests without connectivity. |
| unwanted | If unwanted trigger, then the system name shall response. | If the submitted text is empty, then the preview service shall return a rejected outcome. |
| complex | While state, When trigger, the system name shall response. | While preview is enabled, When a caller submits text, the preview service shall return a decision. |

These forms follow the official keyword order. The bounded checker supports the listed state-plus-event complex form; other legitimate EARS combinations need human review and an explicit reviewed extension, not a falsely labelled row. [Alistair Mavin's EARS guide](https://alistairmavin.com/ears/)

Reject `The shall respond.`, event rows starting `While`, unwanted rows missing `then`, reversed combined conditions, empty response, and multiple shall clauses. Check every row individually, not aggregate keyword counts. A grammatical response can still be vague, contradictory, incomplete, or not externally testable. Human review supplies those judgments.

## What, not how

Good behavior says the caller receives a rejected outcome when input is empty. Bad behavior prescribes a Python function, React component, SQL statement, database schema, hash map, or package install to achieve that outcome. Put implementation decisions in DESIGN or TECH_STACK. API/data details belong in DESIGN contracts/data, while the behavior spec states observable results, error meaning, ordering, and measurable thresholds.

The checker scans Context, Requirements, and AC for code fences, inline code, named implementation technologies such as Postgres/gRPC, and conditional implementation recipes as a best-effort heuristic. Ordinary behavior nouns such as queue, table, column, or class are not forbidden by themselves. Exclusions may name rejected technologies. False positives require human correction of the artifact boundary or a reviewed checker extension. Passing the heuristic does not show that no implementation choice remains.

## Acceptance

Use `### AC-1: A descriptive title (REQ-1, REQ-2)` followed by separate Given, When, Then lines. Every referenced requirement must exist. Every requirement must have AC coverage. Include denied paths, dependency failures, bounds, and meaningful nonfunctional criteria when applicable; do not invent arbitrary numerical thresholds.

An assertion must test an observable outcome rather than merely replaying the requirement text. Generated extraction is test intent only. A scaffold exception or missing import is not enough to establish the Red step of TDD.
