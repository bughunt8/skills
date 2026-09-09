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

**State commits synchronously. Only pixels interpolate.**

`render()` writes the whole truth before the first animation frame: `#top`
datasets, status fields, the results list, the inspector, and label geometry for
the *final* layout. A tween may then move dots, fade edges and reveal the label
layer. No animation callback may write state, selection, query, mode, counts or
label text. A test that reads `#top` or a label's computed size immediately after
a click sees the settled answer with no waiting.

This is what keeps the two hard-won behaviours intact: pointer travel cannot
steal a selection, and a label is never smaller than 16 CSS pixels.

## Motion personality

Corporate, because this is a working tool. One signature curve carries most of
the motion; big context changes borrow the emphasized entrance curve.

| Token | Value | Use |
| --- | --- | --- |
| `--motion-quick` | 160ms | Hover, press, dim, flash |
| `--motion-standard` | 260ms | Panel crossfade, camera nudge, zoom button |
| `--motion-slow` | 460ms | Context change: camera and scene morph |
| `--ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | Signature, ~80% of motion |
| `--ease-enter` | `cubic-bezier(0.05, 0.7, 0.1, 1)` | Entering nodes, first paint |
| `--ease-exit` | `cubic-bezier(0.3, 0, 1, 1)` | Leaving nodes |

Exits run at 65% of the matching entrance. Overshoot stays at or below 3%.
Camera distance scales duration up to a 600ms ceiling, never past it. Linear
easing is not used for spatial movement.

## The three layers

- **Primary** — the camera and the dots. The anchor of the new context (the
  selected skill, or the community's highest-degree member) holds its place while
  the rest of the world rearranges around it.
- **Secondary** — edges fade in behind the dots that already arrived, the label
  layer reveals, the inspector crossfades, a changed status field flashes once.
- **Ambient** — a single slow halo breath on the selected dot. One element only.
  It stops when nothing is selected and never runs under reduced motion.

## Beats

| Beat | Trigger | Duration | Motion |
| --- | --- | --- | --- |
| First paint | Load | ≤700ms | Wave reveal outward from the anchor: dots scale 0.9→1 and fade, 30–60ms stagger, then edges, then labels |
| Context change | Click, result, filter, Back, Overview, Reset | 460ms (600ms ceiling) | Camera tween plus scene morph; persisting dots travel, entering dots fade and scale in, leaving dots exit at 65% |
| Camera only | Zoom buttons, Fit | 260ms | `#vp` transform tween, labels re-placed at settle |
| Search matches | Committed query change | 320ms ×2 | Matched dots pulse a ring twice and stop; unmatched dots dim. Selection untouched |
| Path trace | Path completed | ≤600ms total | Hops draw in sequence via `stroke-dashoffset`, ~120ms per hop, compressed to fit the ceiling |
| Hover | Pointer over a dot | 150ms | CSS-only dot scale and rim. No JavaScript handler, so it cannot reach state |
| Selection | Selected key changes | 260ms | Halo scales in, then the ambient breath begins |

Stagger stays inside the wave budget: 30–60ms per step, under 500ms in total.
No more than a third of the visible dots are in motion at once during a wave.

## Performance

Animate `transform`, `opacity` and `stroke-dashoffset` only. Never width, height,
`x`/`y` attributes, positions, or anything that reflows.

At overview scale the scene holds 490 dots and 1140 edges. Per frame, write one
`transform` per moving dot group and nothing else: edge geometry is never rebuilt
mid-flight, so edges fade out, stay hidden while the dots travel, and fade back in
at settle. One `requestAnimationFrame` loop exists at a time and it stops itself
when idle.

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
- Every dataset, status field and label size listed in `UI_NAVIGATION.md` is
  correct on the frame the interaction commits, before any tween runs.

## Required checks

Beyond the existing suite, all of which must still pass:

1. Read `#top` and every visible label's screen-CTM size immediately after a
   click, with no wait. Mode, selection, query, counts and 16px hold.
2. Sample labels across the whole transition. Nothing drops below 16px.
3. Sweep the pointer across other dots while a transition runs. Selection,
   query and title do not move.
4. Fire rapid clicks, zooms and result selections that interrupt each other.
   Final `#vp` transform, dot translates and `#top` match the reduced-motion
   instant result exactly.
5. With reduced motion, assert no animation frames run and the end state equals
   the animated end state.
6. `data-motion` returns to `idle` within 900ms of any beat.
7. During a community→node transition, no long task exceeds 120ms.
8. Exactly one ambient element animates, and none when nothing is selected.
9. Defect proofs must fail when motion writes state, when a tween shrinks a
   label below 16px, when reduced motion is ignored, and when a transition is
   not interruptible.
