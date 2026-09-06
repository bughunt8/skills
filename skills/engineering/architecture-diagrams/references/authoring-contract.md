# Authoring contract

Every field, and how to choose. The authoritative implementation is `scripts/diagram_ir.py`.
`schemas/diagram.schema.json` is **generated** from it by
`scripts/generate_schema.py`, so the two cannot disagree; do not hand-edit the
schema, and run `generate_schema.py --write` after changing a field spec.

The validator is strict by design:

- **An edge to an undeclared node is an error.** Dropping it silently produces a
  diagram that is confidently wrong, which is worse than one that refuses to
  build.
- **Unknown keys are errors.** A silently ignored key is how you end up certain
  you set something that never took effect.
- **Problems are reported together**, each with its JSON path, so one pass fixes
  the document. One exception: an unrecognised `kind` stops validation, because
  the kind decides which fields apply. The error says so explicitly rather than
  leaving you to wonder what else is wrong.
- **An exact duplicate edge is an error.** Two identical edges draw the same curve
  in the same place with no way for a reader to tell. Parallel edges with
  different labels are legitimate and are fanned apart automatically.
- **Every field is type-checked, not just the required ones.** `{"legend": 7}` is
  rejected at validation rather than crashing the renderer later.

## Top level

| Key | Required | Notes |
| --- | --- | --- |
| `kind` | yes | `architecture`, `workflow`, `dataflow`, `lifecycle`, `sequence` |
| `title` | yes | Short. Names the system or the flow. |
| `subtitle` | no | One or two sentences. State what the diagram *asserts*, so a reader can tell when it has gone stale. |
| `footer` | no | Provenance: commit, date, source of truth. Rendered in the artifact's footer. |
| `orientation` | no | `LR` (default) or `TB`. Ignored for `sequence`. |
| `legend` | no | Extra legend strings. Loop, async and boundary entries are derived for you. |
| `groups` | no | Boundaries. Graph kinds only. |
| `nodes` | graph kinds | At least one. |
| `edges` | no | Omit for a diagram that is only an inventory. |
| `participants` | `sequence` | Lifelines, left to right. |
| `messages` | `sequence` | In order. Numbered automatically. |

Pick `LR` when the diagram is a flow with a beginning and an end. Pick `TB` when
it is a hierarchy or a short pipeline. If it has more than about five ranks, `LR`
almost always reads better on a screen.

## `nodes`

| Key | Required | Notes |
| --- | --- | --- |
| `id` | yes | Referenced by `edges` and `groups`. Short and stable; renaming it breaks every reference. |
| `label` | yes | What a reader calls this thing. Wrapped automatically, including long identifiers and scripts with no spaces, such as Chinese and Japanese. |
| `shape` | no | Default `box`. See the table below. |
| `note` | no | One short line. Must say something the label cannot. |
| `tech` | no | The concrete technology, rendered small and monospaced. |
| `accent` | no | `true` on **one** node per diagram. |

### Shapes

| Shape | Use for |
| --- | --- |
| `box` | a service, component or step (default) |
| `round` | a start or terminal state |
| `cylinder` | a datastore: database, bucket, table |
| `queue` | a queue, topic or stream |
| `cloud` | a managed or third-party service, or the internet |
| `actor` | a person or an external system acting on its own behalf |
| `decision` | a branch, in a workflow or lifecycle |

Shapes are semantic, not decorative. A reader who learns that cylinders are
stores can then scan the diagram for stores. Using `cloud` because it looks nice
destroys that.

### `note` versus `tech`

`note` is a claim about behaviour: `"Validates and de-duplicates"`,
`"Retries three times, then dead-letters"`, `"Public, unauthenticated"`.

`tech` is the implementation: `"Lambda"`, `"DynamoDB"`, `"Cloudflare Workers"`.

`"Handles requests"` on a node called `API server` is neither. Leave it out.

## `edges`

| Key | Required | Notes |
| --- | --- | --- |
| `from`, `to` | yes | Declared node ids. |
| `label` | no | The verb or the payload: `"POST /lead"`, `"cache miss"`, `"nightly"`. |
| `style` | no | `solid` (default), `dashed`, `dotted`. Cycle-closing edges default to `dashed`. |
| `accent` | no | For the one path the diagram exists to show. |

**Direction is meaning.** An edge points the way a request or a record travels,
not the way a dependency is declared in code. If A calls B and B answers, that is
one edge `A -> B`. Add the reverse only when the response path is itself
interesting: a webhook, a callback on a different route, a status push.

**Convention for styles.** Nothing enforces this, so state it in `legend` if you
rely on it. A common and useful one: solid for synchronous, dashed for
asynchronous, dotted for crossing a trust boundary.

**Cycles are fine.** Retry loops, rollbacks and state machines are cyclic. The
layout finds the edges that close a cycle, routes them through a strip that no
node occupies, and dashes them. A self-referential edge (`from` equal to `to`)
draws as a loop above the node. Do not linearise a state machine to make it fit.

**Edges are not routed around obstacles.** Between neighbouring ranks nothing can
be in the way. A longer edge, or the leg of a back edge, can cross an unrelated
node on a dense graph. That is a limitation of the renderer, not of your document:
if it looks wrong, the diagram is too dense and wants splitting.

## `groups`

| Key | Required | Notes |
| --- | --- | --- |
| `label` | yes | The boundary's name. |
| `nodes` | yes | At least one declared node id. |

**Group by boundary, not by team.** Trust boundaries, network boundaries, blast
radius, ownership when ownership is the point. `Public edge`, `VPC private
subnet`, `Third party`, `Customer-managed`. Not `Platform team`, not `src/`.

**A node belongs to at most one group**, and the validator enforces it. Groups are
laid out as swimlanes, so a node cannot be in two bands at once. This is also the
right constraint for the reader: overlapping boundaries cannot be reasoned about,
whether drawn or not.

Groups are ordered automatically by where their members first appear in the flow.

## `participants` and `messages` (sequence)

`participants` takes `id`, `label`, and optionally `shape` and `note`. Order in
the array is left-to-right order on screen; put the initiator first and order the
rest by when they first appear, which minimises long crossing arrows.

`messages` takes `from`, `to`, and optionally `label`, `style`, `note`, `accent`.

- `from` equal to `to` renders as a self-call loop.
- `note` renders under the arrow. Use it for a condition or a caveat:
  `"same email, within the idempotency window"`.
- Use `dashed` for returns and responses. It is the one convention readers of
  sequence diagrams already expect.

Show one scenario per diagram. If you need a branch, either draw the interesting
path and note the other, or draw two diagrams. Sequence diagrams with inline
conditionals become unreadable faster than any other kind.

## Worked examples

- `examples/web-platform.architecture.json` — boundaries, shapes, a return edge,
  mixed edge styles
- `examples/deploy.lifecycle.json` — a cyclic state machine with retry and
  rollback
- `examples/lead-capture.sequence.json` — a self-call, dashed returns, a note

## Commands

```bash
python3 scripts/render_diagram.py doc.json --check       # validate, write nothing
python3 scripts/render_diagram.py doc.json -o out.html   # render the artifact
python3 scripts/render_diagram.py doc.json --svg -o out.svg
python3 scripts/render_diagram.py --self-test            # prove the validator fires
python3 -m unittest discover -s tests -v
```

## Keeping a diagram honest

A committed diagram rots quietly. Two habits help:

1. Put the source of truth in `footer`: the commit or file the diagram was read
   from. A reader can then check it themselves.
2. Commit the `.json` next to the code it describes and render in CI, so the
   artifact cannot be stale relative to the document. `--check` in CI catches a
   document that no longer validates after a refactor renames things.
