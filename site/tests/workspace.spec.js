import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import {
  openWorkspace, readState, activate, measureLabels, assertReadableLabels,
  assertLayout, sweepUnrelatedNodes, saveEvidence, assertNoRuntimeErrors, ensureFiltersOpen, paintedGraphCount
} from "../scripts/workspace-test-helpers.mjs";

const data = JSON.parse(readFileSync(new URL("../data.js", import.meta.url), "utf8")
  .replace(/^window\.SKILLDATA=/, "").replace(/;\s*$/, ""));
// Isolated defect routes are always removed, including after a failed assertion.
// The normal test context teardown is a second restoration boundary.
test.afterEach(async ({ page }) => {
  try { await assertNoRuntimeErrors(page); }
  finally { await page.unrouteAll({ behavior: "wait" }); }
});
function resultFor(page, key) {
  return page.locator(`#gresults button[data-key="${key.replace(/["\\]/g, "\\$&")}"]`);
}
async function catalog(page) {
  return page.evaluate(() => [...document.querySelectorAll(".g-node")].map((n) => {
    const card = document.getElementById(n.getAttribute("href").slice(1));
    return { key: n.dataset.key, name: n.dataset.name, category: n.dataset.dom,
      community: n.dataset.comm, description: card.querySelector("p").textContent.trim(),
      solutions: (n.dataset.sol || "").split(" ").filter(Boolean) };
  }));
}
async function resultKeys(page) {
  return page.locator("#gresults button[data-key]").evaluateAll((items) => items.map((i) => i.dataset.key));
}
async function expectSelected(page, key, name) {
  await expect(page.locator("#top")).toHaveAttribute("data-selected-key", key);
  await expect(page.locator("#top")).toHaveAttribute("data-mode", "node");
  await expect(page.locator("#workspace-title")).toHaveText(name);
  await expect(page.locator("#panelname")).toHaveText(name);
  await expect(resultFor(page, key)).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#status-selected")).toContainText(name);
}
async function typeQuery(page, text) {
  await page.locator("#gsearch").click();
  await page.locator("#gsearch").fill("");
  await page.locator("#gsearch").pressSequentially(text, { delay: 65 });
  await expect(page.locator("#top")).toHaveAttribute("data-query", text);
  await page.waitForTimeout(1100);
}

test.describe("workspace acceptance", () => {
  test.beforeEach(async ({ page }) => { await openWorkspace(page); });

  test("first viewport opens a populated expanded cluster with docked regions", async ({ page }, testInfo) => {
    const state = await readState(page);
    expect(state.context.mode).toBe("community");
    expect(state.context.selected).toBe("");
    await expect(page.locator("#workspace-title")).toHaveText(data.comms[0].label);
    expect(state.matching).toBe(data.comms[0].size);
    expect(state.visible).toBeGreaterThan(0);
    expect(state.visible).toBe(await paintedGraphCount(page));
    expect((await resultKeys(page)).length).toBe(data.comms[0].size);
    const layout = await assertLayout(page);
    const graph = await page.locator("#gsvg").boundingBox();
    expect(graph.width).toBeGreaterThan(layout.regions["graph-region"].width * 0.85);
    expect(graph.height).toBeGreaterThan(180);
    if (page.viewportSize().width >= 1024) {
      expect(graph.width).toBeGreaterThan(page.viewportSize().width * 0.55);
      expect(graph.height).toBeGreaterThan(page.viewportSize().height * 0.50);
      expect(layout.regions["statusbar"].bottom).toBeLessThanOrEqual(page.viewportSize().height + 1);
    }
    const initialScale = state.camera.scale;
    await activate(page.locator("#goverview"), testInfo);
    await expect(page.locator("#top")).toHaveAttribute("data-mode", "overview");
    const overview = await readState(page);
    expect(initialScale, "default should magnify a populated cluster, not show a tiny overview").toBeGreaterThan(overview.camera.scale);
    await activate(page.locator("#greset"), testInfo);
    await saveEvidence(page, testInfo, "first-viewport", { state, overview, layout,
      labels: await measureLabels(page) });
  });

  test("VISIBLE_LABEL_CSS_PX every painted label is >=16px without clipping or collisions", async ({ page }, testInfo) => {
    test.setTimeout(60_000);
    const states = [];
    states.push({ phase: "default", measured: await assertReadableLabels(page) });
    await activate(page.locator("#goverview"), testInfo);
    states.push({ phase: "overview", measured: await assertReadableLabels(page) });
    await ensureFiltersOpen(page);
    await page.locator("#gcommunity").selectOption(String(data.comms[1].id));
    states.push({ phase: "community", measured: await assertReadableLabels(page) });
    await activate(page.locator("#greset"), testInfo);
    await typeQuery(page, "NDA");
    const key = (await resultKeys(page))[0];
    expect(key).toBeTruthy();
    await activate(resultFor(page, key), testInfo);
    states.push({ phase: "selected", measured: await assertReadableLabels(page, { selectedKey: key }) });
    for (let i = 0; i < 30 && await page.locator("#gzoom-in").isEnabled(); i++) {
      await activate(page.locator("#gzoom-in"), testInfo);
    }
    await expect(page.locator("#gzoom-in")).toBeDisabled();
    states.push({ phase: "zoom-in", measured: await assertReadableLabels(page, { selectedKey: key }) });
    for (let i = 0; i < 30 && await page.locator("#gzoom-out").isEnabled(); i++) {
      await activate(page.locator("#gzoom-out"), testInfo);
    }
    await expect(page.locator("#gzoom-out")).toBeDisabled();
    states.push({ phase: "zoom-out", measured: await assertReadableLabels(page) });
    await activate(page.locator("#gfit"), testInfo);
    states.push({ phase: "fit", measured: await assertReadableLabels(page, { selectedKey: key }) });
    const name = (await catalog(page)).find((n) => n.key === key).name;
    await expect(page.locator("#panelname")).toHaveText(name);
    await expect(resultFor(page, key)).toContainText(name);
    await saveEvidence(page, testInfo, "readability", { states });
  });

  test("SEARCH_HOVER_IMMUNITY NDA results survive settled pointer crossing and explicit selection", async ({ page }, testInfo) => {
    const nodes = await catalog(page);
    await typeQuery(page, "NDA");
    // NDA is a short token, not an accidental substring of "standards"; the
    // contract also recognizes the spelled-out non-disclosure description.
    const expected = nodes.filter((n) => /(?:^|[^\p{L}\p{N}])nda[\p{L}\p{N}]*|non[\s-]?disclosure/iu.test(`${n.name} ${n.description}`))
      .map((n) => n.key).sort();
    expect(expected.length, "NDA must actually match descriptions").toBeGreaterThan(0);
    expect(nodes.filter((n) => expected.includes(n.key) && !n.name.toLowerCase().includes("nda")).length)
      .toBeGreaterThan(0);
    expect((await resultKeys(page)).sort()).toEqual(expected);
    const before = await readState(page);
    expect(before.context.mode).toBe("search");
    expect(before.context.selected).toBe("");
    const crossed = await sweepUnrelatedNodes(page);
    expect((await readState(page)).context, "SEARCH_HOVER_IMMUNITY: pointer entry must not replace search").toEqual(before.context);
    await expect(page.locator("#gsearch")).toHaveValue("NDA");
    await expect(page.locator("#gsearch")).toBeFocused();
    // Move across the canvas on the way to a particular existing result.
    const key = expected.find((key) => {
      const index = data.nodes.indexOf(key);
      return data.edges.some(([a, b]) => a === index || b === index);
    });
    expect(key, "choose a real NDA result with a neighborhood").toBeTruthy();
    const target = resultFor(page, key);
    await target.scrollIntoViewIfNeeded();
    const box = await target.boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 20 });
    expect((await readState(page)).context).toEqual(before.context);
    await activate(target, testInfo);
    const node = nodes.find((n) => n.key === key);
    await expectSelected(page, key, node.name);
    const selected = await readState(page);
    expect(selected.context.results.slice().sort()).toEqual(expected);
    expect(selected.context.query).toBe("NDA");
    expect(selected.camera).not.toEqual(before.camera);
    expect(selected.camera.scale, "node neighborhood must expand from broad NDA results").toBeGreaterThan(before.camera.scale);
    const selectedCrossed = await sweepUnrelatedNodes(page, key);
    const frame = await page.locator("#gsvg").boundingBox();
    await page.mouse.move(frame.x + frame.width * 0.5, frame.y + frame.height * 0.5, { steps: 12 });
    await page.mouse.wheel(0, 480);
    await page.waitForTimeout(1200);
    expect((await readState(page)).context, "SEARCH_HOVER_IMMUNITY: selection persists after hover/wheel/idle").toEqual(selected.context);
    await expectSelected(page, key, node.name);
    await saveEvidence(page, testInfo, "search-nda", { before, selected, final: await readState(page), crossed, selectedCrossed });
  });

  test("search supports editing, multi-results, empty query, no results and Escape reset", async ({ page }, testInfo) => {
    const nodes = await catalog(page);
    const origin = await readState(page);
    await typeQuery(page, "NDA");
    const firstKey = (await resultKeys(page))[0];
    await activate(resultFor(page, firstKey), testInfo);
    await typeQuery(page, "finance");
    const expected = nodes.filter((n) => `${n.name} ${n.description}`.toLowerCase().includes("finance")).map((n) => n.key).sort();
    expect(expected.length).toBeGreaterThan(1);
    expect((await resultKeys(page)).sort()).toEqual(expected);
    await expect(page.locator("#top")).toHaveAttribute("data-selected-key", "");
    const targets = await page.locator("#gresults button[data-key]").evaluateAll((buttons) =>
      buttons.map((b) => ({ key: b.dataset.key, height: b.getBoundingClientRect().height })));
    expect(targets.length).toBe(expected.length);
    expect(targets.filter((t) => t.height < 44)).toEqual([]);
    await page.locator("#gsearch").fill("");
    await expect(page.locator("#gsearch")).toHaveValue("");
    await expect(page.locator("#top")).toHaveAttribute("data-query", "");
    expect((await resultKeys(page)).length).toBeGreaterThan(0);
    expect((await readState(page)).context, "empty input restores its pre-search context").toEqual(origin.context);
    await typeQuery(page, "zzzz-no-skill-98765");
    await expect(page.locator("#gresults button[data-key]")).toHaveCount(0);
    const none = await readState(page);
    expect(none.matching).toBe(0);
    await expect(page.locator("#inspector")).toContainText(/no (?:skills|results|matches|matching skills)/i);
    await expect(page.locator("#status-counts")).toContainText("0");
    await page.keyboard.press("Escape");
    const reset = await readState(page);
    expect(reset.context.mode).toBe("community");
    expect(reset.context.query).toBe("");
    expect(reset.context.selected).toBe("");
    await expect(page.locator("#workspace-title")).toHaveText(data.comms[0].label);
  });

  test("search result list uses real keyboard activation and stable identity", async ({ page }) => {
    await typeQuery(page, "NDA");
    const keys = await resultKeys(page);
    const before = await readState(page);
    // Navigate, never programmatically focus or synthesize selection. Bounded to
    // avoid passing a 490-tab traversal disguised as accessibility.
    let focused = "";
    for (let i = 0; i < 35; i++) {
      await page.keyboard.press("Tab");
      focused = await page.evaluate(() => document.activeElement.closest("#gresults") ?
        document.activeElement.dataset.key || "" : "");
      if (focused) break;
    }
    expect(keys).toContain(focused);
    expect((await readState(page)).context).toEqual(before.context);
    await page.keyboard.press("Enter");
    const node = (await catalog(page)).find((n) => n.key === focused);
    await expectSelected(page, focused, node.name);
  });

  test("Clear restores the search origin rather than silently opening all 490 skills", async ({ page }, testInfo) => {
    const origins = [];
    async function roundtrip(phase) {
      const before = await readState(page);
      await typeQuery(page, "NDA");
      const results = await resultKeys(page);
      if (results.length) await activate(resultFor(page, results[0]), testInfo);
      await activate(page.locator("#gclear"), testInfo);
      const after = await readState(page);
      expect(after.context, `Clear must restore ${phase} context`).toEqual(before.context);
      expect(after.matching).toBe(before.matching);
      origins.push({ phase, before, after });
    }
    await roundtrip("default community");
    await ensureFiltersOpen(page);
    await page.locator("#gcategory").selectOption("finance");
    await roundtrip("category filter");
    await activate(page.locator("#goverview"), testInfo);
    await roundtrip("explicit overview");
    await saveEvidence(page, testInfo, "clear-origins", { origins });
  });

  test("LABEL_NODE_CLEARANCE contextual labels avoid other painted nodes", async ({ page }, testInfo) => {
    const opening = await assertReadableLabels(page);
    expect(opening.paintedNodes).toBe(data.comms[0].size);
    expect(opening.labels.length, "a populated opening needs multiple actual labels").toBeGreaterThan(1);
    const key = await page.locator('#gresults button[data-key]').first().getAttribute("data-key");
    await activate(resultFor(page, key), testInfo);
    const selected = await assertReadableLabels(page, { selectedKey: key });
    expect(selected.labels.find((label) => label.key === key).text).toBe(
      (await catalog(page)).find((node) => node.key === key).name);
    await saveEvidence(page, testInfo, "label-node-clearance", { opening, selected });
  });

  test("combined community category and Solution filters report the actual intersection", async ({ page }, testInfo) => {
    const nodes = await catalog(page);
    const candidate = nodes.find((n) => n.solutions.length && nodes.filter((m) =>
      m.community === n.community && m.category === n.category && m.solutions.includes(n.solutions[0])).length > 1);
    expect(candidate).toBeTruthy();
    await ensureFiltersOpen(page);
    await page.locator("#gcategory").selectOption(candidate.category);
    await expect(page.locator("#top")).toHaveAttribute("data-category", candidate.category);
    const categoryText = await page.locator("#gcategory option:checked").textContent();
    await expect(page.locator("#workspace-title")).toContainText(categoryText.replace(/\s*\(\d+\)\s*$/, ""));
    await page.locator("#gcommunity").selectOption(candidate.community);
    await page.locator("#gsolution").selectOption(candidate.solutions[0]);
    const solutionTitle = await page.locator(`.sol[data-sol="${candidate.solutions[0]}"] h3`).textContent();
    await expect(page.locator("#workspace-title")).toHaveText(solutionTitle);
    const expected = nodes.filter((n) => n.category === candidate.category &&
      n.community === candidate.community && (n.solutions.includes(candidate.solutions[0]) ||
        n.key === candidate.solutions[0])).map((n) => n.key).sort();
    expect((await resultKeys(page)).sort()).toEqual(expected);
    const state = await readState(page);
    expect(state.context.category).toBe(candidate.category);
    expect(state.context.community).toBe(candidate.community);
    expect(state.context.solution).toBe(candidate.solutions[0]);
    expect(state.matching).toBe(expected.length);
    await expect(page.locator("#status-counts")).toContainText(String(expected.length));
    const shown = await paintedGraphCount(page);
    expect(state.visible).toBe(shown);
    await activate(page.locator("#gstated"), testInfo);
    await expect(page.locator("#gstated")).toHaveAttribute("aria-pressed", "true");
    const evidence = await readState(page);
    expect(evidence.context.evidence).not.toBe(state.context.evidence);
    expect(evidence.context.category).toBe(candidate.category);
    expect((await resultKeys(page)).sort()).toEqual(expected);
    const visibleInferred = await page.locator(".g-edge--inferred").evaluateAll((edges) =>
      edges.filter((e) => {
        const s = getComputedStyle(e);
        return s.display !== "none" && s.visibility !== "hidden" && Number(s.opacity) > 0;
      }).length);
    expect(visibleInferred).toBe(0);
    await expect(page.locator("#status-evidence")).toContainText(/stated/i);
    await saveEvidence(page, testInfo, "combined-filters", { expected, state, evidence });
  });

  test("every community including singletons has readable labels and reachable members", async ({ page }, testInfo) => {
    test.setTimeout(90_000);
    const measurements = [];
    await ensureFiltersOpen(page);
    for (const community of data.comms) {
      await page.locator("#gcommunity").selectOption(String(community.id));
      await expect(page.locator("#workspace-title")).toHaveText(community.label);
      await expect(page.locator("#gresults button[data-key]")).toHaveCount(community.size);
      const measured = await assertReadableLabels(page);
      if (page.viewportSize().width >= 1280 && community.size <= 8) {
        expect(measured.labels.filter((label) => label.key).length,
          `small community ${community.id}: ample desktop space must label every member`).toBe(community.size);
      }
      measurements.push({ id: community.id, size: community.size,
        visibleLabels: measured.labels.length, paintedNodes: measured.paintedNodes,
        minCssPx: Math.min(...measured.labels.map((l) => l.cssPx)),
        labelNodeCollisions: measured.nodeOverlaps.length });
    }
    expect(measurements).toHaveLength(data.comms.length);
    await saveEvidence(page, testInfo, "all-communities", { measurements });
  });

  test("real graph activation selects exact identity and inspector preserves source evidence", async ({ page }, testInfo) => {
    const point = await page.locator(".g-node").evaluateAll((nodes) => {
      for (const n of nodes) {
        if (n.dataset.visible !== "true") continue;
        const b = n.getBoundingClientRect(), x = b.x + b.width / 2, y = b.y + b.height / 2;
        if (document.elementFromPoint(x, y)?.closest(".g-node") === n)
          return { key: n.dataset.key, x, y };
      }
      return null;
    });
    expect(point, "there must be an actual hit-testable graph node").toBeTruthy();
    const before = await readState(page);
    await page.mouse.move(point.x, point.y, { steps: 20 });
    await page.waitForTimeout(1100);
    expect((await readState(page)).context).toEqual(before.context);
    if (testInfo.project.use.hasTouch) await page.touchscreen.tap(point.x, point.y);
    else await page.mouse.click(point.x, point.y);
    const node = (await catalog(page)).find((n) => n.key === point.key);
    await expect(page.locator("#top")).toHaveAttribute("data-selected-key", point.key);
    await expect(page.locator("#workspace-title")).toHaveText(node.name);
    await expect(page.locator("#paneldesc")).toHaveText(node.description);
    const provenance = await page.locator(`.card[data-id="${point.key}"]`).evaluate((card) => ({
      source: card.querySelector("footer a").href, licence: card.querySelector(".lic").textContent.trim()
    }));
    await expect(page.locator("#panelsource")).toHaveAttribute("href", provenance.source);
    await expect(page.locator("#panel")).toContainText(provenance.licence);
    const index = data.nodes.indexOf(point.key);
    const edges = data.edges.map((e, i) => ({ e, i })).filter(({ e }) => e[0] === index || e[1] === index);
    await expect(page.locator("#panelchain li")).toHaveCount(edges.length);
    const shown = await page.locator("#panelchain li").allTextContents();
    for (const { e, i } of edges) {
      const other = data.nodes[e[0] === index ? e[1] : e[0]];
      const name = (await catalog(page)).find((n) => n.key === other).name;
      const line = shown.find((text) => text.includes(name) &&
        data.why[i].every((why) => text.includes(why)));
      expect(line, `connection ${point.key} -> ${other} retains supplied evidence`).toBeTruthy();
      expect(line).toContain(e[3] === 0 ? "Stated" : "Inferred");
    }
  });

  test("path A/B is a shortest walk over real edges and a disconnected pair is unreachable", async ({ page }, testInfo) => {
    const nodes = await catalog(page), byKey = new Map(nodes.map((n) => [n.key, n]));
    const adjacency = new Map(data.nodes.map((key) => [key, []]));
    const statedAdjacency = new Map(data.nodes.map((key) => [key, []]));
    data.edges.forEach(([a, b, , kind]) => {
      adjacency.get(data.nodes[a]).push(data.nodes[b]);
      adjacency.get(data.nodes[b]).push(data.nodes[a]);
      if (kind === 0) {
        statedAdjacency.get(data.nodes[a]).push(data.nodes[b]);
        statedAdjacency.get(data.nodes[b]).push(data.nodes[a]);
      }
    });
    function bfs(start, end, graph = adjacency) {
      const queue = [[start]], seen = new Set([start]);
      for (let i = 0; i < queue.length; i++) {
        const path = queue[i], last = path[path.length - 1];
        if (last === end) return path;
        for (const next of graph.get(last)) if (!seen.has(next)) {
          seen.add(next); queue.push([...path, next]);
        }
      }
      return [];
    }
    let pair;
    const start = nodes.find((n) => n.community === String(data.comms[0].id)).key;
    for (const node of nodes) {
      const path = bfs(start, node.key);
      if (path.length >= 3 && path.length <= 6) { pair = { start, end: node.key, length: path.length }; break; }
    }
    expect(pair).toBeTruthy();
    async function choose(key) {
      await page.locator("#gsearch").fill(byKey.get(key).name);
      await expect(resultFor(page, key)).toBeVisible();
      await activate(resultFor(page, key), testInfo);
    }
    await choose(pair.start);
    await activate(page.locator("#gpath"), testInfo);
    await expect(page.locator("#gpath")).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator("#results-hint")).toContainText(byKey.get(pair.start).name);
    await choose(pair.end);
    await expect(page.locator("#top")).toHaveAttribute("data-mode", "path");
    const walk = JSON.parse(await page.locator("#top").getAttribute("data-path"));
    expect(walk[0]).toBe(pair.start);
    expect(walk[walk.length - 1]).toBe(pair.end);
    expect(walk).toHaveLength(pair.length);
    for (let i = 1; i < walk.length; i++) expect(adjacency.get(walk[i - 1])).toContain(walk[i]);
    await expect(page.locator("#panelchain li")).toHaveCount(walk.length);
    const details = await page.locator("#panelchain li p").allTextContents();
    expect(details).toHaveLength(walk.length - 1);
    expect(details.every((t) => /^(Stated|Inferred): .+/.test(t))).toBe(true);
    await expect(page.locator("#paneldesc")).toContainText(String(walk.length - 1));
    await ensureFiltersOpen(page);
    await activate(page.locator("#gstated"), testInfo);
    const statedWalk = JSON.parse(await page.locator("#top").getAttribute("data-path"));
    expect(statedWalk).toHaveLength(bfs(pair.start, pair.end, statedAdjacency).length);
    for (let i = 1; i < statedWalk.length; i++) expect(statedAdjacency.get(statedWalk[i - 1])).toContain(statedWalk[i]);
    if (!statedWalk.length) await expect(page.locator("#paneldesc")).toContainText(/no path exists/i);
    expect((await page.locator("#panelchain li p").allTextContents()).every((t) => t.startsWith("Stated:"))).toBe(true);
    const isolated = data.nodes.filter((key) => adjacency.get(key).length === 0);
    expect(isolated.length).toBeGreaterThan(1);
    await activate(page.locator("#greset"), testInfo);
    await choose(isolated[0]);
    await activate(page.locator("#gpath"), testInfo);
    await choose(isolated[1]);
    expect(JSON.parse(await page.locator("#top").getAttribute("data-path"))).toEqual([]);
    await expect(page.locator("#paneldesc")).toContainText(/no path exists/i);
    await expect(page.locator("#panelchain li")).toHaveCount(0);
    await expect(page.locator("#workspace-title")).toContainText(byKey.get(isolated[0]).name);
    await expect(page.locator("#workspace-title")).toContainText(byKey.get(isolated[1]).name);
    await saveEvidence(page, testInfo, "paths", { pair, walk, statedWalk, unreachable: isolated.slice(0, 2) });
  });

  test("overview fit zoom pan Back and reset are explicit and retain context", async ({ page }, testInfo) => {
    await typeQuery(page, "NDA");
    const key = (await resultKeys(page))[0];
    await activate(resultFor(page, key), testInfo);
    const selected = await readState(page);
    await activate(page.locator("#gzoom-in"), testInfo);
    const zoomed = await readState(page);
    expect(zoomed.camera.scale).toBeGreaterThan(selected.camera.scale);
    expect(zoomed.context).toEqual(selected.context);
    await activate(page.locator("#gzoom-out"), testInfo);
    expect((await readState(page)).camera.scale).toBeLessThan(zoomed.camera.scale);
    const graph = await page.locator("#gsvg").boundingBox();
    // Start in an empty edge of the canvas, not on a potentially selected node.
    const p = { x: graph.x + 14, y: graph.y + graph.height - 18 };
    const beforePan = await readState(page);
    await page.mouse.move(p.x, p.y);
    await page.mouse.down();
    await page.mouse.move(p.x + 95, p.y - 48, { steps: 12 });
    await page.mouse.up();
    const panned = await readState(page);
    expect(panned.camera).not.toEqual(beforePan.camera);
    expect(panned.context).toEqual(selected.context);
    await activate(page.locator("#gfit"), testInfo);
    expect((await readState(page)).context).toEqual(selected.context);
    await activate(page.locator("#goverview"), testInfo);
    await expect(page.locator("#top")).toHaveAttribute("data-mode", "overview");
    await activate(page.locator("#gback"), testInfo);
    expect((await readState(page)).context).toEqual(selected.context);
    await activate(page.locator("#greset"), testInfo);
    const reset = await readState(page);
    expect(reset.context.mode).toBe("community");
    expect(reset.context.query).toBe("");
    expect(reset.context.selected).toBe("");
    expect(reset.context.category).toBe("");
    expect(reset.context.solution).toBe("");
  });
});

for (const [width, height, label] of [
  [1440, 900, "1440x900"], [1280, 800, "1280x800"], [1024, 768, "1024x768"],
  [390, 844, "390x844"], [720, 450, "200-percent-equivalent"]
]) {
  test(`responsive ${label}: controls reachable and actual labels readable`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height });
    await openWorkspace(page);
    const layout = await assertLayout(page);
    const opening = await assertReadableLabels(page);
    await typeQuery(page, "NDA");
    const key = (await resultKeys(page))[0];
    await activate(resultFor(page, key), testInfo);
    const node = (await catalog(page)).find((n) => n.key === key);
    await expectSelected(page, key, node.name);
    const selected = await assertReadableLabels(page, { selectedKey: key });
    await activate(page.locator("#gfit"), testInfo);
    await activate(page.locator("#gclear"), testInfo);
    await expect(page.locator("#gsearch")).toHaveValue("");
    await activate(page.locator("#greset"), testInfo);
    await saveEvidence(page, testInfo, `responsive-${label}`, { layout, opening, selected });
  });
}
