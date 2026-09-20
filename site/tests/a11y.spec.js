import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { openWorkspace, readState, activate, assertNoRuntimeErrors } from "../scripts/workspace-test-helpers.mjs";
import { EXPECTED_TOTAL, EXPECTED_CATEGORIES } from "./library-size.mjs";
test.afterEach(async ({ page }) => { await assertNoRuntimeErrors(page); });

async function scan(page) {
  // No exclusions, disabled rules or graph-layer exemptions.
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(violations.map((v) => ({
    id: v.id, impact: v.impact, help: v.help,
    nodes: v.nodes.map((n) => ({ target: n.target, summary: n.failureSummary }))
  }))).toEqual([]);
}

test.describe("accessible workspace", () => {
  for (const mode of ["default", "dark", "search", "selected", "reduced-motion"]) {
    test(`axe WCAG 2.1 AA includes every layer in ${mode}`, async ({ page }, testInfo) => {
      if (mode === "reduced-motion") await page.emulateMedia({ reducedMotion: "reduce" });
      if (mode === "dark") await page.emulateMedia({ colorScheme: "dark" });
      await openWorkspace(page);
      if (mode === "search" || mode === "selected") {
        await page.locator("#gsearch").fill("NDA");
        await expect(page.locator("#gresults button[data-key]").first()).toBeVisible();
      }
      if (mode === "selected") await activate(page.locator("#gresults button[data-key]").first(), testInfo);
      await scan(page);
    });
  }

  test("skip link activates a real target and native text disclosures work by keyboard", async ({ page }) => {
    await openWorkspace(page);
    await page.keyboard.press("Tab");
    const first = await page.evaluate(() => ({
      cls: document.activeElement.className,
      href: document.activeElement.getAttribute("href")
    }));
    expect(first.cls).toContain("skip");
    expect(first.href).toMatch(/^#/);
    await expect(page.locator(first.href)).toHaveCount(1);
    await page.keyboard.press("Enter");
    // The top text-library link provides explicit navigation to native fallback.
    await page.locator('a[data-open="library"]').click();
    await expect(page.locator("#library")).toHaveAttribute("open", "");
    await page.locator(".lib__cat > summary").first().click();
    await expect(page.locator(".card").first()).toBeVisible();
    await page.keyboard.press("Space");
    await expect(page.locator(".lib__cat").first()).not.toHaveAttribute("open", "");
  });

  test("graph has one roving entry, never one Tab stop per skill or focus-driven selection", async ({ page }) => {
    await openWorkspace(page);
    const named = await page.locator(".g-node").evaluateAll((nodes) => ({
      count: nodes.length, unnamed: nodes.filter((n) => !n.getAttribute("aria-label")?.trim()).length,
      tabStops: nodes.filter((n) => n.tabIndex >= 0).length
    }));
    expect(named.count).toBe(EXPECTED_TOTAL);
    expect(named.unnamed).toBe(0);
    expect(named.tabStops).toBeLessThanOrEqual(1);
    const graphEntries = await page.locator("#gsvg, .g-node").evaluateAll((els) =>
      els.filter((e) => e.tabIndex === 0).length);
    expect(graphEntries, "one composite graph entry").toBe(1);
    const before = await readState(page);
    let entered = false;
    for (let i = 0; i < 25; i++) {
      await page.keyboard.press("Tab");
      entered = await page.evaluate(() => document.activeElement.id === "gsvg" ||
        document.activeElement.classList.contains("g-node"));
      if (entered) break;
    }
    expect(entered, "graph is reachable without a long Tab traversal").toBe(true);
    const focusedBefore = await page.evaluate(() => document.activeElement.getAttribute("data-key"));
    await page.keyboard.press("ArrowRight");
    const focusedAfter = await page.evaluate(() => document.activeElement.getAttribute("data-key"));
    const after = await readState(page);
    expect(after.context, "keyboard focus/pan alone must not select").toEqual(before.context);
    if (named.tabStops === 1) expect(focusedAfter).not.toBe(focusedBefore);
    else expect(after.camera, "composite graph arrows pan").not.toEqual(before.camera);
  });

  test("lead links rove as one composite: spatial arrows, Home/End jumps, one Tab entry, focus never selects", async ({ page }) => {
    await openWorkspace(page);
    // The runtime enhancement: exactly one lead carries the graph's Tab stop and
    // the canvas is not a second entry. The build itself never writes a tabindex.
    const composite = await page.evaluate(() => {
      const leads = [...document.querySelectorAll(".g-node[data-leads]")];
      return {
        count: leads.length,
        tabbable: leads.filter((el) => el.tabIndex === 0).length,
        removed: leads.filter((el) => el.tabIndex === -1).length,
        canvas: document.getElementById("gsvg").tabIndex
      };
    });
    expect(composite.count, "the graph must have Solution lead links to rove over").toBeGreaterThan(0);
    expect(composite.tabbable, "exactly one lead is the graph's Tab stop").toBe(1);
    expect(composite.removed).toBe(composite.count - 1);
    expect(composite.canvas, "the canvas must not add a second graph entry").toBe(-1);

    // From the top of the page: the graph is entered exactly once and the next
    // Tab leaves it again, instead of one stop per lead link.
    let graphStops = 0, leftGraph = false;
    for (let i = 0; i < 40 && !leftGraph; i++) {
      await page.keyboard.press("Tab");
      const at = await page.evaluate(() => {
        const el = document.activeElement;
        return { onLead: !!el.closest(".g-node[data-leads]"), inGraph: !!el.closest("#gsvg") };
      });
      if (at.onLead) graphStops++;
      if (graphStops > 0 && !at.inGraph) leftGraph = true;
    }
    expect(graphStops, "Tab enters the graph once").toBe(1);
    expect(leftGraph, "Tab leaves the graph to the next control").toBe(true);

    const focusLead = () => page.evaluate(() => {
      const el = document.activeElement.closest(".g-node[data-leads]");
      return el ? {
        key: el.dataset.key,
        x: Number(el.dataset.renderX ?? el.dataset.x), y: Number(el.dataset.renderY ?? el.dataset.y)
      } : null;
    });
    await page.keyboard.press("Shift+Tab");
    expect(await focusLead(), "Shift+Tab returns to the roving lead").not.toBeNull();

    // Each arrow lands strictly further along its own axis: the order comes from
    // the positions the scene paints, not from document order. The two reversals
    // are guaranteed by the move that preceded them.
    const before = await readState(page);
    for (const [key, axis, sign] of [["ArrowRight", "x", 1], ["ArrowLeft", "x", -1],
      ["ArrowDown", "y", 1], ["ArrowUp", "y", -1]]) {
      const from = await focusLead();
      await page.keyboard.press(key);
      const to = await focusLead();
      expect(to, `${key} keeps focus on a lead`).not.toBeNull();
      expect(sign * (to[axis] - from[axis]), `${key} moves to a lead further ${key.slice(5).toLowerCase()}`)
        .toBeGreaterThan(0);
    }
    const after = await readState(page);
    expect(after.context, "moving focus through the composite must not select").toEqual(before.context);

    // Home and End jump to the reading-order ends of the leads in the scene.
    const ends = await page.evaluate(() => {
      const visible = [...document.querySelectorAll(".g-node[data-leads]")]
        .filter((el) => el.dataset.inContext !== "false")
        .map((el) => ({ key: el.dataset.key,
          x: Number(el.dataset.renderX ?? el.dataset.x), y: Number(el.dataset.renderY ?? el.dataset.y) }))
        .sort((a, b) => a.y - b.y || a.x - b.x || a.key.localeCompare(b.key));
      return { first: visible[0].key, last: visible[visible.length - 1].key };
    });
    expect(ends.first).not.toBe(ends.last);
    await page.keyboard.press("Home");
    expect(await focusLead(), "Home jumps to the first lead in reading order").toMatchObject({ key: ends.first });
    await page.keyboard.press("End");
    expect(await focusLead(), "End jumps to the last lead in reading order").toMatchObject({ key: ends.last });
  });

  test("Enter and Space on a focused lead are explicit activations", async ({ page }) => {
    await openWorkspace(page);
    let onLead = false;
    for (let i = 0; i < 25 && !onLead; i++) {
      await page.keyboard.press("Tab");
      onLead = await page.evaluate(() =>
        !!document.activeElement.closest(".g-node[data-leads]"));
    }
    expect(onLead, "the roving lead must be reachable by Tab").toBe(true);
    const enterKey = await page.evaluate(() => document.activeElement.dataset.key);
    await page.keyboard.press("Enter");
    await expect(page.locator("#top")).toHaveAttribute("data-selected-key", enterKey);
    await expect(page.locator("#top")).toHaveAttribute("data-mode", "node");

    // Escape is the documented Reset shortcut: back to the overview, where every
    // lead is in context again and the rest of the walk stays deterministic.
    await page.keyboard.press("Escape");
    await expect(page.locator("#top")).toHaveAttribute("data-selected-key", "");
    await page.keyboard.press("End");
    const spaceKey = await page.evaluate(() =>
      document.activeElement.closest(".g-node[data-leads]")?.dataset.key ?? "");
    expect(spaceKey, "End puts focus on a lead").toBeTruthy();
    expect(spaceKey).not.toBe(enterKey);
    await page.keyboard.press("Space");
    await expect(page.locator("#top")).toHaveAttribute("data-selected-key", spaceKey);
  });

  test("without scripting every lead stays an ordinary tabbable link", async ({ browser }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const page = await ctx.newPage();
    await page.goto("/index.html");
    // With scripting off the DOM is exactly the generated markup. The no-JS
    // interface is the text library, so the proof is structural: every lead is
    // a plain anchor with a resolvable target, and nothing in the build demotes
    // any node out of the tab order — that demotion lives only in app.js.
    const leads = await page.evaluate(() => {
      const nodes = [...document.querySelectorAll(".g-node")];
      const read = (el) => ({
        tag: el.tagName.toLowerCase(),
        href: el.getAttribute("href"),
        tabindex: el.getAttribute("tabindex"),
        target: !!document.getElementById(el.getAttribute("href").slice(1))
      });
      return { all: nodes.map(read), leadCount: nodes.filter((el) => el.hasAttribute("data-leads")).length };
    });
    expect(leads.leadCount, "the graph has Solution lead links").toBeGreaterThan(0);
    expect(leads.all.every((l) => l.tag === "a"), "every node is an anchor").toBe(true);
    expect(leads.all.every((l) => (l.href || "").startsWith("#skill-")), "every node links into the library").toBe(true);
    expect(leads.all.filter((l) => l.tabindex === null),
      "no lead or node is demoted in the generated markup").toHaveLength(leads.all.length);
    expect(leads.all.every((l) => l.target), "every lead link's target exists").toBe(true);
    await ctx.close();
  });

  test("document landmarks and text alternatives retain names", async ({ page }) => {
    await openWorkspace(page);
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.locator("main")).toHaveCount(1);
    expect(await page.locator("nav[aria-label]").count()).toBeGreaterThan(0);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    expect((await page.locator("#gsvg").getAttribute("aria-label")).length).toBeGreaterThan(20);
    const categories = await page.locator(".lib__cat").evaluateAll((els) =>
      els.map((e) => e.querySelector("summary")?.textContent.trim()));
    expect(categories).toHaveLength(EXPECTED_CATEGORIES);
    expect(categories.every(Boolean)).toBe(true);
  });
});
