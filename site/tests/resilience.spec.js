import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { openWorkspace, readState, activate, assertReadableLabels, assertNoRuntimeErrors, ensureFiltersOpen, settleMotion } from "../scripts/workspace-test-helpers.mjs";
import { EXPECTED_TOTAL, EXPECTED_SOLUTIONS } from "./library-size.mjs";
test.afterEach(async ({ page }) => { await assertNoRuntimeErrors(page); });

function resultFor(page, key) {
  return page.locator(`#gresults button[data-key="${key.replace(/["\\]/g, "\\$&")}"]`);
}

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
        await expect(page.locator(".card")).toHaveCount(EXPECTED_TOTAL);
        await expect(page.locator(".sol")).toHaveCount(EXPECTED_SOLUTIONS);
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
  test("loads nothing from another origin during real interactions", async ({ page, baseURL }, testInfo) => {
    // The served port is per worktree (SITE_TEST_PORT), so the one legitimate
    // origin comes from the configured baseURL and is resolved BEFORE the first
    // request is observed. The comparison itself is unchanged: exact origin
    // equality, anything else is a third party.
    const ownOrigin = new URL(baseURL).origin;
    const external = [], failed = [];
    page.on("request", (r) => {
      const url = new URL(r.url());
      if (url.protocol !== "data:" && url.origin !== ownOrigin) external.push(`${r.resourceType()} ${r.url()}`);
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
      await expect(page.locator(".card")).toHaveCount(EXPECTED_TOTAL);
      await expect(page.locator(".sol")).toHaveCount(EXPECTED_SOLUTIONS);
      await page.locator("#library > summary").click();
      await page.locator(".lib__cat > summary").first().click();
      await expect(page.locator(".card").first()).toBeVisible();
      await expect(page.locator(".card").first().locator("p")).not.toBeEmpty();
      expect(errors).toEqual([]);
    });
  }
});

test.describe("scripting-disabled library and Solutions", () => {
  // The no-JS contract in UI_NAVIGATION.md is functional, not textual: the full
  // `.card` and `.sol` HTML "still works" behind its disclosures. Counting
  // elements only proves they exist, so these tests navigate and open things the
  // way a reader with scripting disabled actually would.
  test("graph fragment anchors land on the exact card and open its collapsed category", async ({ browser }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const page = await ctx.newPage();
    await page.goto("/index.html");

    // Nothing pre-opened: the reveal below has to come from real navigation.
    await expect(page.locator(".no-js")).toBeVisible();
    await expect(page.locator("#library")).not.toHaveAttribute("open", "");
    await expect(page.locator("#cat-finance")).not.toHaveAttribute("open", "");

    // Deterministic spread: the first graph anchor, a Solution lead's anchor,
    // and the anchor of the first card in #cat-finance (reached through its
    // node, so card and anchor identity are both exercised).
    const targets = await page.evaluate(() => {
      const byKey = new Map([...document.querySelectorAll(".g-node")].map((n) => [n.dataset.key, n]));
      function pick(node) {
        const card = document.getElementById(node.getAttribute("href").slice(1));
        return {
          fragment: node.getAttribute("href").slice(1),
          key: node.dataset.key, name: node.dataset.name,
          catId: card?.closest(".lib__cat")?.id ?? null
        };
      }
      const financeCard = document.querySelector("#cat-finance .card");
      return [
        pick(document.querySelector(".g-node")),
        pick(document.querySelector(".g-node[data-leads]")),
        pick(byKey.get(financeCard.dataset.id))
      ];
    });
    expect(targets.every((t) => t.fragment && t.catId)).toBe(true);

    for (const target of targets) {
      await page.goto(`/index.html#${target.fragment}`);
      const landed = await page.evaluate((t) => {
        const card = document.getElementById(t.fragment);
        const box = card?.getBoundingClientRect();
        return {
          hash: location.hash,
          identity: card?.dataset.id ?? null,
          name: card?.dataset.name ?? null,
          libraryOpen: document.getElementById("library").hasAttribute("open"),
          categoryId: card?.closest(".lib__cat")?.id ?? null,
          categoryOpen: card?.closest(".lib__cat")?.hasAttribute("open") ?? null,
          onScreen: !!box && box.height > 0 && box.bottom > 0 && box.top < innerHeight
        };
      }, target);
      expect(landed.hash, "navigation must actually target the anchor").toBe(`#${target.fragment}`);
      expect(landed.identity, `${target.fragment} must land on the exact card for ${target.key}`).toBe(target.key);
      expect(landed.name).toBe(target.name);
      expect(landed.libraryOpen, "fragment navigation opens the collapsed library").toBe(true);
      expect(landed.categoryId).toBe(target.catId);
      expect(landed.categoryOpen, `${target.catId} opens around its own card`).toBe(true);
      expect(landed.onScreen, `${target.name} is revealed on screen, not just present`).toBe(true);
    }
    await ctx.close();
  });

  test("collapsed categories and Solutions open by real clicks without scripting", async ({ browser }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const page = await ctx.newPage();
    await page.goto("/index.html");

    // The links into the reference sections are plain fragment anchors when no
    // script intercepts them, so they must still navigate. Phones hide the
    // header Solutions link (styles.css), where the skip link is the
    // scripting-free path to the same anchor, activated like a keyboard user.
    const solutionsLink = page.locator('a[data-open="solutions"]');
    if (await solutionsLink.isVisible()) {
      await solutionsLink.click();
    } else {
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");
      expect(await page.evaluate(() => document.activeElement.getAttribute("href"))).toBe("#solutions");
      await page.keyboard.press("Enter");
    }
    await expect(page.locator("#solutions")).toBeInViewport();
    await expect(page.locator("#solutions")).not.toHaveAttribute("open", "");
    await page.locator("#solutions > summary").click();
    await expect(page.locator("#solutions")).toHaveAttribute("open", "");
    const solution = page.locator(".sol").first();
    await expect(solution).toBeVisible();
    await expect(solution.locator("h3")).not.toBeEmpty();
    await expect(solution.locator(".sol__step").first()).not.toBeEmpty();

    await page.locator('a[data-open="library"]').click();
    await expect(page.locator("#library")).toBeInViewport();
    await page.locator("#library > summary").click();
    await expect(page.locator("#library")).toHaveAttribute("open", "");

    // A category is a native disclosure: closed, its cards are unreachable;
    // opened by a real click, exactly its declared count of cards is readable.
    const finance = page.locator("#cat-finance");
    await expect(finance).not.toHaveAttribute("open", "");
    await expect(finance.locator(".card").first()).not.toBeVisible();
    await finance.locator("summary").click();
    await expect(finance).toHaveAttribute("open", "");
    const declared = Number(await finance.getAttribute("data-count"));
    await expect(finance.locator(".card")).toHaveCount(declared);
    for (const card of await finance.locator(".card").all()) {
      await expect(card).toBeVisible();
      await expect(card.locator("h3")).not.toBeEmpty();
      await expect(card.locator("p")).not.toBeEmpty();
    }
    await ctx.close();
  });
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
    await settleMotion(page);
    expect((await readState(page)).camera).not.toEqual(before.camera);
    await activate(page.locator("#greset"), testInfo);
    await page.locator("#gsearch").fill("NDA");
    const first = page.locator("#gresults button[data-key]").first();
    const key = await first.getAttribute("data-key");
    await activate(first, testInfo);
    await expect(page.locator("#top")).toHaveAttribute("data-selected-key", key);
    // Same 18273ef timing adaptation as workspace.spec.js: the scale comparison
    // is a settled-camera read, so it waits for idle. Nothing else is delayed.
    await settleMotion(page);
    const selected = await readState(page);
    await activate(page.locator("#gzoom-in"), testInfo);
    await settleMotion(page);
    expect((await readState(page)).camera.scale).toBeGreaterThan(selected.camera.scale);
    await activate(page.locator("#gfit"), testInfo);
    await assertReadableLabels(page, { selectedKey: key });
    expect(violations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test("real policy keeps filters, Solution focus and path traversal functional", async ({ page }, testInfo) => {
    // The test above proves the policy reports no violations. This one proves
    // the interactions still DO things under that policy: a CSP rule that
    // silently disabled a filter, the Solution focus or the traversal must fail
    // here on the interaction's result, not on a console message.
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
    await ensureFiltersOpen(page);

    // The community dropdown filter must change the actual context, not just
    // the camera: mode, title and the member list all follow the selection.
    const community = data.comms[1];
    await page.locator("#gcommunity").selectOption(String(community.id));
    await expect(page.locator("#top")).toHaveAttribute("data-mode", "community");
    await expect(page.locator("#top")).toHaveAttribute("data-community", String(community.id));
    await expect(page.locator("#workspace-title")).toHaveText(community.label);
    const communityState = await readState(page);
    expect(communityState.matching).toBe(community.size);
    expect(communityState.context.results).toHaveLength(community.size);
    // Filters combine, so leave the community selection before focusing a
    // Solution: this reset is what makes the membership assertion exact.
    await activate(page.locator("#greset"), testInfo);

    // Focusing a Solution: the panel names that Solution, carries its tier and
    // evidence, and the result list becomes exactly its members plus the lead.
    const lead = await page.locator(".sol").first().getAttribute("data-sol");
    await page.locator("#gsolution").selectOption(lead);
    await expect(page.locator("#top")).toHaveAttribute("data-mode", "solution");
    await expect(page.locator("#top")).toHaveAttribute("data-solution", lead);
    const solTitle = await page.locator(`.sol[data-sol="${lead}"] h3`).textContent();
    await expect(page.locator("#workspace-title")).toHaveText(solTitle.trim());
    await expect(page.locator("#paneltier")).toHaveText("solution");
    const tier = (await page.locator(`.sol[data-sol="${lead}"] .sol__tier`).textContent()).trim();
    await expect(page.locator("#paneldesc")).toContainText(`${tier} Solution.`);
    const expected = await page.locator(".g-node").evaluateAll((nodes, chosen) =>
      nodes.filter((n) => (n.dataset.sol || "").split(" ").includes(chosen) || n.dataset.key === chosen)
        .map((n) => n.dataset.key).sort(), lead);
    expect(expected.length, "the chosen Solution must have members").toBeGreaterThan(0);
    const solutionState = await readState(page);
    expect(solutionState.matching).toBe(expected.length);
    expect(solutionState.context.results.slice().sort()).toEqual(expected);

    // The traversal: trace a real stated edge end to end. A direct edge is the
    // provably shortest walk, so the result is exactly the two endpoints.
    await activate(page.locator("#greset"), testInfo);
    const edgeIndex = data.edges.findIndex((e) => e[3] === 0);
    expect(edgeIndex, "data.js must contain at least one stated edge").toBeGreaterThanOrEqual(0);
    const startKey = data.nodes[data.edges[edgeIndex][0]];
    const endKey = data.nodes[data.edges[edgeIndex][1]];
    const names = await page.evaluate(() => Object.fromEntries(
      [...document.querySelectorAll(".g-node")].map((n) => [n.dataset.key, n.dataset.name])));
    async function choose(key) {
      await page.locator("#gsearch").fill(names[key]);
      await activate(resultFor(page, key), testInfo);
    }
    await activate(page.locator("#gpath"), testInfo);
    await expect(page.locator("#gpath")).toHaveAttribute("aria-pressed", "true");
    await choose(startKey);
    await choose(endKey);
    await expect(page.locator("#top")).toHaveAttribute("data-mode", "path");
    expect(JSON.parse(await page.locator("#top").getAttribute("data-path")))
      .toEqual([startKey, endKey]);
    await expect(page.locator("#panelchain li")).toHaveCount(2);
    const hop = page.locator("#panelchain li").nth(1).locator("p");
    await expect(hop).toHaveText(/^Stated: /);
    for (const why of data.why[edgeIndex]) await expect(hop).toContainText(why);

    // The evidence-tier filter must recompute the walk under stated-only and
    // keep a stated walk standing; a rule that silenced the toggle fails here.
    await activate(page.locator("#gstated"), testInfo);
    await expect(page.locator("#gstated")).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator("#gstated")).toHaveText("Stated only");
    await expect(page.locator("#top")).toHaveAttribute("data-evidence", "stated");
    expect(JSON.parse(await page.locator("#top").getAttribute("data-path")))
      .toEqual([startKey, endKey]);
    await expect(page.locator("#panelchain li").nth(1).locator("p")).toHaveText(/^Stated: /);

    expect(violations).toEqual([]);
    expect(errors).toEqual([]);
  });
});
