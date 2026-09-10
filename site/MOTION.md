# Graph motion

Interaction motion for the skill workspace. No scroll drives anything: the removal
of scroll choreography in `UI_NAVIGATION.md` stands, and `tests/motion.spec.js`
keeps guarding it. Motion here is caused by a click, an activation, a control, a
committed query change or first paint, and nothing else.

Sources for the rules below: the motion-design principles at
<https://github.com/lottiefiles/motion-design-skill> (personality, duration,
easing, choreography and the 1/3 rules) and the UI rules at
<https://github.com/nextlevelbuilder/ui-ux-pro-max-skill> (animation timing,
interruptibility, reduced motion, transform-only performance).

## The rule that protects the workspace

**Semantic state commits synchronously. View measurements describe the current frame.**

Mode, selected identity, query, filters, history, path, title, results, inspector
content and matching count commit before the first animation frame. Animation
callbacks must never change those values or select a different skill.

Camera transforms and their datasets, onscreen counts, label positions and leader
lines are view measurements. They may update during a tween, but must describe the
pixels currently painted. At idle, geometry must equal the instant-render result.
The previous contract incorrectly required these values to describe both the final
layout and an interpolated frame simultaneously. This revision corrects that
conflict without relaxing search stability or the 16px painted-label floor.

This is what keeps the two hard-won behaviours intact: pointer travel cannot
steal a selection, and a label is never smaller than 16 CSS pixels.

## Motion personality

Corporate, because this is a working tool. One signature curve carries most of
the motion; big context changes borrow the emphasized entrance curve.

| Token | Value | Use |
| --- | --- | --- |
| `--motion-quick` | 160ms | Hover, press, dim, flash |
| `--motion-standard` | 260ms | Panel crossfade, camera nudge, zoom button |
| `--motion-slow` | 420ms | Context change: bounded camera entry |
| `--ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | Signature, ~80% of motion |
| `--ease-enter` | `cubic-bezier(0.05, 0.7, 0.1, 1)` | Entering nodes, first paint |
| `--ease-exit` | `cubic-bezier(0.3, 0, 1, 1)` | Leaving nodes |

Exits run at 65% of the matching entrance. Overshoot stays at or below 3%.
Camera distance scales duration up to a 600ms ceiling, never past it. Linear
easing is not used for spatial movement.

## The three layers

- **Primary:** commit the new scene layout, then move the camera into it with a
  bounded translation. Derive direction from the old and new anchor positions.
  Limit displacement to 6% of the canvas, with no theatrical fly-through.
- **Secondary:** keep real edges visible throughout. Retain the selected label
  and a small collision-safe set of labels during flight, then restore the full
  settled label layout. Optional exit ghosts are decoration, never click targets.
- **Ambient:** a single slow halo breath on the selected dot, absent under reduced
  motion. It does not require an idle JavaScript animation loop.

## Beats

| Beat | Trigger | Duration | Motion |
| --- | --- | --- | --- |
| First paint | Load | Readable immediately after layout; decoration ≤500ms | Dots may enter in a bounded wave, but real edges and a readable label core are not hidden behind the wave |
| Context change | Click, result, filter, Back, Overview, Reset | 420ms, 600ms ceiling | Instant scene layout plus bounded camera translation into the destination; no per-node layout morph |
| Camera only | Zoom buttons, Fit | 260ms | Real camera transform interpolation; screen-space labels remain readable and follow their dots |
| Search matches | Committed query change | ≤400ms | Brief matched-dot emphasis; non-matches remain filtered out, never falsely described as dimmed |
| Path trace | Path completed | ≤600ms total | Hops draw in sequence via `stroke-dashoffset`, ~120ms per hop, compressed to fit the ceiling |
| Hover | Pointer over a dot | 150ms | CSS-only dot scale and rim. No JavaScript handler, so it cannot reach state |
| Selection | Selected key changes | 260ms | Halo scales in, then the ambient breath begins |

Use bounded wave buckets rather than an unbounded delay per node. The wave and
its last dot must finish within 500ms. The camera is one coordinated moving scene,
not hundreds of independent animated node layouts.

## Performance

Animate `transform`, `opacity` and `stroke-dashoffset` only. Never width, height,
`x`/`y` attributes, positions, or anything that reflows.

The scene layout is fixed during a camera flight. Real node and edge geometry
therefore moves together through the parent transform, without rebuilding paths.
Project screen-space labels separately; cache text measurements and bound the
in-flight set. A selected label remains visible, with at least one genuinely
painted label and visible edge structure on every populated connected frame.

Run one requestAnimationFrame loop only while it performs visual work. Use
cancellable animation completion or timers for CSS-only effects, not a no-op
frame clock. Remove unused per-node morph and ghost-edge machinery. An animation
counter or running flag is not evidence that pixels moved.

## Interruptibility

Any new interaction cancels the tween in flight and the final semantic state and
geometry must be exactly what an instant render would have produced. Motion never
blocks input, never queues, and never replays a stale target.

## Reduced motion

`prefers-reduced-motion: reduce` skips every tween, the wave, the pulses, the
draw-in and the ambient breath. The final state is applied in one pass and no
animation loop starts. The existing global CSS reset stays.

## Test contract

Added to the contract in `UI_NAVIGATION.md`:

- `#top[data-motion]` is `running` while a tween is in flight and `idle`
  otherwise. It is `idle` under reduced motion at all times. Browser checks wait
  on `idle` instead of sleeping.
- `#top[data-motion-beat]` names the last beat: `first-paint`, `context`,
  `camera`, `search`, `path`, `selection`.
- `#graph-labels[data-revealed]` reports whether the label layer is shown.
- `.g-node[data-entering]`, `.g-node[data-leaving]`, `.g-node[data-ambient]`
  mark the current motion role of a dot.
- Semantic fields are correct at commit without waiting. View datasets match the
  current frame, then match the instant result at idle. Settled geometry checks
  may wait for idle; semantic and in-flight checks must not.

## Required checks

Beyond the existing suite, all of which must still pass:

1. Read semantic fields and painted label size immediately after a click, with no
   wait. Mode, selection, query, matching count and the 16px floor hold.
2. Sample labels across the whole transition, including ancestor opacity and
   viewport clipping. At least one is painted, the selected label remains
   readable when in view, and none drops below 16px. Check the visible core for
   collisions and attached leaders, not just hidden elements' computed size.
3. Sweep the pointer across other dots while a transition runs. Selection,
   query and title do not move.
4. Fire rapid clicks, zooms and result selections that interrupt each other.
   Final `#vp` transform, dot translates and `#top` match the reduced-motion
   instant result exactly.
5. With reduced motion, assert no motion animation frames run and the end state
   equals the animated end state. With motion allowed, measure actual camera
   displacement over multiple frames; a no-op frame loop must fail.
6. `data-motion` returns to `idle` within 900ms of any beat.
7. During a community→node transition, no long task exceeds 120ms.
8. Exactly one ambient element animates, and none when nothing is selected.
9. Defect proofs must fail when motion writes semantic state, when a tween shrinks a
   label below 16px, when reduced motion is ignored, and when a transition is
   not interruptible. Additional proofs must reject label blackout, edge blackout
   and a context/camera beat whose pixels never move.
