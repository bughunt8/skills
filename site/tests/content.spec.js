import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

/*
 * The page is prerendered by build.py. These tests guard the property that makes
 * that worth doing: the content is real HTML, present for a crawler and for a
 * reader with JavaScript disabled, and the numbers shown agree with the markup.
 *
 * An earlier version of this page built every card in JavaScript. It served 858
 * characters of text to a crawler and rendered nothing at all with JS off. These
 * tests exist so that cannot come back unnoticed.
 */

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const data = JSON.parse(
  readFileSync(new URL("../data.js", import.meta.url), "utf8")
    .replace(/^window\.SKILLDATA=/, "")
    .replace(/;\s*$/, "")
);

test.describe("prerendered content", () => {
  test("every card is in the shipped HTML, not created by script", () => {
    const cards = html.match(/<article class="card[^"]*"/g) || [];
    expect(cards.length).toBe(data.total);
    expect(cards.length).toBe(490);
    expect(data.solutions).toBe(50);

    // Workspace chrome can be dynamic; library cards must remain prerendered.
    const app = readFileSync(new URL("../app.js", import.meta.url), "utf8");
    expect(app).not.toMatch(/createElement\(\s*["']article["']/);
  });

  test("renders fully with JavaScript disabled", async ({ browser }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const page = await ctx.newPage();
    await page.goto("/index.html");

    await expect(page.locator(".card")).toHaveCount(data.total);
    await expect(page.locator(".lib__cat")).toHaveCount(data.categories);
    // The Solutions are the page's subject, so they must be present with the
    // script off too, not assembled from a data blob on load.
    await expect(page.locator(".sol")).toHaveCount(data.solutions);
    // The graph draws skills, and every one of them is a real link to its own card, so with
    // the script off the graph is a table of contents rather than an ornament. It used to
    // draw Solutions as nodes too; it does not, and this asserted the old shape.
    await expect(page.locator(".g-node")).toHaveCount(data.total);
    const linked = await page.locator(".g-node").evaluateAll((ns) =>
      ns.every((n) => (n.getAttribute("href") || "").startsWith("#skill-"))
    );
    expect(linked, "every node is a link into the library").toBe(true);

    // Substantive text, not just a shell. The JS-built version scored 858.
    //
    // textContent, not innerText: the library's categories are collapsed
    // <details>, so their text is in the document and indexable but not rendered.
    // innerText measures what is painted, which is the wrong question for "is the
    // content present for a crawler" and dropped this from 41,000 to 19,217.
    const text = await page.evaluate(() => document.body.textContent.length);
    expect(text).toBeGreaterThan(20000);

    // A native disclosure is an intentional reachable fallback, not hidden
    // content. Actually open it with input instead of counting invisible text.
    await page.locator("#library > summary").click();
    await page.locator(".lib__cat").first().locator("summary").click();

    // Every card must carry its description, source and licence with JS off.
    const first = page.locator(".card").first();
    await expect(first).toBeVisible();
    await expect(first.getByRole("heading", { level: 3 })).not.toBeEmpty();
    await expect(first.locator("p")).not.toBeEmpty();
    await expect(first.locator("footer a")).not.toBeEmpty();
    await page.locator("#solutions > summary").click();
    await expect(page.locator(".sol").first()).toBeVisible();
    await ctx.close();
  });

  test("counts on screen agree with the markup", async ({ page }) => {
    await page.goto("/index.html");

    await expect(page.locator(".lib__cat")).toHaveCount(data.categories);
    await expect(page.locator("#gcategory option[value]:not([value=''])")).toHaveCount(data.categories);
    await expect(page.locator("#gsolution option[value]:not([value=''])")).toHaveCount(data.solutions);

    // Each category's declared count must equal the cards it actually holds.
    const rows = await page.locator(".lib__cat").evaluateAll((sections) =>
      sections.map((s) => ({
        id: s.id,
        declared: Number(s.getAttribute("data-count")),
        shown: Number(s.querySelector(".lib__catname span")?.textContent ?? -1),
        actual: s.querySelectorAll(".card").length
      }))
    );
    let running = 0;
    for (const r of rows) {
      expect(r.actual, `${r.id} card count`).toBe(r.declared);
      expect(r.shown, `${r.id} visible count`).toBe(r.declared);
      running += r.declared;
    }
    expect(running).toBe(data.total);

    // Every step of every Solution must resolve to one specific skill, and to a
    // graph node with the same identity.
    //
    // Checked on identity, not on the displayed name. Six names in this library
    // belong to more than one skill, so a name-based version of this check passed
    // while a chain pointed at a skill in an unrelated category that happened to
    // share a word, and while two different skills were drawn as a single node.
    const broken = await page.evaluate(() => {
      const cards = new Set(
        [...document.querySelectorAll(".card")].map((c) => c.getAttribute("data-id"))
      );
      // Nodes only, keyed by the skill's identity. Each node also has a <text> label
      // carrying the same identity, and counting those makes every skill look like two
      // nodes. The layer filter this used to carry is gone with the layers: every node in
      // the graph is a skill now.
      const graph = [...document.querySelectorAll(".g-node")].reduce((m, el) => {
        const key = el.getAttribute("data-key");
        m[key] = (m[key] || 0) + 1;
        return m;
      }, {});
      const bad = [];
      document.querySelectorAll(".sol").forEach((sol) => {
        const lead = sol.getAttribute("data-sol");
        sol.querySelectorAll(".sol__step").forEach((step) => {
          const id = step.getAttribute("data-id");
          if (!id) return bad.push(`${lead} -> a step with no identity`);
          if (!cards.has(id)) bad.push(`${lead} -> ${id} has no library card`);
          // Exactly one, not "at least one": two nodes for one identity is the
          // fusion defect, and no count of nodes can see it.
          if (graph[id] !== 1) {
            bad.push(`${lead} -> ${id} has ${graph[id] || 0} graph nodes`);
          }
        });
      });
      return bad;
    });
    expect(broken, "Solution steps that do not resolve to one skill").toEqual([]);

    // The h1 now names the user's current context, not a huge static billboard.
    await expect(page.locator("h1")).not.toBeEmpty();
    const lede = await page.locator(".sols__lede").textContent();
    expect(lede).toContain(String(data.covered));
    expect(lede).toContain(String(data.unclaimed));
  });

  test("every category filter resolves to a real category and fallback disclosure", async ({ page }) => {
    await page.goto("/index.html");
    const values = await page.locator("#gcategory option").evaluateAll((options) =>
      options.map((o) => o.value).filter(Boolean)
    );
    expect(values).toHaveLength(data.categories);
    for (const value of values) {
      await expect(page.locator(`[id="cat-${value}"]`), `category ${value}`).toHaveCount(1);
    }
    await page.locator("#library > summary").click();
    await page.locator("#cat-finance > summary").click();
    await expect(page.locator("#cat-finance")).toHaveAttribute("open", "");
    await expect(page.locator("#cat-finance .card").first()).toBeVisible();
  });

  test("attribution is present and licence-bearing", async ({ page }) => {
    await page.goto("/index.html");

    // Each source repo is credited with a licence and a resolvable link.
    const credits = page.locator("#credits > div");
    expect(await credits.count()).toBeGreaterThanOrEqual(3);
    for (const row of await credits.all()) {
      await expect(row.locator("strong a")).toHaveAttribute("href", /^https:\/\/github\.com\//);
      await expect(row.locator(".lic")).not.toBeEmpty();
    }

    // No card may ship without naming its licence.
    const missing = await page.locator(".card").evaluateAll((cards) =>
      cards
        .filter((c) => !(c.querySelector("footer .lic")?.textContent ?? "").trim())
        .map((c) => c.querySelector("h3")?.textContent)
    );
    expect(missing, "cards with no licence").toEqual([]);
  });

  test("no placeholder or lorem text survived", () => {
    expect(html).not.toMatch(/lorem ipsum/i);
    expect(html).not.toMatch(/TODO|FIXME|XXX|PLACEHOLDER/);
    expect(html).not.toMatch(/undefined|NaN|\[object Object\]/);
  });
});
