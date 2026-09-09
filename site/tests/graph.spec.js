import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

// Identity/topology stay separate from interaction acceptance so a usable-looking
// subset cannot quietly replace the complete source graph.
const data = JSON.parse(readFileSync(new URL("../data.js", import.meta.url), "utf8")
  .replace(/^window\.SKILLDATA=/, "").replace(/;\s*$/, ""));
const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

test.describe("complete graph identity and evidence", () => {
  test.beforeEach(async ({ page }) => { await page.goto("/index.html"); });

  test("all 490 distinct skills link to exactly their own library cards", async ({ page }) => {
    expect(data.total).toBe(490);
    await expect(page.locator(".g-node")).toHaveCount(data.total);
    const result = await page.locator(".g-node").evaluateAll((nodes) => ({
      keys: nodes.map((n) => n.dataset.key),
      broken: nodes.flatMap((n) => {
        const href = n.getAttribute("href");
        const card = href?.startsWith("#") ? document.getElementById(href.slice(1)) : null;
        return !card || card.dataset.id !== n.dataset.key ? [n.dataset.key] : [];
      }),
      unnamed: nodes.filter((n) => !n.getAttribute("aria-label")?.trim()).map((n) => n.dataset.key)
    }));
    expect(new Set(result.keys).size).toBe(490);
    expect(result.keys.slice().sort()).toEqual(data.nodes.slice().sort());
    expect(result.broken).toEqual([]);
    expect(result.unnamed).toEqual([]);
  });

  test("every drawn edge has the exact endpoints and classification in the data", async ({ page }) => {
    const actual = await page.locator(".g-edge").evaluateAll((edges) => edges.map((e) => ({
      a: e.dataset.a, b: e.dataset.b,
      stated: e.classList.contains("g-edge--extracted")
    })));
    expect(actual).toHaveLength(data.edges.length);
    const signatures = actual.map((e) => `${e.a}|${e.b}|${e.stated}`).sort();
    expect(signatures).toEqual(data.edges.map((e) =>
      `${data.nodes[e[0]]}|${data.nodes[e[1]]}|${e[3] === 0}`).sort());
    expect(data.why).toHaveLength(data.edges.length);
    expect(data.why.every((why) => why.length > 0)).toBe(true);
  });

  test("every skill has a real community and frontier means zero degree", async ({ page }) => {
    const nodes = await page.locator(".g-node").evaluateAll((els) => els.map((n) => ({
      key: n.dataset.key, comm: Number(n.dataset.comm), degree: Number(n.dataset.deg)
    })));
    const degree = new Map(data.nodes.map((key) => [key, 0]));
    data.edges.forEach(([a, b]) => {
      degree.set(data.nodes[a], degree.get(data.nodes[a]) + 1);
      degree.set(data.nodes[b], degree.get(data.nodes[b]) + 1);
    });
    for (const node of nodes) {
      expect(data.comms.some((c) => c.id === node.comm), `${node.key} community`).toBe(true);
      expect(node.degree, `${node.key} degree`).toBe(degree.get(node.key));
    }
    for (const community of data.comms) {
      expect(nodes.filter((n) => n.comm === community.id)).toHaveLength(community.size);
    }
    expect(nodes.filter((n) => n.degree === 0)).toHaveLength(data.agreement.automatic);
  });

  test("graph markup has no inline CSS or duplicate identity", () => {
    expect((html.match(/class="g-node\b/g) || [])).toHaveLength(data.total);
    expect(html).not.toMatch(/\sstyle\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/i);
  });
});
