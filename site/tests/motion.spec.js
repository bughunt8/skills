import { test, expect } from "@playwright/test";
import { readFileSync, readdirSync } from "node:fs";
import { openWorkspace, readState, activate, assertNoRuntimeErrors } from "../scripts/workspace-test-helpers.mjs";
test.afterEach(async ({ page }) => { await assertNoRuntimeErrors(page); });

test.describe("no scroll choreography", () => {
  test("no HUD, rail, scroll triggers or scroll-animation assets ship", async ({ page }) => {
    await openWorkspace(page);
    await expect(page.locator("#hud, #rail, .pin-spacer")).toHaveCount(0);
    const runtime = await page.evaluate(() => ({
      gsap: typeof window.gsap,
      scrollTrigger: typeof window.ScrollTrigger,
      lenis: typeof window.Lenis,
      requests: performance.getEntriesByType("resource").map((r) => r.name)
    }));
    expect(runtime.gsap).toBe("undefined");
    expect(runtime.scrollTrigger).toBe("undefined");
    expect(runtime.lenis).toBe("undefined");
    expect(runtime.requests.filter((url) => /gsap|scrolltrigger|lenis/i.test(url))).toEqual([]);
    const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
    const app = readFileSync(new URL("../app.js", import.meta.url), "utf8");
    expect(html).not.toMatch(/(?:src|href)=["'][^"']*(?:gsap|ScrollTrigger|lenis)/i);
    expect(app).not.toMatch(/ScrollTrigger|gsap\.|new\s+Lenis/);
    // Historical licence copies may remain in the repository, but the actual
    // production assembly must exclude the retired vendor directory completely.
    const deploy = readFileSync(new URL("../../.github/workflows/site-deploy.yml", import.meta.url), "utf8");
    expect(deploy, "legacy vendor bytes must never enter the deployed site").toContain("--exclude 'vendor'");
    const assets = readdirSync(new URL("../", import.meta.url), { recursive: true })
      .filter((p) => !/^(node_modules|test-results|playwright-report|tests|scripts|vendor)\//.test(p));
    expect(assets.filter((p) => /(?:gsap|scrolltrigger|lenis).*\.(?:js|mjs)$/i.test(p))).toEqual([]);
  });

  test("real wheel, pointer passage and idle never drive context", async ({ page }, testInfo) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(String(error)));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    await openWorkspace(page);
    await page.locator("#gsearch").fill("NDA");
    await expect(page.locator("#gresults button[data-key]").first()).toBeVisible();
    await activate(page.locator("#gresults button[data-key]").first(), testInfo);
    const before = await readState(page);
    const graph = await page.locator("#gsvg").boundingBox();
    await page.mouse.move(graph.x + graph.width / 2, graph.y + graph.height / 2, { steps: 12 });
    await page.mouse.wheel(0, 550);
    await page.waitForTimeout(1100);
    await page.mouse.wheel(0, -550);
    await page.waitForTimeout(1100);
    const after = await readState(page);
    expect(after.context).toEqual(before.context);
    expect(errors).toEqual([]);
    await expect(page.locator(".pin-spacer")).toHaveCount(0);
  });
});
