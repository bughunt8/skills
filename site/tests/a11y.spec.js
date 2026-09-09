import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/*
 * A page that is mostly motion is easy to make unusable by keyboard or screen
 * reader. These are gates, not advice: a violation fails the build.
 */

test.describe("accessibility", () => {
  test("no axe violations at WCAG 2.1 AA", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(2000);

    const { violations } = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      // Nothing is excluded. The previous version of this test excluded the entire
      // .g-labels layer, and an independent review was right that this hid a real
      // failure: eleven community labels were dimmed to 1.99:1 while the README claimed
      // an unqualified AA gate. Those labels name the detected communities, which is
      // information, so they were fixed rather than exempted. (.g-tail was also excluded
      // and no longer exists anywhere in the page.)
      .analyze();

    const summary = violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.length,
      help: v.help
    }));
    expect(summary, JSON.stringify(summary, null, 2)).toEqual([]);
  });

  test("reduced-motion variant is also clean", async ({ browser }) => {
    const ctx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      reducedMotion: "reduce"
    });
    const page = await ctx.newPage();
    await page.goto("/index.html");
    await page.waitForTimeout(1400);

    const { violations } = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    expect(
      violations.map((v) => v.id),
      JSON.stringify(violations.map((v) => ({ id: v.id, help: v.help })), null, 2)
    ).toEqual([]);
    await ctx.close();
  });

  test("the skip link works and every category is keyboard reachable", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(1800);

    // First tab stop must be the skip link, and it must go somewhere real.
    await page.keyboard.press("Tab");
    const first = await page.evaluate(() => ({
      cls: document.activeElement.className,
      href: document.activeElement.getAttribute("href")
    }));
    expect(first.cls).toContain("skip");
    await expect(page.locator(first.href)).toHaveCount(1);

    // Every node is named, and the graph is entered once and then walked.
    //
    // This used to require tabIndex === 0 on all 490, which is what the page did and what
    // made it unusable by keyboard: reaching the section below the graph meant several
    // hundred Tab presses. A roving tabindex replaced it, so the requirement is now that
    // there is exactly one way in, that every node still carries its own name for a screen
    // reader, and that the arrow keys move between them.
    const named = await page.locator(".g-node").evaluateAll((gs) =>
      gs.every((g) => g.getAttribute("aria-label"))
    );
    expect(named, "every node carries its own name").toBe(true);

    const stops = await page.locator('.g-node[tabindex="0"]').count();
    expect(stops, "exactly one tab stop for the whole graph").toBe(1);

    await page.locator('.g-node[tabindex="0"]').focus();
    const before = await page.evaluate(() =>
      document.activeElement.getAttribute("data-key")
    );
    await page.keyboard.press("ArrowRight");
    await page.waitForTimeout(250);
    const after = await page.evaluate(() =>
      document.activeElement.getAttribute("data-key")
    );
    expect(after, "arrow keys move between nodes").not.toBe(before);
    expect(after).toBeTruthy();
    expect(
      await page.locator('.g-node[tabindex="0"]').count(),
      "still one way in after moving"
    ).toBe(1);

    // Rail links are real anchors, so they are reachable and focusable.
    const focusable = await page.locator("#rail a").evaluateAll((as) =>
      as.every((a) => a.tabIndex >= 0 && a.getAttribute("href"))
    );
    expect(focusable).toBe(true);
  });

  test("document structure is landmarked and headed correctly", async ({ page }) => {
    await page.goto("/index.html");

    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.locator("main")).toHaveCount(1);
    await expect(page.locator("nav[aria-label]")).toHaveCount(1);
    expect(await page.getAttribute("html", "lang")).toBe("en");

    // Each category is a disclosure with a real summary, so a screen reader can
    // find and open them without needing the graph.
    const named = await page.locator(".lib__cat").evaluateAll((els) =>
      els.every((e) => {
        const s = e.querySelector("summary");
        return s && s.textContent.trim().length > 0;
      })
    );
    expect(named).toBe(true);

    // The graph carries a text alternative rather than being an unlabelled
    // decoration, since it is the page's opening image.
    const label = await page.getAttribute("#gsvg", "aria-label");
    expect(label && label.length).toBeGreaterThan(20);
  });

  test("focusing a rail target does not leave the reader stranded", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(2000);

    // The rail is hidden below 860px, where it would eat a phone screen, so
    // there is nothing to click. Skip rather than time out for 30 seconds.
    test.skip(
      !(await page.locator("#rail").isVisible()),
      "no category rail at this width"
    );

    const href = await page.locator("#rail a").nth(3).getAttribute("href");
    await page.locator(`#rail a[href="${href}"]`).click();
    await page.waitForTimeout(1500);

    // The category must be open and its heading on screen after navigating to it,
    // not collapsed out of sight.
    await expect(page.locator(href)).toHaveAttribute("open", "");
    const visible = await page.locator(`${href} .lib__catname`).isVisible();
    expect(visible).toBe(true);
  });
});
