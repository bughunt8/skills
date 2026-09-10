import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { openWorkspace, readState, activate, assertNoRuntimeErrors } from "../scripts/workspace-test-helpers.mjs";
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

  test("graph has one roving entry, never 490 Tab stops or focus-driven selection", async ({ page }) => {
    await openWorkspace(page);
    const named = await page.locator(".g-node").evaluateAll((nodes) => ({
      count: nodes.length, unnamed: nodes.filter((n) => !n.getAttribute("aria-label")?.trim()).length,
      tabStops: nodes.filter((n) => n.tabIndex >= 0).length
    }));
    expect(named.count).toBe(490);
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

  test("document landmarks and text alternatives retain names", async ({ page }) => {
    await openWorkspace(page);
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.locator("main")).toHaveCount(1);
    expect(await page.locator("nav[aria-label]").count()).toBeGreaterThan(0);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    expect((await page.locator("#gsvg").getAttribute("aria-label")).length).toBeGreaterThan(20);
    const categories = await page.locator(".lib__cat").evaluateAll((els) =>
      els.map((e) => e.querySelector("summary")?.textContent.trim()));
    expect(categories).toHaveLength(24);
    expect(categories.every(Boolean)).toBe(true);
  });
});
