# Graph workspace navigation

This is a task workspace, not a scroll presentation. Remove scroll animation,
pinning, smooth-scroll libraries and scroll-driven selection entirely. Keep the
static HTML build, local fonts, graph evidence and stable identity keys.

## Layout and type

The top row contains labelled search and community, category, Solution and evidence
filters. The next row names the current context and has Back, Overview and Reset.
The graph fills the remaining workspace beside a 320px inspector column. Nothing
overlays the graph. A bottom status bar reports actual context, matching and
onscreen counts, selected skill, zoom and evidence. Help is available there.

On phones, search and a native Filters disclosure occupy the top row. Open
`#gfilters` to use the community/category/Solution/evidence controls. The graph
and a compact inspector/results region stack. The Text library link and the
Solutions disclosure below keep the full reference material accessible. All list
buttons and controls have at least 44px hit targets. Body and controls use the
existing local Inter at 16px; the current title uses local Space Grotesk at 24px.

Graph geometry moves inside `#vp`; labels do not. Screen-space labels stay at
16 CSS pixels or larger regardless of SVG scale, zoom or device width. Collision
handling reserves visible node-dot bounds as well as existing label bounds. It
hides lower-priority labels, never shrinks them, and has no fixed label-count cap.
Offset labels use leader lines beginning at their node's rim. The selected label
shows the full skill name, wrapping at hyphens/spaces when necessary. It is
anchored beside the selected dot, with a leader line if clamped to the canvas.
An offscreen selection retains the full callout and a visible status instruction
to use Fit. The companion list makes
every member reachable even if its graph label is hidden.

## Explicit state

State contains mode, selected identity key, query, filters and viewport. Modes
are community, overview, search, node, category, solution and path.
The initial view fits the largest detected community, not the entire graph.
Selecting a node expands a local neighborhood. Overview is a deliberate action.
Pan, zoom, resize, pointer passage and keyboard focus do not change context.
Only clicks, Enter/Space activation, form submission and deliberate input changes
may do so. There are no hover handlers: pointer passage over a dot may give
purely presentational CSS feedback, and still never changes context.

Interaction motion is specified in `MOTION.md`. State commits synchronously on
the interaction; only pixels interpolate afterwards, so every dataset, status
field, list, panel and label is already final before the first animation frame.
Browser checks that read painted pixels wait for `#top[data-motion]="idle"`
rather than sleeping; at idle the label layer is fully revealed. Reduced motion
schedules no animation frames at all and leaves `data-motion` at `idle`.

Search indexes complete skill names and frontmatter descriptions, independent
of the initial community focus. Explicit dropdown filters constrain results.
Typing updates matching results; it does not select a skill. Clicking a result
keeps the query and result list available. Clear restores the search's originating
context and viewport, unless dropdown filters changed during search; in that case
it clears the query while preserving those explicit filters. Back returns
to the previous context with its query, selection, filters and viewport.
Reset returns to the initial largest community and clears the query/filters.
Escape is an explicit keyboard shortcut for Reset and suppresses the browser's
partial search-input clear. Background clicks do not clear context.

Paths use exact unweighted breadth-first search over the active evidence graph.
Use the selected skill as a start and another result as the end, or choose two
results. Report every edge's stated/inferred classification and supplied evidence.
Never imply that inferred edges are repository declarations.

Full `.card` and `.sol` HTML remains in the document, behind explicit library and
Solutions disclosures below the workspace. With JavaScript absent, the text
library still works. Actual skill-file links retain source and licence credit.

## Stable browser test contract

- `#top`: `data-ready`, `data-mode`, `data-query`, `data-selected-key`,
  `data-community`, `data-category`, `data-solution`, `data-evidence`,
  `data-matching-count`, `data-visible-count`, `data-path`.
- `#workspace-header`, `#workspace-title`, `#graph-region`, `#inspector`,
  `#panel`, `#statusbar`: layout and context regions.
- `#gsearch`, `#gcommunity`, `#gcategory`, `#gsolution`, `#gstated`,
  `#greset`, `#goverview`, `#gclear`, `#gback`, `#gpath`: controls.
- `#gfilters`: native filter disclosure, initially closed below 768px.
- `#gzoom-in`, `#gzoom-out`, `#gfit`: camera controls.
- `#gresults button[data-key]`: native, persistent result/member buttons.
  `aria-pressed` identifies the explicitly selected item.
- `#gsvg`, `#vp`, `.g-node[data-key]`, `.g-edge[data-i]`: graph geometry.
  `#vp` has an SVG `transform` plus `data-x`, `data-y`, `data-scale`.
  Nodes expose `data-visible` and `data-in-context`.
- Motion state: `#top[data-motion]` is `running` or `idle`,
  `#top[data-motion-beat]` names the beat (`first-paint`, `context`, `camera`,
  `search`, `path`, `selection`), and `#top[data-motion-flight]` is present only
  while dots travel. `#top[data-pulse]` marks a search pulse.
  `#graph-labels[data-revealed]` is `false` only while the scene is in flight.
  `.g-node` carries `data-entering`, `data-leaving` or `data-ambient` for the
  duration of its role; `.g-edge[data-draw]` marks a drawing path hop, and
  `.g-halo` is the single ambient element on the selected dot.
- `#graph-labels .g-nlabel[data-key]` and `.g-clabel[data-comm]`: screen-space
  labels. Check computed font size multiplied by screen CTM scale.
- `#selected-label-leader` and `#top[data-selected-offscreen]`: selected label
  callout and offscreen status. The root SVG has no runtime `viewBox`, so labels
  remain one CSS pixel per unit even while the header wraps on resize.
- `#status-context`, `#status-counts`, `#status-selected`, `#status-zoom`,
  `#status-evidence`: truthful dynamic status fields.
- `#panelname`, `#paneldesc`, `#panelchain`, `#panelev`, `#panelsource`:
  selected skill and evidence. Source is an actual file URL.

## Required checks

Build with `--write`, then `--check`; validate HTML. Measure label size with
screen CTM at desktop/mobile and minimum/maximum zoom. Measure expanded community
bounds against overview and graph/inspector/header/status non-overlap.
Type NDA, select a result, sweep the pointer across other nodes, move focus,
scroll, pan, zoom and resize. Query, selection and title must remain stable.
Exercise clear, back, filters, isolated communities, empty search, touch results,
path BFS, source links, no-JS disclosures and reduced-motion operation.
