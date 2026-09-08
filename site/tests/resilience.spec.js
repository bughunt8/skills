import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

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

    // The graph is still there and still complete: reduced motion removes the
    // traversal, not the content or the ability to explore it.
    expect(await page.locator(".g-lead").count()).toBeGreaterThan(0);
    const dimmed = await page.locator(".g-node").evaluateAll((ns) =>
      ns.filter((n) => Number(getComputedStyle(n).opacity) < 0.1).length
    );
    expect(dimmed, "nothing may be hidden by a focus state nobody triggered").toBe(0);
    expect(errors).toEqual([]);
    await ctx.close();
  });

  test("nothing on the page reads zero", async ({ browser }) => {
    const { ctx, page } = await openReduced(browser);

    // The old hero animated its number up from 0 as you scrolled, and the HUD
    // started at "000 / 490". With motion off both simply sat at zero, so the page
    // opened by understating itself by its entire contents.
    const hud = await page.locator("#hudcount").innerText();
    const h1 = await page.locator("h1").innerText();
    const total = await page.evaluate(() => window.SKILLDATA.total);

    expect(hud).toContain(String(total));
    expect(hud).not.toMatch(/\b0+\s*\//);
    expect(h1).toContain(String(total));
    expect(h1).not.toMatch(/\b0\s*(Solutions|skills)/);
    await ctx.close();
  });
});

test.describe("narrow viewports", () => {
  test("the graph stays usable by touch", async ({ browser }) => {
    const ctx = await browser.newContext({
      viewport: { width: 390, height: 844 },
      hasTouch: true,
      isMobile: true
    });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e)));

    await page.goto("/index.html");
    await page.waitForTimeout(1600);

    // No pinning on a touch-scrolled page.
    expect(await page.locator(".pin-spacer").count()).toBe(0);

    // The graph must still be drawn at a usable size rather than squeezed to a
    // sliver by the desktop two-column layout.
    const box = await page.locator("#gsvg").boundingBox();
    expect(box.width).toBeGreaterThan(280);
    expect(box.height).toBeGreaterThan(300);

    // Interaction is function, not decoration, so it survives on touch: tapping a
    // Solution fills the panel with that Solution.
    await page.locator('.g-lead[data-name="agenthub"]').tap({ force: true });
    await page.waitForTimeout(400);
    await expect(page.locator("#panelname")).toHaveText(/agenthub/);

    // Search is the only practical way through 490 skills on a phone.
    await page.fill("#gsearch", "resume");
    await page.waitForTimeout(400);
    expect(await page.locator(".card.is-hit").count()).toBeGreaterThan(0);

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
      display: getComputedStyle(document.querySelector(".stage h1")).fontFamily
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

test.describe("the production Content-Security-Policy", () => {
  /*
   * This exists because a CSP violation shipped to production and no gate saw it.
   *
   * The policy is set by .htaccess, which only Hostinger serves. The test server
   * here sends no CSP at all, so every browser test passed while the live page
   * logged "Applying inline style violates the following Content Security Policy
   * directive: style-src 'self'" and silently dropped a style. A header that only
   * exists in production is a header that is never tested, so these tests bring the
   * real policy to the local page.
   */

  const htaccess = readFileSync(new URL("../.htaccess", import.meta.url), "utf8");
  const csp = (htaccess.match(/Content-Security-Policy\s+"([^"]+)"/) || [])[1];

  test("is same-origin with no inline escape hatch", () => {
    expect(csp, "no CSP found in .htaccess").toBeTruthy();
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("style-src 'self'");
    expect(csp).not.toContain("unsafe-inline");
    expect(csp).not.toContain("unsafe-eval");
  });

  test("nothing in the built page needs an inline style", () => {
    // Under style-src 'self' the browser refuses a style attribute outright, and
    // hashes do not apply to them. One `style="margin-top: 28px"` survived in the
    // hand-written part of index.html and was dropped on every page load in
    // production.
    const page = readFileSync(new URL("../index.html", import.meta.url), "utf8");
    // Matches a style attribute however it is quoted. The double-quoted-only
    // version of this check had two bypasses, single-quoted and unquoted, and a
    // gate with a bypass is a gate that will eventually be walked around by
    // accident rather than on purpose.
    expect(
      page.match(/\sstyle\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi) || [],
      "an inline style is blocked by the production CSP, so it silently does nothing"
    ).toEqual([]);
    expect(page).not.toMatch(/<style[\s>]/);
  });

  test("the page loads clean with the real policy applied", async ({ page }) => {
    const violations = [];
    page.on("console", (m) => {
      if (m.type() === "error" && /Content Security Policy/i.test(m.text())) {
        violations.push(m.text());
      }
    });

    // Serve the local page with production's header attached.
    await page.route("**/index.html", async (route) => {
      const res = await route.fetch();
      await route.fulfill({
        response: res,
        headers: { ...res.headers(), "content-security-policy": csp }
      });
    });

    await page.goto("/index.html");
    await page.waitForTimeout(1800);

    // Exercise the parts that manipulate style at runtime, since CSSOM writes are
    // allowed but setAttribute("style", ...) is not, and only one of those is
    // visible in the source.
    await page.locator('.g-lead[data-name="agenthub"]').click({ force: true });
    await page.evaluate(() => window.scrollTo(0, 1200));
    await page.waitForTimeout(900);
    await page.fill("#gsearch", "finance");
    await page.waitForTimeout(500);

    expect(violations).toEqual([]);
  });
});
