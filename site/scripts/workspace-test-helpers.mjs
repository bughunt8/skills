import { expect } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const pageErrors = new WeakMap();
export async function openWorkspace(page) {
  if (!pageErrors.has(page)) {
    const errors = [];
    pageErrors.set(page, errors);
    page.on("pageerror", (error) => errors.push(String(error)));
  }
  const defect = process.env.WORKSPACE_PLANTED_DEFECT;
  if (defect === "hover-steals-search") {
    await page.route(/\/app\.js(?:\?.*)?$/, async (route) => {
      const response = await route.fetch();
      const original = await response.text();
      const marker = "  function selectNode(key) {";
      if (original.split(marker).length !== 2) throw new Error("Hover defect insertion marker must occur exactly once");
      // Deliberately wrong application bytes, not a synthetic user action:
      // actual pointer entry invokes the application's genuine selection path.
      const defectCode = `  svg.addEventListener("pointerover", (event) => {
    const node = event.target.closest(".g-node");
    if (node) selectNode(node.dataset.key);
  });
`;
      await route.fulfill({ response, body: original.replace(marker, defectCode + marker) });
    });
  } else if (defect === "unreadable-font") {
    await page.route(/\/styles\.css(?:\?.*)?$/, async (route) => {
      const response = await route.fetch();
      await route.fulfill({ response, body: await response.text() +
        "\n/* Isolated acceptance defect: do not ship. */\n#graph-labels text { font-size: 8px !important; }\n" });
    });
  } else if (defect === "label-over-node") {
    await page.route(/\/app\.js(?:\?.*)?$/, async (route) => {
      const response = await route.fetch();
      const original = await response.text();
      const marker = "\n  }\n\n  function contextTitle() {";
      if (original.split(marker).length !== 2) throw new Error("Label defect insertion marker must occur exactly once");
      // An intentionally defective renderer positions a real visible label on
      // another node. No browser evaluation or user action is simulated.
      const defectCode = `
    const faultyLabel = [...svg.querySelectorAll(".g-nlabel")].find((el) =>
      getComputedStyle(el).display !== "none" && el.getBoundingClientRect().width > 0);
    const faultyTarget = [...svg.querySelectorAll(".g-node")].find((el) =>
      el.dataset.visible === "true" && el.dataset.key !== faultyLabel?.dataset.key);
    if (faultyLabel && faultyTarget) {
      const dot = faultyTarget.querySelector(".g-dot").getBoundingClientRect();
      const frame = svg.getBoundingClientRect();
      const x = dot.x + dot.width / 2 - frame.x - 5;
      const y = dot.y + dot.height / 2 - frame.y + 6;
      faultyLabel.setAttribute("x", x);
      faultyLabel.setAttribute("y", y);
      faultyLabel.querySelectorAll("tspan").forEach((span) => span.setAttribute("x", x));
    }`;
      await route.fulfill({ response, body: original.replace(marker, defectCode + marker) });
    });
  } else if (defect) throw new Error(`Unknown isolated workspace defect: ${defect}`);
  await page.goto("/index.html", { waitUntil: "load" });
  await expect(page.locator("#top")).toHaveAttribute("data-ready", "true");
  await page.evaluate(() => document.fonts.ready);
  // The rejected implementation suppressed hover while its camera moved. A
  // settled mouse entry (>660ms) is mandatory: immediate hover hid the defect.
  await page.waitForTimeout(1100);
}

// MOTION.md makes the settled frame observable: `#top[data-motion]` is `running`
// while a tween is in flight and `idle` otherwise (always `idle` under reduced
// motion). Geometry assertions measure the settled layout, so they wait on that
// attribute rather than on a sleep. Pages without the motion layer (the missing
// app.js fallbacks in resilience.spec.js) simply have nothing to wait for.
export async function settleMotion(page, timeout = 5000) {
  await page.waitForFunction(() => {
    const top = document.getElementById("top");
    return !top || top.dataset.motion === undefined || top.dataset.motion === "idle";
  }, null, { timeout });
}

export async function assertNoRuntimeErrors(page) {
  expect(pageErrors.get(page) || [], "workspace must not throw during partially completed render").toEqual([]);
}

export async function ensureFiltersOpen(page) {
  if (!(await page.locator("#gcommunity").isVisible())) {
    const disclosure = page.locator("#gfilters > summary");
    await expect(disclosure, "mobile filters must have an actual reachable control").toBeVisible();
    await disclosure.click();
  }
  await expect(page.locator("#gcommunity")).toBeVisible();
}

export async function activate(locator, testInfo) {
  if (testInfo.project.use.hasTouch) await locator.tap();
  else await locator.click();
}

export async function readState(page) {
  return page.evaluate(() => {
    const d = document.getElementById("top").dataset;
    const vp = document.getElementById("vp").dataset;
    return {
      context: {
        mode: d.mode, query: d.query, selected: d.selectedKey,
        community: d.community, category: d.category, solution: d.solution,
        evidence: d.evidence, path: d.path,
        title: document.getElementById("workspace-title").textContent.trim(),
        results: [...document.querySelectorAll("#gresults button[data-key]")].map((e) => e.dataset.key)
      },
      matching: Number(d.matchingCount), visible: Number(d.visibleCount),
      camera: { x: Number(vp.x), y: Number(vp.y), scale: Number(vp.scale) }
    };
  });
}

// Timing adaptation approved in MOTION.md at 18273ef: the camera is now a live
// per-frame measurement, so a settled-geometry helper that samples immediately
// after a camera activation reads a frame of the flight (culled core labels,
// leaders still travelling) instead of the settled layout it asserts about.
// These three helpers measure SETTLED geometry only, so each waits for
// `#top[data-motion="idle"]` first. Nothing about what they assert changes, and
// no semantic read and no in-flight floor waits: `readState`, `activate` and the
// motion spec are untouched.
export async function paintedGraphCount(page) {
  await settleMotion(page);
  return page.evaluate(() => {
    const frame = document.getElementById("gsvg").getBoundingClientRect();
    return [...document.querySelectorAll(".g-node")].filter((node) => {
      for (let el = node; el instanceof Element; el = el.parentElement) {
        const style = getComputedStyle(el);
        if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return false;
      }
      const dot = node.querySelector(".g-dot"), matrix = dot.getScreenCTM();
      if (!matrix) return false;
      const x = Number(dot.getAttribute("cx")), y = Number(dot.getAttribute("cy"));
      const screenX = matrix.a * x + matrix.c * y + matrix.e;
      const screenY = matrix.b * x + matrix.d * y + matrix.f;
      return screenX >= frame.left && screenX <= frame.right &&
        screenY >= frame.top && screenY <= frame.bottom;
    }).length;
  });
}

export async function measureLabels(page) {
  await settleMotion(page);
  return page.evaluate(() => {
    const frame = document.getElementById("gsvg").getBoundingClientRect();
    function painted(el) {
      for (let e = el; e instanceof Element; e = e.parentElement) {
        const s = getComputedStyle(e);
        if (s.display === "none" || s.visibility === "hidden" || Number(s.opacity) === 0) return false;
      }
      const b = el.getBoundingClientRect();
      return b.width > 0 && b.height > 0;
    }
    const labels = [...document.querySelectorAll("#graph-labels .g-nlabel, #graph-labels .g-clabel")]
      .filter(painted).map((e) => {
        const b = e.getBoundingClientRect(), ctm = e.getScreenCTM();
        const computed = parseFloat(getComputedStyle(e).fontSize);
        return {
          key: e.dataset.key ?? null, text: e.textContent.trim(),
          computed, scale: ctm ? Math.hypot(ctm.a, ctm.b) : 0,
          cssPx: computed * (ctm ? Math.hypot(ctm.a, ctm.b) : 0),
          left: b.left, right: b.right, top: b.top, bottom: b.bottom
        };
      });
    // Test the painted dot, not its intentionally transparent 44px hit target.
    // Ignore the label's own node, but reserve every other on-screen mark.
    const nodes = [...document.querySelectorAll(".g-node")].filter(painted).map((node) => {
      const dot = node.querySelector(".g-dot"), b = dot.getBoundingClientRect();
      return { key: node.dataset.key, left: b.left, right: b.right, top: b.top, bottom: b.bottom };
    }).filter((b) => (b.left + b.right) / 2 >= frame.left && (b.left + b.right) / 2 <= frame.right &&
      (b.top + b.bottom) / 2 >= frame.top && (b.top + b.bottom) / 2 <= frame.bottom);
    const overlaps = [], nodeOverlaps = [];
    for (const label of labels) for (const node of nodes) {
      if (label.key === node.key) continue;
      const width = Math.min(label.right, node.right) - Math.max(label.left, node.left);
      const height = Math.min(label.bottom, node.bottom) - Math.max(label.top, node.top);
      if (width > 0.01 && height > 0.01)
        nodeOverlaps.push({ label: label.text, node: node.key, overlapArea: width * height });
    }
    for (let i = 0; i < labels.length; i++) for (let j = i + 1; j < labels.length; j++) {
      const a = labels[i], b = labels[j];
      if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 0.01 &&
          Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 0.01)
        overlaps.push([a.text, b.text]);
    }
    const clipped = labels.filter((b) => b.left < frame.left - 0.01 || b.right > frame.right + 0.01 ||
      b.top < frame.top - 0.01 || b.bottom > frame.bottom + 0.01);
    const selectedKey = document.getElementById("top").dataset.selectedKey;
    const selectedDot = nodes.find((node) => node.key === selectedKey);
    const selectedLabel = labels.find((label) => label.key === selectedKey);
    const leader = document.getElementById("selected-label-leader");
    let selectedAnchor = null;
    if (selectedDot && selectedLabel && leader && getComputedStyle(leader).display !== "none" &&
        getComputedStyle(leader).visibility !== "hidden" && leader.getTotalLength() > 0) {
      const ctm = leader.getScreenCTM();
      const start = leader.getPointAtLength(0).matrixTransform(ctm);
      const end = leader.getPointAtLength(leader.getTotalLength()).matrixTransform(ctm);
      const center = { x: (selectedDot.left + selectedDot.right) / 2, y: (selectedDot.top + selectedDot.bottom) / 2 };
      selectedAnchor = {
        radius: (selectedDot.right - selectedDot.left) / 2,
        startDistance: Math.hypot(start.x - center.x, start.y - center.y),
        endToLabel: Math.hypot(Math.max(selectedLabel.left - end.x, 0, end.x - selectedLabel.right),
          Math.max(selectedLabel.top - end.y, 0, end.y - selectedLabel.bottom))
      };
    }
    return { labels, overlaps, nodeOverlaps, paintedNodes: nodes.length, clipped, selectedAnchor, frame: frame.toJSON() };
  });
}

export async function assertReadableLabels(page, { selectedKey } = {}) {
  const measured = await measureLabels(page);
  expect(measured.labels.length, "non-vacuous: graph must paint actual readable labels").toBeGreaterThan(0);
  expect(measured.labels.filter((l) => !l.text)).toEqual([]);
  const tiny = measured.labels.filter((l) => l.cssPx < 16 - 1e-6);
  expect(tiny, "VISIBLE_LABEL_CSS_PX: every painted label >=16 actual CSS px including CTM").toEqual([]);
  expect(measured.clipped, "graph labels clipped by frame").toEqual([]);
  expect(measured.nodeOverlaps, "LABEL_NODE_CLEARANCE: labels must not cover another painted node").toEqual([]);
  expect(measured.overlaps, "painted graph labels overlap").toEqual([]);
  if (selectedKey) {
    expect(measured.labels.some((l) => l.key === selectedKey),
      "selected node label has priority and must be painted").toBe(true);
    if (await page.locator("#top").getAttribute("data-selected-offscreen") !== "true") {
      expect(measured.selectedAnchor, "selected label must connect to its actual visible dot").not.toBeNull();
      expect(Math.abs(measured.selectedAnchor.startDistance - measured.selectedAnchor.radius),
        "selected leader begins at its own node's rim").toBeLessThanOrEqual(1);
      expect(measured.selectedAnchor.endToLabel, "selected leader reaches the full label").toBeLessThanOrEqual(6);
    }
  }
  return measured;
}

export async function assertLayout(page) {
  await settleMotion(page);
  const initialRegions = await page.evaluate(() => Object.fromEntries(
    ["workspace-header", "workspace-title", "graph-region", "inspector", "statusbar"]
      .map((id) => [id, document.getElementById(id).getBoundingClientRect().toJSON()])));
  const disclosureWasClosed = !(await page.locator("#gcommunity").isVisible());
  if (disclosureWasClosed) {
    // Coordinator approved a native mobile disclosure, not phantom geometry of
    // its hidden children. Its control is first-viewport and opening is real input.
    await expect(page.locator("#gfilters > summary")).toBeInViewport();
    await ensureFiltersOpen(page);
  }
  for (const id of ["gsearch", "gcommunity", "gcategory", "gsolution", "gstated", "greset", "goverview"]) {
    await expect(page.locator(`#${id}`), `${id} must actually be visible, not a phantom box in closed details`).toBeVisible();
  }
  const measured = await page.evaluate(() => {
    const ids = ["workspace-header", "workspace-title", "graph-region", "inspector", "statusbar"];
    const regions = Object.fromEntries(ids.map((id) => [id, document.getElementById(id).getBoundingClientRect().toJSON()]));
    const controls = ["gsearch", "gcommunity", "gcategory", "gsolution", "gstated", "greset", "goverview"]
      .map((id) => ({ id, ...document.getElementById(id).getBoundingClientRect().toJSON() }));
    return { regions, controls, width: innerWidth, height: innerHeight,
      scrollWidth: document.documentElement.scrollWidth };
  });
  measured.regions = initialRegions;
  measured.filtersDisclosureWasOpened = disclosureWasClosed;
  if (disclosureWasClosed) await page.locator("#gfilters > summary").click();
  expect(measured.scrollWidth).toBeLessThanOrEqual(measured.width + 1);
  for (const control of measured.controls) {
    expect(control.width, `${control.id} real control width`).toBeGreaterThan(0);
    expect(control.height, `${control.id} touch target height`).toBeGreaterThanOrEqual(44);
    expect(control.x, `${control.id} left`).toBeGreaterThanOrEqual(-1);
    expect(control.right, `${control.id} right`).toBeLessThanOrEqual(measured.width + 1);
    expect(control.y, `${control.id} in first viewport`).toBeGreaterThanOrEqual(-1);
    expect(control.bottom, `${control.id} in first viewport`).toBeLessThanOrEqual(measured.height + 1);
  }
  const regions = Object.entries(measured.regions);
  for (const [id, region] of regions) {
    expect(region.width, `${id} is not empty`).toBeGreaterThan(0);
    expect(region.height, `${id} is not empty`).toBeGreaterThan(0);
  }
  for (let i = 0; i < regions.length; i++) for (let j = i + 1; j < regions.length; j++) {
    const [ai, a] = regions[i], [bi, b] = regions[j];
    // Title is intentionally nested in the workspace header.
    if ([ai, bi].includes("workspace-title") && [ai, bi].includes("workspace-header")) continue;
    const area = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) *
      Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
    expect(area, `${ai} overlaps ${bi}`).toBeLessThanOrEqual(1);
  }
  return measured;
}

export async function sweepUnrelatedNodes(page, selectedKey = "") {
  // This proves a SETTLED pointer crossing. Dot positions are only stable once
  // motion is idle, so sample after settling and re-sample under a bounded retry
  // rather than trusting one reading of a moving scene. Nothing about what this
  // asserts changes: the crossing still uses real coordinates of real dots.
  await settleMotion(page);
  const graph = await page.locator("#gsvg").boundingBox();
  const sample = () => page.locator(".g-node").evaluateAll((nodes, key) => nodes.flatMap((n) => {
    const b = n.getBoundingClientRect(), s = getComputedStyle(n);
    if (n.dataset.key === key || n.dataset.visible !== "true" || !b.width || !b.height ||
      s.display === "none" || s.visibility === "hidden") return [];
    return [{ x: b.x + b.width / 2, y: b.y + b.height / 2, key: n.dataset.key }];
  }), selectedKey);
  const inside = (points) => points.filter((p) => p.x > graph.x && p.x < graph.x + graph.width &&
    p.y > graph.y && p.y < graph.y + graph.height).slice(0, 8);
  let reachable = inside(await sample());
  for (const deadline = Date.now() + 3000; !reachable.length && Date.now() < deadline;) {
    await settleMotion(page);
    await page.waitForTimeout(100);
    reachable = inside(await sample());
  }
  expect(reachable.length, "search hover proof must cross actual unrelated visible nodes").toBeGreaterThan(0);
  await page.waitForTimeout(1100);
  for (const p of reachable) {
    await page.mouse.move(p.x, p.y, { steps: 7 });
    await page.waitForTimeout(100);
  }
  await page.mouse.move(graph.x + graph.width * 0.82, graph.y + graph.height * 0.65, { steps: 15 });
  await page.waitForTimeout(1100);
  return reachable;
}

export async function saveEvidence(page, testInfo, name, data) {
  const dir = process.env.WORKSPACE_EVIDENCE_DIR;
  if (!dir) return;
  mkdirSync(dir, { recursive: true });
  const stem = `${testInfo.project.name}-${name}`.replace(/[^a-zA-Z0-9_.-]/g, "-");
  const json = join(dir, `${stem}.json`);
  writeFileSync(json, JSON.stringify({ test: testInfo.title, project: testInfo.project.name,
    viewport: page.viewportSize(), ...data }, null, 2) + "\n");
  const image = join(dir, `${stem}.png`);
  await page.screenshot({ path: image, fullPage: false });
  await testInfo.attach(stem, { path: json, contentType: "application/json" });
  await testInfo.attach(`${stem}-screenshot`, { path: image, contentType: "image/png" });
}
