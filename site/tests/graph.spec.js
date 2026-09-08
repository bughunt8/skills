import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const html = readFileSync(join(root, "index.html"), "utf8");
const data = JSON.parse(
  readFileSync(join(root, "data.js"), "utf8")
    .replace("window.SKILLDATA=", "")
    .replace(/;\s*$/, "")
);

/*
 * The graph is the opening of the page and its navigation, so these are function
 * tests, not decoration tests. Each one below failed at least once during the
 * build, which is the only reason any of them are worth running.
 */

test.describe("the Solution graph", () => {
  test("is prerendered, not drawn by script", async ({ page }) => {
    // Asserted against the shipped file first: if the graph only exists after
    // JavaScript runs, the opening image of the page is a blank box for anyone the
    // script fails for.
    const leads = (html.match(/class="g-lead\b/g) || []).length;
    expect(leads).toBe(data.solutions);
    expect((html.match(/class="g-edge/g) || []).length).toBeGreaterThan(200);

    await page.goto("/index.html");
    await expect(page.locator(".g-lead")).toHaveCount(data.solutions);
    await expect(page.locator(".sol")).toHaveCount(data.solutions);
    await expect(page.locator(".card")).toHaveCount(data.total);
  });

  test("every lead node has a matching Solution card, and the reverse", async ({ page }) => {
    await page.goto("/index.html");
    const pair = await page.evaluate(() => ({
      nodes: [...document.querySelectorAll(".g-lead")].map((e) => e.getAttribute("data-id")),
      cards: [...document.querySelectorAll(".sol")].map((e) => e.getAttribute("data-sol"))
    }));
    expect([...pair.nodes].sort()).toEqual([...pair.cards].sort());
  });

  test("focusing a Solution lights exactly the skills it leads", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(600);

    // Includes c-level-agents, which leads 21, and the Solutions that share a
    // skill with another. data-sol used to hold a single owner, so focusing the
    // second Solution to claim a shared skill lit one fewer node than its own card
    // listed: code-review is led by both idea-to-shipped-code and hard-to-find-bug.
    const ids = await page.evaluate(() =>
      [...document.querySelectorAll(".g-lead")].map((e) => e.getAttribute("data-id"))
    );
    expect(ids.length).toBe(data.solutions);

    for (const id of ids) {
      // dispatchEvent, not click(). locator.click() computes a box and then moves a
      // real pointer to it, and this page runs Lenis smooth scrolling, so the
      // coordinate is stale by the time the event is dispatched and the click lands
      // on the SVG background instead of the node. A real pointer click is covered
      // separately below, at a coordinate measured immediately beforehand.
      await page.locator(`.g-lead[data-id="${id}"]`).dispatchEvent("click");
      const seen = await page.evaluate((leadId) => {
        const card = document.querySelector(`.sol[data-sol="${CSS.escape(leadId)}"]`);
        return {
          panel: document.getElementById("panelname").textContent.trim(),
          panelChain: document.querySelectorAll("#panelchain li").length,
          cardChain: card.querySelectorAll(".sol__step").length,
          lit: document.querySelectorAll(".g-node--member.is-on").length,
          edges: document.querySelectorAll(".g-edge.is-on").length,
          cardMarked: card.classList.contains("is-on")
        };
      }, id);

      expect(seen.panel, `panel for ${id}`).toContain(id);
      expect(seen.panelChain, `panel chain for ${id}`).toBe(seen.cardChain);
      expect(seen.lit, `lit members for ${id}`).toBe(seen.cardChain);
      expect(seen.edges, `lit edges for ${id}`).toBe(seen.cardChain);
      expect(seen.cardMarked, `card marked for ${id}`).toBe(true);
    }
  });

  test("the camera never moves, so every Solution stays clickable", async ({ page }) => {
    await page.goto("/index.html");
    const before = await page.getAttribute("#gsvg", "viewBox");

    // An earlier version eased the viewBox to frame the focused Solution. Zooming
    // in put every other Solution outside the frame and made it unclickable, so
    // the graph's own navigation broke unless the reader knew to press Escape. It
    // also scaled the labels, because SVG text is measured in user units.
    await page.locator('.g-lead[data-id="agenthub"]').dispatchEvent("click");
    await page.waitForTimeout(900);
    await page.mouse.wheel(0, 700);
    await page.waitForTimeout(900);

    expect(await page.getAttribute("#gsvg", "viewBox")).toBe(before);
  });

  test("clicking commits, hovering only previews", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(600);

    // The selection model is reflected onto the stage, because "pinned" and
    // "merely hovered" is exactly the distinction that broke twice and cannot be
    // asserted from the outside otherwise.
    await page.locator('.g-lead[data-id="agenthub"]').dispatchEvent("click");
    await expect(page.locator("#top")).toHaveAttribute("data-pinned", "agenthub");

    // Hovering a different Solution must not replace a committed selection. It did,
    // and worse: the pin was being cleared a tick later by the traversal's own dead
    // zone, so a click at the top of the page appeared to work and then quietly
    // stopped holding.
    await page.locator('.g-lead[data-id="c-level-agents"]').hover({ force: true });
    await page.waitForTimeout(400);
    await expect(page.locator("#panelname")).toHaveText(/agenthub/);
    await expect(page.locator("#top")).toHaveAttribute("data-pinned", "agenthub");

    // And it must still be holding a second later, not just immediately.
    await page.waitForTimeout(1000);
    await expect(page.locator("#top")).toHaveAttribute("data-pinned", "agenthub");

    // With nothing pinned, hover previews.
    await page.keyboard.press("Escape");
    await expect(page.locator("#top")).toHaveAttribute("data-pinned", "");
    await page.locator('.g-lead[data-id="c-level-agents"]').hover({ force: true });
    await page.waitForTimeout(300);
    await expect(page.locator("#panelname")).toHaveText(/c-level-agents/);
  });

  test("a real pointer click hits a node", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(1200);

    // The rest of the suite dispatches events, so this is the one test that proves
    // the nodes are actually big enough to hit with a pointer, and that nothing is
    // layered over the graph intercepting clicks. The panel and the intro used to
    // sit on top of it, and two Solutions were unclickable.
    for (const id of ["commercial-skills", "c-level-agents", "agenthub"]) {
      const pt = await page.evaluate((leadId) => {
        const g = document.querySelector(`.g-lead[data-id="${CSS.escape(leadId)}"]`);
        const r = g.getBoundingClientRect();
        const cx = Math.round(r.left + r.width / 2);
        const cy = Math.round(r.top + r.height / 2);
        const el = document.elementFromPoint(cx, cy);
        return { cx, cy, owner: el && el.closest ? el.closest(".g-lead")?.getAttribute("data-id") : null };
      }, id);

      // Whatever is on top at the node's centre must be the node itself.
      expect(pt.owner, `element on top at ${id}`).toBe(id);

      await page.mouse.click(pt.cx, pt.cy);
      await page.waitForTimeout(250);
      await expect(page.locator("#top")).toHaveAttribute("data-pinned", id);
    }
  });

  test("search finds skills and opens the category holding them", async ({ page }) => {
    await page.goto("/index.html");

    // Every category starts closed, so a hit inside one is a hit nobody can see
    // unless searching opens it.
    await expect(page.locator(".lib__cat[open]")).toHaveCount(0);

    await page.fill("#gsearch", "gdpr");
    await page.waitForTimeout(400);

    const found = await page.evaluate(() => ({
      dim: document.getElementById("top").classList.contains("is-dim"),
      nodeHits: document.querySelectorAll(".g-node.is-hit").length,
      visibleCardHits: [...document.querySelectorAll(".card.is-hit")].filter(
        (c) => c.getBoundingClientRect().height > 0
      ).length,
      opened: document.querySelectorAll(".lib__cat[open]").length
    }));
    expect(found.dim).toBe(true);
    expect(found.nodeHits).toBeGreaterThan(0);
    expect(found.opened).toBeGreaterThan(0);
    expect(found.visibleCardHits).toBeGreaterThan(0);

    await page.fill("#gsearch", "");
    await page.waitForTimeout(400);
    await expect(page.locator(".lib__cat[open]")).toHaveCount(0);
    await expect(page.locator(".card.is-hit")).toHaveCount(0);
  });

  test("the provenance filters select by tier", async ({ page }) => {
    await page.goto("/index.html");
    await page.click('.chip[data-tier="curated"]');
    await page.waitForTimeout(300);

    const lit = await page.locator(".g-lead.is-hit").count();
    expect(lit).toBe(data.tiers.curated);
    expect(await page.locator(".sol.is-on").count()).toBe(data.tiers.curated);

    await page.click("#greset");
    await page.waitForTimeout(300);
    expect(await page.locator(".is-hit, .is-on").count()).toBe(0);
  });

  test("scrolling travels between Solutions", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(700);

    const seen = new Set();
    for (const y of [400, 800, 1200, 1600, 2000]) {
      await page.evaluate((to) => window.scrollTo(0, to), y);
      await page.waitForTimeout(500);
      seen.add(await page.locator("#panelname").innerText());
      expect(await page.locator(".beat.is-on").count()).toBe(1);
    }
    // The traversal must actually move; a pin that reports the same Solution the
    // whole way down is a pin that is not wired to anything.
    expect(seen.size).toBeGreaterThan(2);
  });

  test("lead nodes are keyboard reachable", async ({ page }) => {
    await page.goto("/index.html");
    const tabbable = await page.locator(".g-lead[tabindex='0']").count();
    expect(tabbable).toBe(data.solutions);

    await page.locator('.g-lead[data-id="agenthub"]').focus();
    await page.keyboard.press("Enter");
    await page.waitForTimeout(300);
    await expect(page.locator("#panelname")).toHaveText(/agenthub/);
  });
});

test.describe("the page states its size honestly", () => {
  test("the headline never reads zero", async ({ page }) => {
    // The previous hero animated its number up from 0 as you scrolled, so the
    // first thing every visitor read was "0 skills, 24 categories". A headline's
    // resting state must not be a false statement.
    expect(html).not.toMatch(/<h1>[\s\S]*?>0</);

    await page.goto("/index.html");
    for (const y of [0, 200, 900, 1800]) {
      await page.evaluate((to) => window.scrollTo(0, to), y);
      await page.waitForTimeout(300);
      const h1 = await page.locator("h1").innerText();
      expect(h1, `headline at y=${y}`).toContain(String(data.total));
      expect(h1, `headline at y=${y}`).not.toMatch(/\b0\s*(Solutions|skills)/);
    }
  });

  test("the whole page fits in a sane amount of scrolling", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(1200);
    const height = await page.evaluate(() => document.body.scrollHeight);

    // This page was 76,000 pixels tall: 24 pinned chapters, each scrubbing a
    // filmstrip sideways, with the graph 3,000px down and the library behind all
    // of it. The budget exists so that never comes back by accident.
    expect(height).toBeLessThan(20000);
    expect(height).toBeGreaterThan(4000);
  });
});
