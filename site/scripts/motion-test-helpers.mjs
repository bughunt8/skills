import { expect } from "@playwright/test";
import { openWorkspace } from "./workspace-test-helpers.mjs";

// Motion acceptance helpers. Everything here only *reads* state and geometry from
// the page; browser input stays real click/tap/mouse in the specs. Isolated
// planted defects mutate served response bytes in a disposable browser context —
// app.js/styles.css in the checkout are never edited, because the implementation
// worker owns them.

export const MOTION_DEFECT_ENV = "MOTION_PLANTED_DEFECT";

const DEFECTS = {
  // (a) An animation callback writes state. Real application bytes, wrong ones:
  // a raf loop started by a click keeps writing selection/query/title after the
  // synchronous commit, which is exactly what the contract forbids.
  "motion-writes-state": {
    url: /\/app\.js(?:\?.*)?$/,
    patch: (source) => source + `
/* Isolated acceptance defect: do not ship. */
(() => {
  const top = () => document.getElementById("top");
  addEventListener("click", () => {
    const started = performance.now();
    const step = () => {
      if (performance.now() - started > 240) {
        const root = top();
        if (!root) return;
        const other = [...document.querySelectorAll("#gresults button[data-key]")]
          .map((b) => b.dataset.key).find((k) => k !== root.dataset.selectedKey);
        if (other) root.dataset.selectedKey = other;
        root.dataset.query = "stolen-by-a-tween";
        const title = document.getElementById("workspace-title");
        if (title) title.textContent = "Stolen by a tween";
        return;
      }
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, true);
})();
`
  },
  // (b) A tween shrinks a label below the 16 CSS px floor while it is in flight.
  // Settled frames stay legal, so only across-transition sampling can see it.
  "tween-shrinks-label": {
    url: /\/styles\.css(?:\?.*)?$/,
    patch: (source) => source + `
/* Isolated acceptance defect: do not ship. */
#top[data-motion="running"] #graph-labels .g-nlabel,
#top[data-motion="running"] #graph-labels .g-clabel { font-size: 9px !important; }
`
  },
  // (g) The camera stops interpolating. The revised contract lets the camera
  // dataset update live per frame, so replaying "the current target" would still
  // be motion. This mutant HOLDS the pre-flight transform constant for the whole
  // flight and releases it only when `data-motion` returns to idle, writing the
  // committed camera once. Every other tween and the animation clock keep
  // running, so rAF counts cannot see it.
  "camera-interpolation-disabled": {
    url: /\/app\.js(?:\?.*)?$/,
    patch: (source) => `/* Isolated acceptance defect: do not ship. */
(function () {
  var apply = function () {
    var vp = document.getElementById("vp"), top = document.getElementById("top");
    if (!vp || !top) { setTimeout(apply, 0); return; }
    var set = Element.prototype.setAttribute.bind(vp);
    var held = null;
    var running = function () { return top.dataset.motion === "running"; };
    vp.setAttribute = function (name, value) {
      if (name !== "transform") return set(name, value);
      if (running()) {
        if (held === null) held = vp.getAttribute("transform") || value;
        return set("transform", held);
      }
      held = null;
      return set("transform", value);
    };
    new MutationObserver(function () {
      if (running()) return;
      held = null;
      var x = Number(vp.dataset.x), y = Number(vp.dataset.y), s = Number(vp.dataset.scale);
      if (isFinite(x) && isFinite(y) && isFinite(s)) {
        set("transform", "translate(" + x + " " + y + ") scale(" + s + ")");
      }
    }).observe(top, { attributes: true, attributeFilter: ["data-motion"] });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply);
  else apply();
})();
` + source
  },
  // (e) The label layer is blanked for the whole flight — the behaviour the
  // design review rejected. Geometry still reports 16 CSS px, so only an
  // effective-visibility check during flight can see it.
  "label-layer-hidden-in-flight": {
    url: /\/styles\.css(?:\?.*)?$/,
    patch: (source) => source + `
/* Isolated acceptance defect: do not ship. */
#top[data-motion="running"] #graph-labels,
#top[data-motion-flight] #graph-labels { opacity: 0 !important; }
`
  },
  // (f) The network blinks out mid-transition: both the real edges and the
  // in-flight stand-in path fade to nothing while the dots travel.
  "edges-vanish-in-flight": {
    url: /\/styles\.css(?:\?.*)?$/,
    patch: (source) => source + `
/* Isolated acceptance defect: do not ship. */
#top[data-motion="running"] .g-edges,
#top[data-motion="running"] .g-flight-edges,
#top[data-motion-flight] .g-edges,
#top[data-motion-flight] .g-flight-edges { opacity: 0 !important; }
`
  },
  // (c) Reduced motion is ignored: the application never observes the query.
  "reduced-motion-ignored": {
    url: /\/app\.js(?:\?.*)?$/,
    patch: (source) => `/* Isolated acceptance defect: do not ship. */
(() => {
  const real = window.matchMedia.bind(window);
  window.matchMedia = (query) => /prefers-reduced-motion/i.test(query)
    ? { media: query, matches: false, onchange: null, addListener() {}, removeListener() {},
        addEventListener() {}, removeEventListener() {}, dispatchEvent: () => false }
    : real(query);
})();
` + source
  },
  // (d) A transition is not interruptible: a stale tween target is replayed after
  // the interaction burst, so the settled camera is not the instant result.
  "stale-tween-wins": {
    url: /\/app\.js(?:\?.*)?$/,
    patch: (source) => source + `
/* Isolated acceptance defect: do not ship. */
(() => {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  let stale = null, timer = 0;
  addEventListener("click", () => {
    const vp = document.getElementById("vp");
    if (!vp) return;
    if (!stale) stale = { transform: vp.getAttribute("transform"), ...vp.dataset };
    clearTimeout(timer);
    timer = setTimeout(() => {
      vp.setAttribute("transform", stale.transform);
      vp.dataset.x = stale.x; vp.dataset.y = stale.y; vp.dataset.scale = stale.scale;
      stale = null;
    }, 700);
  }, true);
})();
`
  }
};

export async function plantMotionDefect(page) {
  const defect = process.env[MOTION_DEFECT_ENV];
  if (!defect) return null;
  const spec = DEFECTS[defect];
  if (!spec) throw new Error(`Unknown isolated motion defect: ${defect}`);
  await page.route(spec.url, async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, body: spec.patch(await response.text()) });
  });
  return defect;
}

// Instrumentation must exist before any application script runs, so animation
// frames and every data-motion flip are counted from the very first paint.
export async function installMotionProbes(page) {
  await page.addInitScript(() => {
    const probe = { rafTotal: 0, rafSince: 0, motionLog: [], longTasks: [], longTaskSupported: false };
    window.__motionProbe = probe;
    const nativeRaf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = (callback) => nativeRaf((time) => {
      probe.rafTotal++; probe.rafSince++;
      return callback(time);
    });
    const attach = () => {
      if (!document.documentElement) return false;
      new MutationObserver((records) => {
        for (const record of records) {
          if (record.target.id !== "top") continue;
          probe.motionLog.push({ t: performance.now(), attr: record.attributeName,
            value: record.target.getAttribute(record.attributeName) });
        }
      }).observe(document.documentElement, { subtree: true, attributes: true,
        attributeFilter: ["data-motion", "data-motion-beat"] });
      return true;
    };
    if (!attach()) document.addEventListener("readystatechange", attach, { once: true });
    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries())
          probe.longTasks.push({ start: entry.startTime, duration: entry.duration });
      }).observe({ type: "longtask", buffered: true });
      probe.longTaskSupported = true;
    } catch { probe.longTaskSupported = false; }
  });
}

export async function openMotionWorkspace(page) {
  await installMotionProbes(page);
  await plantMotionDefect(page);
  await openWorkspace(page);
  await expectMotionIdle(page);
}

// A page opened in a context this spec created itself (reduced motion), so it
// cannot use the shared fixture. Same bytes, same probes, same planted defect.
export async function openMotionPage(context, origin) {
  const page = await context.newPage();
  await installMotionProbes(page);
  await plantMotionDefect(page);
  await page.goto(`${origin}/index.html`, { waitUntil: "load" });
  await expect(page.locator("#top")).toHaveAttribute("data-ready", "true");
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(1100);
  await expectMotionIdle(page);
  return page;
}

export async function expectMotionIdle(page, timeout = 5000) {
  await expect(page.locator("#top"), "MOTION_IDLE_CONTRACT: #top[data-motion] must settle to idle")
    .toHaveAttribute("data-motion", "idle", { timeout });
}

export async function resetProbe(page) {
  await page.evaluate(() => {
    const probe = window.__motionProbe;
    probe.rafSince = 0; probe.motionLog.length = 0; probe.longTasks.length = 0;
  });
}

export async function readProbe(page) {
  return page.evaluate(() => ({ ...window.__motionProbe,
    motionLog: window.__motionProbe.motionLog.slice(),
    longTasks: window.__motionProbe.longTasks.slice() }));
}

// running -> idle episodes reconstructed from the recorded attribute flips.
export function motionEpisodes(log) {
  const episodes = [];
  let open = null;
  for (const entry of log) {
    if (entry.attr !== "data-motion") continue;
    if (entry.value === "running" && !open) open = entry.t;
    else if (entry.value === "idle" && open !== null) { episodes.push({ start: open, end: entry.t, duration: entry.t - open }); open = null; }
  }
  if (open !== null) episodes.push({ start: open, end: null, duration: Infinity });
  return episodes;
}

// Lightweight in-flight sample: cheap enough to poll many times per transition.
export async function sampleMotionFrame(page) {
  return page.evaluate(() => {
    const top = document.getElementById("top");
    // A computed font size of 16px proves nothing about an invisible label, and
    // "opacity: 0 on an ancestor" is exactly how a layer gets blanked for the
    // whole flight. Walk the ancestor chain and multiply the opacities: anything
    // at or below 0.05 effective is not on screen.
    const opacityCache = new Map();
    const effectiveOpacity = (el) => {
      if (!(el instanceof Element)) return 1;
      if (opacityCache.has(el)) return opacityCache.get(el);
      const style = getComputedStyle(el);
      const own = style.display === "none" || style.visibility === "hidden"
        ? 0 : Number(style.opacity);
      const value = own === 0 ? 0 : own * effectiveOpacity(el.parentElement);
      opacityCache.set(el, value);
      return value;
    };
    const painted = (el) => {
      if (effectiveOpacity(el) <= 0.05) return false;
      const b = el.getBoundingClientRect();
      return b.width > 0 && b.height > 0;
    };
    // "Visible" means placed for the current layout: not display:none, with real
    // text and a real screen CTM. The label layer's reveal opacity is a separate,
    // secondary beat, so a label whose layer has not faded in yet is still a
    // label whose geometry must already be final and legal.
    const measure = (el) => {
      const ctm = el.getScreenCTM();
      const computed = parseFloat(getComputedStyle(el).fontSize);
      return { key: el.dataset.key ?? el.dataset.comm ?? null, text: el.textContent.trim(),
        cssPx: computed * (ctm ? Math.hypot(ctm.a, ctm.b) : 0),
        painted: painted(el), opacity: effectiveOpacity(el) };
    };
    const labels = [...document.querySelectorAll("#graph-labels .g-nlabel, #graph-labels .g-clabel")]
      .filter((el) => getComputedStyle(el).display !== "none" && el.textContent.trim() && el.getScreenCTM())
      .map(measure);
    const paintedLabels = labels.filter((l) => l.painted);
    return {
      t: performance.now(),
      motion: top.dataset.motion ?? null,
      beat: top.dataset.motionBeat ?? null,
      selected: top.dataset.selectedKey ?? "",
      mode: top.dataset.mode ?? "",
      query: top.dataset.query ?? "",
      title: document.getElementById("workspace-title").textContent.trim(),
      revealed: document.getElementById("graph-labels")?.dataset.revealed ?? null,
      labelCount: labels.length,
      paintedLabelCount: paintedLabels.length,
      minCssPx: labels.length ? Math.min(...labels.map((l) => l.cssPx)) : null,
      minPaintedCssPx: paintedLabels.length ? Math.min(...paintedLabels.map((l) => l.cssPx)) : null,
      tiny: labels.filter((l) => l.cssPx < 16 - 1e-6),
      tinyPainted: paintedLabels.filter((l) => l.cssPx < 16 - 1e-6),
      // The network must never blink out mid-transition: either the real curved
      // edges are still on screen, or the single in-flight path that stands in
      // for them is. Both fading away is the ghost-edge regression.
      edges: (() => {
        const group = document.querySelector(".g-edges");
        let drawn = 0;
        if (!group || effectiveOpacity(group) > 0.05) {
          for (const el of document.querySelectorAll(".g-edge")) {
            const style = getComputedStyle(el);
            if (style.display === "none" || Number(style.opacity) <= 0.05) continue;
            const box = el.getBoundingClientRect();
            if (box.width > 0.01 || box.height > 0.01) drawn++;
            if (drawn >= 25) break;
          }
        }
        const path = document.querySelector(".g-flight-edges, #flight-edges");
        let flight = null;
        if (path) {
          const d = path.getAttribute("d") || "";
          let length = 0;
          try { length = path.getTotalLength(); } catch { length = 0; }
          flight = { hasPath: !!d, length, opacity: effectiveOpacity(path),
            visible: !!d && length > 0 && effectiveOpacity(path) > 0.05 };
        }
        return { drawn, flight, structure: drawn > 0 || !!flight?.visible };
      })()
    };
  });
}

const round = (value) => Math.round(value * 100) / 100;

// Live camera reading. Deliberately tiny: it is polled hard during a flight, and
// it never waits for anything, so it can observe the camera actually travelling.
// `matrix` is the on-screen CTM of the viewport group (what the eye sees) and
// `target` is the committed camera on `#vp`'s dataset (what it must settle on).
export async function sampleCamera(page) {
  return page.evaluate(() => {
    const top = document.getElementById("top"), vp = document.getElementById("vp");
    const ctm = vp.getScreenCTM();
    return {
      t: performance.now(),
      motion: top.dataset.motion ?? null,
      beat: top.dataset.motionBeat ?? null,
      transform: vp.getAttribute("transform"),
      matrix: ctm ? { a: ctm.a, b: ctm.b, c: ctm.c, d: ctm.d, e: ctm.e, f: ctm.f } : null,
      target: { x: Number(vp.dataset.x), y: Number(vp.dataset.y), scale: Number(vp.dataset.scale) }
    };
  });
}

// Screen displacement of the scene origin between two camera samples, plus the
// scale change. A camera that never interpolates produces zeroes here.
export function cameraDisplacement(a, b) {
  if (!a?.matrix || !b?.matrix) return { dx: 0, dy: 0, distance: 0, dScale: 0 };
  const dx = b.matrix.e - a.matrix.e, dy = b.matrix.f - a.matrix.f;
  return { dx, dy, distance: Math.hypot(dx, dy),
    dScale: Math.hypot(b.matrix.a, b.matrix.b) - Math.hypot(a.matrix.a, a.matrix.b) };
}

// The settled truth an instant render must reproduce: #top, the #vp transform and
// where every in-context dot actually lands on screen (implementation-agnostic:
// group translate or geometry attribute, both resolve through the screen CTM).
export async function motionSnapshot(page) {
  return page.evaluate(() => {
    const r = (value) => Math.round(value * 100) / 100;
    const top = document.getElementById("top"), vp = document.getElementById("vp");
    const keys = ["mode", "query", "selectedKey", "community", "category", "solution",
      "evidence", "matchingCount", "visibleCount", "path", "selectedOffscreen"];
    return {
      top: Object.fromEntries(keys.map((k) => [k, top.dataset[k] ?? null])),
      title: document.getElementById("workspace-title").textContent.trim(),
      status: Object.fromEntries(["status-context", "status-counts", "status-selected",
        "status-zoom", "status-evidence"].map((id) =>
        [id, (document.getElementById(id)?.textContent ?? "").trim()])),
      vp: { transform: vp.getAttribute("transform"), x: r(Number(vp.dataset.x)),
        y: r(Number(vp.dataset.y)), scale: r(Number(vp.dataset.scale)) },
      nodes: [...document.querySelectorAll(".g-node")]
        .filter((node) => node.dataset.inContext === "true")
        .map((node) => {
          const dot = node.querySelector(".g-dot"), ctm = dot.getScreenCTM();
          const x = Number(dot.getAttribute("cx")), y = Number(dot.getAttribute("cy"));
          return { key: node.dataset.key,
            transform: node.getAttribute("transform") || "",
            screenX: ctm ? r(ctm.a * x + ctm.c * y + ctm.e) : null,
            screenY: ctm ? r(ctm.b * x + ctm.d * y + ctm.f) : null };
        }).sort((a, b) => a.key.localeCompare(b.key))
    };
  });
}

// 18273ef splits the contract in two. These commit instantly on the acting frame
// and must never mutate from a tween:
export const SEMANTIC_TOP_KEYS = ["mode", "query", "selectedKey", "community",
  "category", "solution", "evidence", "matchingCount", "path"];
// These are measurements of the live view. They may truthfully change per frame
// while the camera moves, and equal the instant render once idle:
export const VIEW_TOP_KEYS = ["visibleCount", "selectedOffscreen"];

export function semanticTop(snapshot) {
  return Object.fromEntries(SEMANTIC_TOP_KEYS.map((k) => [k, snapshot.top[k]]));
}

export function viewTop(snapshot) {
  return Object.fromEntries(VIEW_TOP_KEYS.map((k) => [k, snapshot.top[k]]));
}

// Is the view dataset telling the truth about the pixels right now? Counts the
// dots actually painted inside the SVG frame and compares with
// `#top[data-visible-count]`. No waiting: it is called mid-flight.
export async function sampleViewTruth(page) {
  return page.evaluate(() => {
    const top = document.getElementById("top");
    const frame = document.getElementById("gsvg").getBoundingClientRect();
    let onScreen = 0;
    for (const node of document.querySelectorAll(".g-node")) {
      const dot = node.querySelector(".g-dot");
      if (!dot) continue;
      const style = getComputedStyle(node);
      if (style.display === "none" || style.visibility === "hidden") continue;
      const box = dot.getBoundingClientRect();
      const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
      if (!box.width || !box.height) continue;
      if (cx >= frame.x && cx <= frame.x + frame.width &&
          cy >= frame.y && cy <= frame.y + frame.height) onScreen++;
    }
    return { motion: top.dataset.motion ?? null,
      reported: Number(top.dataset.visibleCount),
      painted: onScreen,
      transform: document.getElementById("vp").getAttribute("transform"),
      target: { x: Number(document.getElementById("vp").dataset.x),
        y: Number(document.getElementById("vp").dataset.y),
        scale: Number(document.getElementById("vp").dataset.scale) } };
  });
}

export function comparableSnapshot(snapshot) {
  return { top: snapshot.top, title: snapshot.title, vp: snapshot.vp, nodes: snapshot.nodes };
}

export async function resultKeys(page) {
  return page.locator("#gresults button[data-key]").evaluateAll((items) => items.map((i) => i.dataset.key));
}

export function resultFor(page, key) {
  return page.locator(`#gresults button[data-key="${key.replace(/["\\]/g, "\\$&")}"]`);
}

export async function tapOrClick(locator, testInfo) {
  if (testInfo.project.use.hasTouch) await locator.tap();
  else await locator.click();
}

// Camera controls live beside the graph on desktop; on phones they may sit behind
// the native filters disclosure, which is opened with real input.
export async function ensureVisible(page, selector) {
  const locator = page.locator(selector);
  if (!(await locator.isVisible())) {
    const disclosure = page.locator("#gfilters > summary");
    if (await disclosure.count()) await disclosure.click();
  }
  await expect(locator, `${selector} must be reachable`).toBeVisible();
  return locator;
}

export { round };
