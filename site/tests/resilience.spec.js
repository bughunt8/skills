import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { openWorkspace, readState, activate, assertReadableLabels, assertNoRuntimeErrors, ensureFiltersOpen } from "../scripts/workspace-test-helpers.mjs";
test.afterEach(async ({ page }) => { await assertNoRuntimeErrors(page); });

const data = JSON.parse(readFileSync(new URL("../data.js", import.meta.url), "utf8")
  .replace(/^window\.SKILLDATA=/, "").replace(/;\s*$/, ""));

test.describe("responsive resilience", () => {
  for (const width of [320, 375, 390, 768, 1024, 1280, 1440, 1920]) {
    for (const reducedMotion of ["no-preference", "reduce"]) {
      test(`${width}px has no horizontal overflow with motion=${reducedMotion}`, async ({ page }) => {
        await page.setViewportSize({ width, height: 860 });
        await page.emulateMedia({ reducedMotion });
        await openWorkspace(page);
        const overflow = await page.evaluate(() => ({
          page: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          controls: [...document.querySelectorAll("#workspace-header input, #workspace-header select, #workspace-header button")]
            .filter((e) => {
              const b = e.getBoundingClientRect();
              return b.width && (b.left < -1 || b.right > innerWidth + 1);
            }).map((e) => e.id)
        }));
        expect(overflow.page).toBeLessThanOrEqual(1);
        expect(overflow.controls).toEqual([]);
        await expect(page.locator(".card")).toHaveCount(490);
        await expect(page.locator(".sol")).toHaveCount(50);
        await expect(page.locator("#workspace-title")).not.toBeEmpty();
        expect((await readState(page)).matching).toBeGreaterThan(0);
      });
    }
  }

  test("reduced motion keeps the complete graph usable rather than disabling controls", async ({ page }, testInfo) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await openWorkspace(page);
    expect(await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches)).toBe(true);
    await expect(page.locator(".pin-spacer")).toHaveCount(0);
    await expect(page.locator(".g-node")).toHaveCount(data.total);
    await page.locator("#gsearch").fill("NDA");
    const first = page.locator("#gresults button[data-key]").first();
    await expect(first).toBeVisible();
    const key = await first.getAttribute("data-key");
    await activate(first, testInfo);
    await expect(page.locator("#top")).toHaveAttribute("data-selected-key", key);
    await assertReadableLabels(page, { selectedKey: key });
    await page.locator("#library > summary").click();
    await page.locator(".lib__cat > summary").first().click();
    const card = page.locator(".card").first();
    await expect(card).toBeVisible();
    expect(await card.evaluate((e) => getComputedStyle(e).opacity)).toBe("1");
  });
});

test.describe("no third party in the request path", () => {
  test("loads nothing from another origin during real interactions", async ({ page }, testInfo) => {
    const external = [], failed = [];
    page.on("request", (r) => {
      const url = new URL(r.url());
      if (url.protocol !== "data:" && url.origin !== "http://127.0.0.1:8123") external.push(`${r.resourceType()} ${r.url()}`);
    });
    page.on("requestfailed", (r) => failed.push(r.url()));
    await openWorkspace(page);
    await page.locator("#gsearch").fill("NDA");
    await activate(page.locator("#gresults button[data-key]").first(), testInfo);
    await activate(page.locator("#gzoom-in"), testInfo);
    await activate(page.locator("#gfit"), testInfo);
    expect(external).toEqual([]);
    expect(failed).toEqual([]);
  });

  test("scripts use relative same-origin paths and local fonts actually load", async ({ page }) => {
    await openWorkspace(page);
    const state = await page.evaluate(() => ({
      scripts: [...document.querySelectorAll("script[src]")].map((e) => e.getAttribute("src")),
      errored: [...document.fonts].filter((f) => f.status === "error").map((f) => f.family),
      loaded: [...document.fonts].filter((f) => f.status === "loaded").length,
      served: performance.getEntriesByType("resource").filter((r) => r.name.endsWith(".woff2")).map((r) => r.name),
      display: getComputedStyle(document.querySelector("#workspace-title")).fontFamily
    }));
    expect(state.scripts.length).toBeGreaterThanOrEqual(2);
    state.scripts.forEach((src) => expect(src).toMatch(/^\.\//));
    expect(state.errored).toEqual([]);
    expect(state.loaded).toBeGreaterThan(0);
    expect(state.served.length).toBeGreaterThan(0);
    state.served.forEach((url) => {
      expect(url).toContain("/fonts/");
      expect(url).not.toContain("/fonts/fonts/");
    });
    expect(state.display).toContain("Space Grotesk");
  });

  test("no stylesheet or font references a CDN", () => {
    for (const path of ["../index.html", "../styles.css", "../fonts/fonts.css"]) {
      const text = readFileSync(new URL(path, import.meta.url), "utf8");
      for (const host of ["jsdelivr", "fonts.googleapis.com", "fonts.gstatic.com", "unpkg", "cdnjs"])
        expect(text, `${path} references ${host}`).not.toContain(host);
    }
  });
});

test.describe("graceful failure", () => {
  for (const missing of ["app.js", "data.js"]) {
    test(`complete native fallback survives missing ${missing}`, async ({ page }) => {
      const blocked = [];
      await page.route((url) => url.pathname === `/${missing}`, async (route) => {
        blocked.push(route.request().url());
        await route.abort();
      });
      const errors = [];
      page.on("pageerror", (error) => errors.push(String(error)));
      await page.goto("/index.html");
      expect(blocked, "fallback proof must actually block the versioned runtime asset").toHaveLength(1);
      await expect(page.locator("#top")).not.toHaveAttribute("data-ready", "true");
      await expect(page.locator(".card")).toHaveCount(490);
      await expect(page.locator(".sol")).toHaveCount(50);
      await page.locator("#library > summary").click();
      await page.locator(".lib__cat > summary").first().click();
      await expect(page.locator(".card").first()).toBeVisible();
      await expect(page.locator(".card").first().locator("p")).not.toBeEmpty();
      expect(errors).toEqual([]);
    });
  }
});

test.describe("production Content-Security-Policy", () => {
  const htaccess = readFileSync(new URL("../.htaccess", import.meta.url), "utf8");
  const csp = (htaccess.match(/Content-Security-Policy\s+"([^"]+)"/) || [])[1];

  test("same-origin policy has no inline escape hatch", () => {
    expect(csp).toBeTruthy();
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("style-src 'self'");
    expect(csp).not.toContain("unsafe-inline");
    expect(csp).not.toContain("unsafe-eval");
  });

  test("built HTML contains no inline style requiring an exception", () => {
    const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
    expect(html.match(/\sstyle\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi) || []).toEqual([]);
    expect(html).not.toMatch(/<style[\s>]/);
  });

  test("real policy permits search selection and camera changes without violations", async ({ page }, testInfo) => {
    const violations = [], errors = [];
    page.on("console", (m) => {
      if (m.type() === "error" && /Content Security Policy/i.test(m.text())) violations.push(m.text());
    });
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.route("**/index.html", async (route) => {
      const response = await route.fetch();
      await route.fulfill({ response, headers: { ...response.headers(), "content-security-policy": csp } });
    });
    await openWorkspace(page);
    const before = await readState(page);
    await ensureFiltersOpen(page);
    await page.locator("#gcommunity").selectOption(String(data.comms[1].id));
    expect((await readState(page)).camera).not.toEqual(before.camera);
    await activate(page.locator("#greset"), testInfo);
    await page.locator("#gsearch").fill("NDA");
    const first = page.locator("#gresults button[data-key]").first();
    const key = await first.getAttribute("data-key");
    await activate(first, testInfo);
    await expect(page.locator("#top")).toHaveAttribute("data-selected-key", key);
    const selected = await readState(page);
    await activate(page.locator("#gzoom-in"), testInfo);
    expect((await readState(page)).camera.scale).toBeGreaterThan(selected.camera.scale);
    await activate(page.locator("#gfit"), testInfo);
    await assertReadableLabels(page, { selectedKey: key });
    expect(violations).toEqual([]);
    expect(errors).toEqual([]);
  });
});
