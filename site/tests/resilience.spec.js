import { test, expect } from "@playwright/test";

/*
 * The page must degrade to a plain, complete list rather than to a broken one.
 * Two failures found by hand are pinned here:
 *   1. With prefers-reduced-motion set, the decorative ghost wordmark
 *      (white-space: nowrap at 176px) had nothing containing it once pinning was
 *      off, and overflowed the document by 582px.
 *   2. Cards left at 0.3 opacity by the reduced-motion path would have been
 *      unreadable, so opacity is asserted, not assumed.
 */

const WIDTHS = [320, 375, 390, 768, 1024, 1280, 1440, 1920];

test.describe("no horizontal overflow at any width", () => {
  for (const width of WIDTHS) {
    for (const reducedMotion of ["no-preference", "reduce"]) {
      test(`${width}px, motion=${reducedMotion}`, async ({ browser }) => {
        const ctx = await browser.newContext({
          viewport: { width, height: 860 },
          reducedMotion
        });
        const page = await ctx.newPage();
        await page.goto("/index.html");
        await page.waitForTimeout(1600);

        const overflow = await page.evaluate(
          () =>
            document.documentElement.scrollWidth -
            document.documentElement.clientWidth
        );
        expect(overflow, `overflow at ${width}px`).toBeLessThanOrEqual(0);

        // Content must be reachable, so check the elements that carry meaning.
        // A blanket scan over every element is not a valid test here: it flags
        // the deliberately off-screen skip link, and getBoundingClientRect
        // reports an element's untruncated box even when an ancestor clips it,
        // so children of an overflow:hidden mask look like overflow when the
        // reader can see nothing wrong.
        const wide = await page.evaluate(() => {
          const w = document.documentElement.clientWidth;
          const clipped = (el) => {
            for (let p = el.parentElement; p; p = p.parentElement) {
              const o = getComputedStyle(p).overflowX;
              if (o === "hidden" || o === "auto" || o === "scroll") return true;
            }
            return false;
          };
          return [...document.querySelectorAll(".card h3, .card p, h1, h2, .close p")]
            .filter((el) => {
              const b = el.getBoundingClientRect();
              return b.width > 0 && b.right > w + 1 && !clipped(el);
            })
            .map((el) => el.className || el.tagName)
            .slice(0, 5);
        });
        expect(wide, `content past the viewport at ${width}px`).toEqual([]);
        await ctx.close();
      });
    }
  }
});

/*
 * These build their contexts explicitly rather than using describe-level
 * `test.use({ reducedMotion })`. The overflow sweep above proves context-level
 * emulation works, while the describe-level form was not taking effect here: the
 * page came back with 23 pin-spacers and an enhanced document, which is the
 * no-preference path. An emulation option that silently does not apply turns
 * these into tests that pass for the wrong reason, so the mechanism that
 * demonstrably works is used instead.
 */
test.describe("prefers-reduced-motion", () => {
  const openReduced = async (browser) => {
    const ctx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      reducedMotion: "reduce"
    });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto("/index.html");
    await page.waitForTimeout(1800);
    // Confirm the emulation actually applied before asserting anything on it.
    const applied = await page.evaluate(
      () => window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
    expect(applied, "reduced-motion emulation must be in effect").toBe(true);
    return { ctx, page, errors };
  };

  test("becomes a static, complete, readable list", async ({ browser }) => {
    const { ctx, page, errors } = await openReduced(browser);

    // No pinning at all.
    expect(await page.locator(".pin-spacer").count()).toBe(0);
    await expect(page.locator("html")).not.toHaveClass(/is-enhanced/);

    // Every card fully opaque and untransformed, so nothing is hidden.
    const hidden = await page.locator(".card").evaluateAll((cards) =>
      cards.filter((c) => Number(getComputedStyle(c).opacity) < 0.95).length
    );
    expect(hidden).toBe(0);

    // The decorative ghost is removed rather than left to overflow.
    const ghosts = await page.locator(".chapter__ghost").evaluateAll((els) =>
      els.filter((e) => getComputedStyle(e).display !== "none").length
    );
    expect(ghosts).toBe(0);

    expect(errors).toEqual([]);
    await ctx.close();
  });

  test("the counter is truthful instead of stuck at zero", async ({ browser }) => {
    const { ctx, page } = await openReduced(browser);
    const n = await page.evaluate(
      () => Number(document.querySelector("#hudcount b")?.textContent ?? -1)
    );
    const total = await page.evaluate(() => window.SKILLDATA.total);
    expect(n).toBe(total);
    await ctx.close();
  });
});

test.describe("narrow viewports", () => {
  test("swap pinning for a native scroll-snap carousel", async ({ browser }) => {
    const ctx = await browser.newContext({
      viewport: { width: 390, height: 844 },
      hasTouch: true,
      isMobile: true
    });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e)));

    await page.goto("/index.html");
    await page.waitForTimeout(1800);

    // Pinning a horizontal strip inside a touch-scrolled page fights the reader,
    // so the strip becomes a native scroll-snap carousel instead.
    expect(await page.locator(".pin-spacer").count()).toBe(0);

    // What makes it swipeable: a horizontal scroll container whose content
    // overflows it, with snap points. Asserting that assigning scrollLeft moves
    // it is a test of the browser's scroll-snap implementation, not of our CSS,
    // and snapping legitimately rejects an arbitrary offset.
    const strip = await page.evaluate(() => {
      const s = document.querySelector(".chapter .strip");
      const cs = getComputedStyle(s);
      return {
        overflowX: cs.overflowX,
        snap: cs.scrollSnapType,
        scrollable: s.scrollWidth - s.clientWidth,
        cards: s.querySelectorAll(".card").length,
        snapAligned: [...s.querySelectorAll(".card")].every(
          (c) => getComputedStyle(c).scrollSnapAlign !== "none"
        )
      };
    });
    expect(["auto", "scroll"]).toContain(strip.overflowX);
    expect(strip.snap).toMatch(/x/);
    expect(strip.scrollable, "content must overflow to be swipeable").toBeGreaterThan(0);
    expect(strip.snapAligned, "cards must define snap points").toBe(true);

    // The fixed rail would eat the screen on a phone.
    await expect(page.locator("#rail")).toBeHidden();

    expect(errors).toEqual([]);
    await ctx.close();
  });
});

test.describe("no third party in the request path", () => {
  /*
   * The motion libraries and both webfonts used to come from jsDelivr and Google
   * Fonts. Both see every reader, both can be blocked or disappear, and jsDelivr
   * routes through Cloudflare. They are now served from this origin, and these
   * tests keep it that way.
   *
   * The font check exists because moving them in place broke them silently: CSS
   * url() resolves against the stylesheet, not the page, so url('./fonts/x.woff2')
   * inside fonts/fonts.css requested /fonts/fonts/x.woff2. The browser fell back
   * to a system font and said nothing.
   */

  test("loads nothing from another origin", async ({ page }) => {
    const external = [];
    page.on("request", (r) => {
      const url = r.url();
      if (!url.startsWith("http://127.0.0.1") && !url.startsWith("data:")) {
        external.push(`${r.resourceType()} ${url}`);
      }
    });
    page.on("requestfailed", (r) => external.push(`FAILED ${r.url()}`));

    await page.goto("/index.html", { waitUntil: "load" });
    await page.waitForTimeout(2500);

    expect(external, "the page must be entirely self-hosted").toEqual([]);
  });

  test("the motion libraries are served from this origin", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(2500);

    const srcs = await page.locator("script[src]").evaluateAll((els) =>
      els.map((e) => e.getAttribute("src"))
    );
    for (const src of srcs) {
      expect(src, `script src must be relative: ${src}`).toMatch(/^\.\//);
    }
    // And they must actually have loaded, not merely be referenced.
    const globals = await page.evaluate(() => ({
      gsap: typeof window.gsap,
      st: typeof window.ScrollTrigger,
      lenis: typeof window.Lenis
    }));
    expect(globals.gsap).not.toBe("undefined");
    expect(globals.st).not.toBe("undefined");
    expect(globals.lenis).not.toBe("undefined");
  });

  test("the self-hosted fonts actually load", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(2500);
    await page.evaluate(() => document.fonts.ready);

    const state = await page.evaluate(() => ({
      errored: [...document.fonts]
        .filter((f) => f.status === "error")
        .map((f) => `${f.family} ${f.weight}`),
      loaded: [...document.fonts].filter((f) => f.status === "loaded").length,
      served: performance
        .getEntriesByType("resource")
        .filter((r) => r.name.endsWith(".woff2"))
        .map((r) => r.name),
      display: getComputedStyle(document.querySelector(".hero h1")).fontFamily
    }));

    expect(state.errored, "a font face failed to load").toEqual([]);
    expect(state.loaded, "no font face loaded at all").toBeGreaterThan(0);
    expect(state.served.length, "no woff2 was fetched").toBeGreaterThan(0);
    for (const url of state.served) {
      expect(url).toContain("/fonts/");
      expect(url, "double fonts/ path regression").not.toContain("/fonts/fonts/");
    }
    // The display family must be the one we ship, not a system fallback.
    expect(state.display).toContain("Space Grotesk");
  });

  test("no stylesheet or font is requested from a CDN", async () => {
    const fs = await import("node:fs");
    const html = fs.readFileSync(new URL("../index.html", import.meta.url), "utf8");
    const css = fs.readFileSync(new URL("../styles.css", import.meta.url), "utf8");
    const fonts = fs.readFileSync(new URL("../fonts/fonts.css", import.meta.url), "utf8");

    for (const [name, text] of [["index.html", html], ["styles.css", css], ["fonts.css", fonts]]) {
      for (const host of ["jsdelivr", "fonts.googleapis.com", "fonts.gstatic.com", "unpkg", "cdnjs"]) {
        expect(text, `${name} references ${host}`).not.toContain(host);
      }
    }
  });
});

test.describe("graceful failure", () => {
  test("survives the motion libraries failing to load", async ({ page }) => {
    // The libraries are self-hosted now, so blocking jsDelivr would prove
    // nothing: the request is never made. Block what is actually requested.
    await page.route("**/vendor/*.js", (r) => r.abort());

    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e)));

    await page.goto("/index.html");
    await page.waitForTimeout(1600);

    const total = await page.evaluate(() => window.SKILLDATA.total);
    await expect(page.locator(".card")).toHaveCount(total);
    await expect(page.locator("html")).not.toHaveClass(/is-enhanced/);
    expect(errors, "must bail out quietly, not throw").toEqual([]);
  });
});
