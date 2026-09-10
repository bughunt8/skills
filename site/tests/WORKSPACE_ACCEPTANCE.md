# Graph workspace acceptance inventory

Contract: `site/UI_NAVIGATION.md` plus `site/MOTION.md`, authored by the
implementation worker and accepted by the test worker. This replaces the obsolete
scroll presentation; `MOTION.md` adds interaction motion on top of it.

## Gates

| Area | Browser proof |
| --- | --- |
| Content and identity | Exactly 490 skill cards/nodes and 50 Solutions; unique identity keys; every Solution step and edge endpoint resolves; source/licence provenance and no-JS disclosures remain. |
| First viewport | Visible top filters (native mobile Filters disclosure permitted by coordinator; opened with real input), populated default community, dynamic h1, docked inspector, graph filling available area, bottom status; measured region rectangles do not overlap. Hidden disclosure descendants never count as visible controls. |
| Readability | Every painted graph label measured with computed font size × SVG screen-CTM scale, minimum 16 actual CSS px. Nonempty labels required. Bounding rectangles detect clipping, label-label and label-vs-other-painted-dot collisions (transparent hit zones excluded). Small communities up to 8 members expose every graph label on desktop; every member remains in the full actionable list. Selected full name remains reachable. |
| Search — critical | Type NDA and description-only terms; preserve query/results/mode while crossing unrelated nodes/canvas; select an exact identity using real click/tap; neighborhood camera changes; hover/wheel/idle never change selection. Edit/clear/no-result/multi-result/Escape reset; persistent result targets ≥44px and real keyboard activation. |
| Filters and truth | Community/category/Solution/evidence intersections compared with independently computed data; matching/visible counts and inspector/title agree; no stale selected identity after deliberate context change. |
| Navigation | Overview, fit, zoom, pan, Back and reset are explicit; camera input leaves selection unchanged. Clear restores the pre-search community/category/overview, not an accidental 490-node overview. Path A/B uses real BFS edges; disconnected pair reports no path, not a fabricated walk. |
| Responsive | 1440×900, 1280×800, 1024×768, 390×844 and 720×450 CSS-pixel viewport (200%-zoom-equivalent reflow at 1440×900). Controls reachable and no horizontal overflow. Actual browser chrome zoom is not claimed. |
| Keyboard and accessibility | One roving graph tab stop, arrow navigation without implicit selection; Enter selects; skip link works; axe WCAG 2.1 AA without excluded layers in default/search/selected/reduced-motion states. |
| No scroll choreography | No HUD/rail/pin spacers, GSAP, ScrollTrigger or Lenis; real wheel and idle leave context stable. Native document scrolling remains available for fallback disclosures. |
| Resilience/security | No remote runtime requests, local fonts actually load, missing app/data fallback, production CSP applied while interacting, no inline style escape hatch; HTML/secrets gates retained. |
| Graph motion | `MOTION.md` "Required checks", one Node Playwright test each: `MOTION_COMMIT_SYNC` (with zero wait after a click: the semantic datasets — mode, query, selected key, community, category, solution, evidence, matching count, path — the title and every visible label's screen-CTM size; the semantic set must be identical again at idle, while the view measurements — visible count, selected-offscreen — are checked for truthfulness against the painted dots on every in-flight frame and for equality with the pixels and the committed camera at idle), `MOTION_LABEL_FLOOR` (labels sampled repeatedly across a whole transition never fall under 16 CSS px, and on every in-flight frame a real number of labels are effectively visible — no `display`/`visibility` loss and no cumulative ancestor opacity at or below 0.05 — with the smallest visible label still at least 16 CSS px), `MOTION_CAMERA_TRAVEL` (for the context, zoom and Fit beats alike: successive in-flight readings of the `#vp` screen CTM differ by more than a pixel of displacement or a real scale change, and the settled camera equals the committed `#vp` target exactly), `MOTION_SELECTED_ANCHOR` (through zoom out, a second zoom out and Fit, sampled live with no idle wait: no frame paints zero labels, and while the selected dot is on screen its own name stays painted above 0.05 effective opacity and at or above 16 CSS px with its leader visible and within 6px of the dot; frames where the selection is genuinely offscreen must be reported by the `#status-selected` cue), `MOTION_EDGE_CONTINUITY` (every sampled in-flight frame shows visible edge structure: real `.g-edge` paths or the in-flight stand-in path, and the settled scene shows its edges again), `MOTION_POINTER_IMMUNITY` (real pointer sweep across other dots while a tween runs leaves selection/query/title/mode alone), `MOTION_INTERRUPTIBLE` (rapid interrupting clicks, zooms and result selections settle on exactly the reduced-motion instant `#vp` transform, dot positions and `#top`), `MOTION_REDUCED_MOTION` (zero animation frames, `data-motion` never leaves `idle`, no ambient breath, end state equals the animated end state), `MOTION_IDLE_RETURN` (`data-motion` back to `idle` within 900ms of every beat, measured from recorded attribute flips), `MOTION_LONG_TASK` (no PerformanceObserver long task over 120ms during a community→node transition at overview scale), `MOTION_AMBIENT_SINGLETON` (exactly one `[data-ambient]` element while a skill is selected, none otherwise). Every wait is on `#top[data-motion="idle"]` or an explicit attribute; no fixed sleeps stand in for settling. |
| Non-vacuity | Isolated planted hover-stealing, tiny-font and label-over-node response defects must fail the targeted Node Playwright checks; baseline and restored runs must pass. Proof runner records logs and restoration. Motion adds seven planted defects in `scripts/prove-motion-defects.mjs`: an animation callback that writes state/selection, a tween that shrinks a label below 16px, ignored `prefers-reduced-motion`, a stale tween target that wins after an interrupt, a label layer blanked to zero opacity for the whole flight (geometry still reports 16 CSS px), all edge structure faded to zero mid-transition, and a camera that holds its pre-flight transform constant for the whole flight, releasing to the committed camera only at settle (the animation clock and every other tween keep running, so rAF counts cannot see it). Each must fail its named assertion and pass again once removed. |
| Deployment compatibility | Apply the actual workflow rsync exclusions into an external fixture; retired vendor bytes must be absent. Run the implementation's Node smoke script against those generated bytes under the production CSP. This is not a live Hostinger/Apache verification. |
| Returning-client cache | Runtime URLs contain exact content digests. Prime old unversioned assets in the real browser HTTP cache, serve new HTML, and verify the current workspace initializes and selects a result. Missing-script fallback routes match the URL pathname and prove the request was blocked, including versioned URLs. |

## Execution and evidence

## Timing adaptation for a live camera (approved at MOTION.md 18273ef)

Before the camera moved, every camera change was instant, so the pre-motion
specs could read geometry and camera scale on the frame after a click. Under the
corrected contract the camera is a live per-frame measurement: the first frame
after a zoom still carries the old scale, a mid-flight scale is not the value
those tests reason about, and mid-flight label geometry is the culled core with
leaders still travelling. Three narrow changes, all in test-owned files:

1. `measureLabels`, `paintedGraphCount` and `assertLayout` wait for
   `#top[data-motion="idle"]` before sampling. They only ever asserted about
   settled geometry; what they assert is unchanged.
2. In `workspace.spec.js` ("overview fit zoom pan Back and reset") and the
   production-CSP test in `resilience.spec.js`, each camera-scale or camera-value
   comparison waits for idle after the activation that causes it. The semantic
   read after a zoom stays immediate and unwaited — in fact the workspace test
   now asserts explicitly, with no wait, that a zoom does not touch semantic
   state.
3. Nothing else waits. `readState` and `activate` are untouched, no semantic
   assertion waits, and no in-flight floor waits: the motion spec observes the
   flight directly and `MOTION_SELECTED_ANCHOR` exists precisely to catch a
   mid-flight blackout. The 16 CSS px floor is not relaxed anywhere.

Inventory: **150 Node Playwright checks** across eight spec files and two browser
profiles (desktop Chromium and touch-enabled mobile Chromium), with no skips.
That is 75 distinct tests run at desktop 1440x900 and phone 390x844; the eleven
motion checks in `tests/graph-motion.spec.js` run at both sizes.
The extra review regressions cover Clear-origin restoration and selected-label
clearance from neighboring painted dots. Dark-theme axe is included.
The cache follow-up adds four checks for exact asset digests and returning-client
HTTP cache behavior. The motion follow-up adds twenty-two checks (eleven tests times
two profiles) for `site/MOTION.md`.

Non-vacuity proofs:

```sh
node scripts/prove-workspace-defects.mjs   # three planted workspace defects
SITE_TEST_PORT=8241 node scripts/prove-motion-defects.mjs   # seven planted motion defects
```

Both planted defects only rewrite served response bytes in a disposable browser
context. Source files are hashed before and after and must be unchanged.

Use the actual locked **Node** Playwright suite, not a Python analogue:

```sh
SITE_TEST_PORT=8241 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/path/to/chromium npm test -- --workers=1
```

The environment override is optional; CI leaves it unset. Browser input uses
real click/tap, keyboard and mouse/wheel events: no forced clicks and no
`dispatchEvent` selection. Page evaluation only reads state/geometry.

Set `WORKSPACE_EVIDENCE_DIR` to an absolute directory outside the repository to
save JSON measurements and screenshots. Each artifact names the project/test.
Failures are findings, not reasons to skip or weaken requirements. A passing
axe scan is not a substitute for geometry, actual-pixel type or interaction tests.
