import { test, expect } from "@playwright/test";

/*
 * What is left of the motion layer after the page stopped being a 76,000-pixel
 * pinned filmstrip.
 *
 * The choreography tests that used to live here are gone with the thing they
 * tested: there are no per-category chapters, no horizontal strip to scrub, and no
 * counter animating up from zero. The traversal that replaced all of it is tested
 * in graph.spec.js, because it is graph behaviour rather than decoration.
 *
 * Two rules survive from that work and are still worth pinning:
 *   1. The page must not log an error while being scrolled from top to bottom.
 *   2. Motion must actually attach, rather than the page silently falling back to
 *      its static form while appearing fine.
 */

test.describe("motion layer", () => {
  test.skip(({ isMobile }) => isMobile, "desktop pinning only");

  test("loads and scrolls with no console or page errors", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(m.text());
    });

    await page.goto("/index.html");
    await page.waitForTimeout(2000);

    // All the way down, in steps, so a fault in any section is attributed rather
    // than missed by jumping straight to the bottom.
    const height = await page.evaluate(() => document.body.scrollHeight);
    for (let y = 0; y <= height; y += Math.round(height / 8)) {
      await page.evaluate((to) => window.scrollTo(0, to), y);
      await page.waitForTimeout(220);
    }

    expect(errors).toEqual([]);
  });

  test("motion actually attaches", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(2000);

    await expect(page.locator("html")).toHaveClass(/is-enhanced/);

    // The stage pin and the page-progress trigger.
    const triggers = await page.evaluate(() => window.ScrollTrigger.getAll().length);
    expect(triggers).toBeGreaterThanOrEqual(2);

    // The opening is pinned; that pin is what the traversal scrubs.
    expect(await page.locator(".pin-spacer").count()).toBeGreaterThan(0);
  });

  test("the progress bar reports position, and only that", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(1500);

    const read = () =>
      page.evaluate(() => {
        const m = new DOMMatrixReadOnly(getComputedStyle(document.getElementById("bar")).transform);
        return m.a;
      });

    const atTop = await read();
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(900);
    const atBottom = await read();

    // The previous bar meant "skills seen" during the chapters and "size of the
    // library" during the hero, so it counted up and then jumped backwards.
    expect(atBottom).toBeGreaterThan(atTop);
    expect(atBottom).toBeLessThanOrEqual(1.01);
  });
});
